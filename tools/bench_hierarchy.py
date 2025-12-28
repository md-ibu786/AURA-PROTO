"""Benchmark the hierarchy endpoints using FastAPI TestClient"""
import statistics, time
from fastapi.testclient import TestClient
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# import app as module
from api import main

client = TestClient(main.app)

endpoints = [
    ('GET /departments', '/departments'),
]
# First get a department id
resp = client.get('/departments')
depts = resp.json().get('departments', [])
if not depts:
    raise SystemExit('No departments found')
dep_id = depts[0]['id']
endpoints.append((f'GET /departments/{dep_id}/semesters', f'/departments/{dep_id}/semesters'))
# get semester id
resp = client.get(f'/departments/{dep_id}/semesters')
sems = resp.json().get('semesters', [])
sem_id = sems[0]['id'] if sems else None
if sem_id:
    endpoints.append((f'GET /semesters/{sem_id}/subjects', f'/semesters/{sem_id}/subjects'))
    resp = client.get(f'/semesters/{sem_id}/subjects')
    subs = resp.json().get('subjects', [])
    sub_id = subs[0]['id'] if subs else None
    if sub_id:
        endpoints.append((f'GET /subjects/{sub_id}/modules', f'/subjects/{sub_id}/modules'))

N = 50
results = {}

for name, path in endpoints:
    durations = []
    # warmup 5
    for _ in range(5):
        client.get(path)
    for _ in range(N):
        t0 = time.perf_counter()
        r = client.get(path)
        t1 = time.perf_counter()
        durations.append((t1-t0)*1000)
        if r.status_code != 200:
            print('Non-200', path, r.status_code, r.text)
    durations.sort()
    results[name] = {
        'count': N,
        'min_ms': durations[0],
        'median_ms': statistics.median(durations),
        'mean_ms': statistics.mean(durations),
        'p95_ms': durations[int(0.95*len(durations))-1],
        'max_ms': durations[-1]
    }

for k,v in results.items():
    print(k)
    for kk,vv in v.items():
        if isinstance(vv,float):
            print(f'  {kk}: {vv:.2f} ms')
        else:
            print(f'  {kk}: {vv}')
