"""ADSB Flask API. Run with: python main.py"""
import datetime as dt
import os
import time
from decimal import Decimal

import pymysql
import yaml
from flask import Flask, jsonify, request

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE_DIR, 'config.yml'), encoding='utf-8') as handle:
    config = yaml.safe_load(handle)['mysql']
DB_CONFIG = dict(config)
# Optional environment overrides; don't commit real passwords.
for env, key in [('MYSQL_HOST', 'host'), ('MYSQL_USER', 'user'),
                 ('MYSQL_PASSWORD', 'password'), ('MYSQL_DATABASE', 'database')]:
    if os.environ.get(env):
        DB_CONFIG[key] = os.environ[env]
DB_CONFIG['port'] = int(os.environ.get('MYSQL_PORT', DB_CONFIG.get('port', 3306)))
DB_CONFIG['connect_timeout'] = 5
TABLE_PREFIX = os.environ.get('ADSB_TABLE_PREFIX', 'username_')
# Table names are identifiers, not query parameters. Restrict to safe characters.
if not TABLE_PREFIX.replace('_', '').isalnum():
    raise ValueError('ADSB_TABLE_PREFIX must contain only letters, numbers, and underscores')
AUTH_TABLE = f'{TABLE_PREFIX}auth'
LOG_TABLE = f'{TABLE_PREFIX}api_logs'


def connect():
    return pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)


def serialize(value):
    if isinstance(value, (dt.datetime, dt.date)):
        return value.isoformat(sep=' ') if isinstance(value, dt.datetime) else value.isoformat()
    if isinstance(value, dt.time):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (bytes, bytearray)):
        return value.hex()
    if isinstance(value, dict):
        return {k: serialize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serialize(v) for v in value]
    return value


def query(sql, params=(), fetch=True):
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            result = cursor.fetchall() if fetch else None
        if not fetch:
            connection.commit()
        return result
    finally:
        connection.close()


def authenticated(key):
    # The assignment explicitly requires key=123 for every request.
    if key != '123':
        return False
    # Also validate against the assignment-specific authentication table.
    rows = query(f'SELECT `token` FROM `{AUTH_TABLE}` WHERE `token` = %s LIMIT 2', (key,))
    return len(rows) == 1


def log_request(key, endpoint, status):
    # Log every API request; do not allow a logging failure to mask the original response.
    try:
        query(f'INSERT INTO `{LOG_TABLE}` (`endpoint`, `token`, `response`, `dt`) '
              'VALUES (%s, %s, %s, %s)',
              (endpoint, key, str(status), dt.datetime.now()), fetch=False)
    except Exception:
        app.logger.exception('Unable to write API request log')


def reply(endpoint, code, msg, results=None, sqltime=0.0, status=200, **extra):
    payload = {'code': code, 'msg': msg, 'req': endpoint, 'sqltime': round(sqltime, 6)}
    if results is not None:
        payload['results'] = serialize(results)
        payload['num_results'] = len(results) if isinstance(results, list) else None
    payload.update(extra)
    log_request(request.args.get('key'), endpoint, status)
    return jsonify(payload), status


def parse_date(text):
    try:
        return dt.datetime.strptime(text, '%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError):
        raise ValueError('Dates must use YYYY-MM-DD HH:MM:SS')


def check_dates(required):
    start = request.args.get('start')
    end = request.args.get('end')
    if required and (not start or not end):
        raise ValueError('start and end dates are required')
    a = parse_date(start) if start else None
    b = parse_date(end) if end else None
    if a and b and a > b:
        raise ValueError('start must be earlier than or equal to end')
    return a, b


def check_polygon(value):
    if not value:
        raise ValueError('polygon is required')
    points = []
    for pair in value.split(','):
        coords = pair.strip().split()
        if len(coords) != 2:
            raise ValueError('Each polygon point must be longitude latitude')
        try:
            lon, lat = (float(v) for v in coords)
        except ValueError:
            raise ValueError('Polygon coordinates must be numeric')
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            raise ValueError('Polygon coordinates are out of range')
        points.append((lon, lat))
    if len(points) < 4 or points[0] != points[-1] or len(set(points[:-1])) < 3:
        raise ValueError('Polygon requires 3 distinct vertices and a closing point')
    return 'POLYGON((' + ','.join(f'{x:g} {y:g}' for x, y in points) + '))'


def execute_endpoint(endpoint, callback):
    started = time.time()
    try:
        if not authenticated(request.args.get('key')):
            return reply(endpoint, 0, 'Invalid API key; key must be 123 and authorized',
                         sqltime=time.time() - started, status=401)
        results = callback()
        return reply(endpoint, 1, 'ok', results=results,
                     sqltime=time.time() - started)
    except ValueError as exc:
        return reply(endpoint, 0, str(exc), sqltime=time.time() - started, status=400)
    except pymysql.MySQLError:
        app.logger.exception('Database request failed')
        return reply(endpoint, 0, 'Database error; check connection and table setup',
                     sqltime=time.time() - started, status=500)


@app.get('/')
def root():
    return reply('/', 0, 'Specify /getData, /countInPolygon, or /getAvgSpeedByFlight', status=404)


@app.get('/getData')
def get_data():
    def run():
        start, end = check_dates(required=True)
        return query('SELECT * FROM `class_datapoints` WHERE `date_time` BETWEEN %s AND %s '
                     'ORDER BY `date_time` LIMIT 500', (start, end))
    return execute_endpoint('getData', run)


@app.get('/countInPolygon')
def count_in_polygon():
    def run():
        wkt = check_polygon(request.args.get('polygon'))
        rows = query('SELECT COUNT(*) AS `count` FROM `class_datapoints` '
                     'WHERE ST_Within(`geo_point`, ST_GeomFromText(%s, 0))', (wkt,))
        return rows
    return execute_endpoint('countInPolygon', run)


@app.get('/getAvgSpeedByFlight')
def avg_speed():
    def run():
        start, end = check_dates(required=False)
        sql = 'SELECT AVG(`gs`) AS `avg_speed`, `flight_num` FROM `class_datapoints`'
        clauses, params = [], []
        if start is not None:
            clauses.append('`date_time` >= %s')
            params.append(start)
        if end is not None:
            clauses.append('`date_time` <= %s')
            params.append(end)
        if clauses:
            sql += ' WHERE ' + ' AND '.join(clauses)
        sql += ' GROUP BY `flight_num` ORDER BY `flight_num` LIMIT 500'
        return query(sql, tuple(params))
    return execute_endpoint('getAvgSpeedByFlight', run)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
