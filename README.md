# School Management — Data Studio

Streamlit app for school data: SQL query lab, live schema flow, and auto dashboards.

## Features

- Run SQL against a SQLite school database
- Schema flow that follows your query (plus FK-connected tables)
- AI-style dashboards (charts + insights from query results)
- Large dummy dataset for testing

## Setup

```bash
python -m venv venv
# Windows
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python database.py
streamlit run app.py
```

## Project files

| File | Purpose |
|------|---------|
| `app.py` | Streamlit UI |
| `database.py` | Schema, seed data, query helpers |
| `requirements.txt` | Dependencies |

## GitHub

https://github.com/MeghanaBogini09
