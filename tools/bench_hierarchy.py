"""
============================================================================
FILE: bench_hierarchy.py
LOCATION: tools/bench_hierarchy.py
============================================================================

PURPOSE:
    Performance benchmarking script for hierarchy API endpoints.
    Measures response times for GET requests to departments, semesters,
    subjects, and modules endpoints to identify performance bottlenecks.

ROLE IN PROJECT:
    Development/debugging utility for monitoring API performance.
    Useful when optimizing Firestore queries or adding caching layers.
    Not used in production - development tool only.

KEY COMPONENTS:
    - Uses FastAPI TestClient for in-process API testing
    - Runs 50 iterations per endpoint (with 5 warmup runs)
    - Reports min, median, mean, p95, and max latency for each endpoint

OUTPUT METRICS:
    - count: Number of test iterations
    - min_ms: Minimum response time
    - median_ms: Median (50th percentile) response time
    - mean_ms: Average response time
    - p95_ms: 95th percentile response time
    - max_ms: Maximum response time

DEPENDENCIES:
    - External: fastapi (TestClient)
    - Internal: api/main.py (FastAPI app)

USAGE:
    python tools/bench_hierarchy.py

EXAMPLE OUTPUT:
    GET /departments
      count: 50
      min_ms: 15.23 ms
      median_ms: 18.45 ms
      ...
============================================================================
"""
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
