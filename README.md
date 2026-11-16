# ADSB API assignment

Flask/MySQL implementation based on the instructor's `ADSB API.pdf`, `main.py`, `test-client.py`, and `config.yml` examples.

## Deliverables

- `main.py`: Flask server with the three required GET endpoints and key authentication and logging.
- `test-client.py`: HTTP client covering success and failure cases.
- `schemas/`: proposed JSON Schema for each endpoint's response.
- `setup.sql`: creates assignment-specific auth and request log tables.
- `tests/test_api.py`: automated offline unit tests (mock MySQL, not live database verification).
- `config.yml`, `requirements.txt`, `.gitignore`: setup files.

## Before running

1. Make a Python virtual environment: `python -m venv .venv` and activate it.
2. Install dependencies: `pip install -r requirements.txt`.
3. Replace placeholders in `config.yml` with **your own authorized MySQL credentials** (from the instructor-provided file). Do not push passwords to a public GitHub repository. Alternatively, set `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE` environment variables.
4. Run `setup.sql` in your MySQL database, **changing `username_` to your instructor-assigned username prefix if needed**. The default application prefix is `username_`; set `ADSB_TABLE_PREFIX` to match any changed prefix (include trailing underscore). The supplied `class_datapoints` table must already be accessible.
5. Run `python main.py` in one terminal, then `python test-client.py` in another.
6. Run `pytest -q` to check offline tests independently of the database.

## Endpoints

Base: `http://127.0.0.1:5000`. All requests require `key=123` and a matching row in the auth table.

- `GET /getData?key=123&start=2022-11-23%2005:28:10&end=2022-11-23%2005:28:15`: up to 500 records sorted by date_time. Both dates required.
- `GET /countInPolygon?key=123&polygon=-74%2042,-75%2039,-74%2041,-74%2042`: one result object with the count.
- `GET /getAvgSpeedByFlight?key=123&start=2022-11-23%2005:00:00&end=2022-11-23%2008:00:00`: up to 500 flight averages. Either or both dates can be omitted.

All responses include `code` (1 success, 0 failure), `msg`, `req`, and `sqltime` (elapsed query-operation time in seconds, measured with `time.time()`). Successful responses additionally include `results` and `num_results`. The polygon response uses `results: [{"count": N}]`. The provided assignment mentions `getMinMax` and `getMean` in the response description, but these are not listed as endpoints; `req` uses the actual requested endpoint names.

## Important limits

**Not yet live-verified:** Database connectivity, actual `class_datapoints` columns and access permissions, and instructor-assigned table prefix must be confirmed in your environment. The original starter code used `class_auth` and `class_api-logs`, but the assignment explicitly requests `username_*` tables, so this project uses new prefixed auth/log tables. The `class_datapoints` table remains unchanged as specified.

## GitHub submission

Create a repository on GitHub, add these files, and submit the resulting repository URL. **Remove credentials from `config.yml` before pushing**. The repository cannot be created from this offline package. You can keep real credentials in environment variables rather than the committed config file.
