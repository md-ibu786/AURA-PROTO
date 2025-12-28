# AURA-PROTO

Local development instructions

1) Install dependencies
```
pip install -r requirements.txt
```

2) Start API
```
cd api
uvicorn main:app --reload --port 8000
```

3) Seed dev data (optional)
```
python -m api.seed_db
```

4) Run Streamlit UI
```
streamlit run UI/main.py
```

Notes:
- API base URL default is http://localhost:8000; set `API_BASE_URL` env var to override.
- The explorer page for staff is at `UI/explorer.py` (requires `STAFF_KEY` env var when set).
