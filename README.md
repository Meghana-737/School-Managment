# School Management — Data Studio

Streamlit app for school data: SQL query lab, live schema flow, and auto dashboards.

## Features

- Run SQL against a SQLite school database
- Schema flow that follows your query (plus FK-connected tables)
- AI-style dashboards (charts + insights from query results)
- Large dummy dataset for testing

## Setup (local)

```bash
python -m venv venv
# Windows
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python database.py
streamlit run app.py
```

## Deploy (Streamlit Community Cloud)

1. Open [Streamlit Community Cloud](https://share.streamlit.io/)
2. Sign in with GitHub
3. Click **New app**
4. Choose repo: `Meghana-737/School-Managment`
5. Branch: `main` · Main file: `app.py`
6. Click **Deploy**

Direct deploy link (after GitHub login):  
https://share.streamlit.io/deploy?repository=Meghana-737/School-Managment&branch=main&mainModule=app.py

The database file is created automatically on first run (`database.py` seeds dummy data).

## Project files

| File | Purpose |
|------|---------|
| `app.py` | Streamlit UI |
| `database.py` | Schema, seed data, query helpers |
| `requirements.txt` | Python dependencies |
| `packages.txt` | System packages (Graphviz for schema diagram) |

## GitHub

https://github.com/Meghana-737/School-Managment
