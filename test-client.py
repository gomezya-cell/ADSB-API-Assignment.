"""Run after starting main.py: python test-client.py"""
import json
import requests

BASE = 'http://127.0.0.1:5000'
CASES = [
    ('Invalid key', '/getData', {'key': '1234', 'start': '2022-11-23 05:28:10', 'end': '2022-11-23 05:28:15'}, 0),
    ('Missing dates', '/getData', {'key': '123'}, 0),
    ('Data in range', '/getData', {'key': '123', 'start': '2022-11-23 05:28:10', 'end': '2022-11-23 05:28:15'}, 1),
    ('Polygon count', '/countInPolygon', {'key': '123', 'polygon': '-74 42,-75 39,-74 41,-74 42'}, 1),
    ('Average speed with dates', '/getAvgSpeedByFlight', {'key': '123', 'start': '2022-11-23 05:00:00', 'end': '2022-11-23 08:00:00'}, 1),
    ('Average speed without dates', '/getAvgSpeedByFlight', {'key': '123'}, 1),
]

failures = 0
for name, endpoint, params, expected in CASES:
    try:
        response = requests.get(BASE + endpoint, params=params, timeout=30)
        body = response.json()
        passed = (body.get('code') == expected and
                  all(key in body for key in ('code', 'msg', 'req', 'sqltime')))
        if expected == 1:
            passed = passed and isinstance(body.get('results'), list)
        print(f'{"PASS" if passed else "FAIL"} | {name} | HTTP {response.status_code} | '
              f'{body.get("msg")} | {body.get("num_results", "-")} records')
        if not passed:
            failures += 1
            print(json.dumps(body, indent=2))
    except requests.RequestException as exc:
        failures += 1
        print(f'FAIL | {name} | {exc}')
print(f'\n{len(CASES) - failures}/{len(CASES)} tests passed')
raise SystemExit(1 if failures else 0)
