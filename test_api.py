"""Offline tests: pytest -q (database calls mocked)."""
import importlib.util
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('adsb_api', Path(__file__).resolve().parents[1] / 'main.py')
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)


def client():
    api.app.config['TESTING'] = True
    return api.app.test_client()


def test_invalid_key():
    with patch.object(api, 'log_request'):
        response = client().get('/getData?key=bad')
    assert response.status_code == 401
    assert response.json['code'] == 0


def test_get_data_and_limit():
    with patch.object(api, 'query', side_effect=[[{'token': '123'}], [{'flight_num': 'ABC'}]]) as mock_query, patch.object(api, 'log_request'):
        response = client().get('/getData', query_string={'key': '123', 'start': '2022-11-23 05:28:10', 'end': '2022-11-23 05:28:15'})
    assert response.json['code'] == 1
    assert response.json['results'][0]['flight_num'] == 'ABC'
    assert 'LIMIT 500' in mock_query.call_args.args[0]


def test_missing_dates():
    with patch.object(api, 'query', return_value=[{'token': '123'}]), patch.object(api, 'log_request'):
        response = client().get('/getData?key=123')
    assert response.status_code == 400
    assert response.json['code'] == 0


def test_polygon():
    with patch.object(api, 'query', side_effect=[[{'token': '123'}], [{'count': 42}]]) as mock_query, patch.object(api, 'log_request'):
        response = client().get('/countInPolygon', query_string={'key': '123', 'polygon': '-74 42,-75 39,-74 41,-74 42'})
    assert response.json['results'] == [{'count': 42}]
    assert 'ST_Within' in mock_query.call_args.args[0]


def test_invalid_polygon():
    with patch.object(api, 'query', return_value=[{'token': '123'}]), patch.object(api, 'log_request'):
        response = client().get('/countInPolygon', query_string={'key': '123', 'polygon': '1 2,3 4'})
    assert response.status_code == 400


def test_avg_without_dates():
    with patch.object(api, 'query', side_effect=[[{'token': '123'}], [{'flight_num': 'A1', 'avg_speed': 210.5}]]) as mock_query, patch.object(api, 'log_request'):
        response = client().get('/getAvgSpeedByFlight?key=123')
    assert response.json['code'] == 1
    assert 'GROUP BY' in mock_query.call_args.args[0]
    assert 'WHERE' not in mock_query.call_args.args[0]


def test_avg_with_one_date():
    with patch.object(api, 'query', side_effect=[[{'token': '123'}], []]) as mock_query, patch.object(api, 'log_request'):
        response = client().get('/getAvgSpeedByFlight', query_string={'key': '123', 'start': '2022-11-23 05:00:00'})
    assert response.json['code'] == 1
    assert '`date_time` >= %s' in mock_query.call_args.args[0]
