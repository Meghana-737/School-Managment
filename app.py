"""
School Management — Query Lab + Schema Flow + AI Dashboards
Run: streamlit run app.py
"""

import re

import pandas as pd
import plotly.express as px
import streamlit as st

from database import get_schema_info, init_database, run_query
from sql_assist import (
    SYNTAX_TEMPLATE,
    merge_suggestion,
    natural_language_to_sql,
    next_syntax_hint,
    suggest_sql,
)

st.set_page_config(
    page_title="School Query Lab",
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Styles ----------
st.markdown(
    """
    <style>
    .block-container { padding-top: 1.2rem; }
    .metric-hint { color: #5b6472; font-size: 0.85rem; }
    div[data-testid="stTextArea"] textarea {
        font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
        font-size: 0.95rem;
    }
    .syntax-hint {
        background: #f0f7ff;
        border: 1px solid #cfe3f7;
        border-radius: 8px;
        padding: 0.55rem 0.75rem;
        color: #1e3a5f;
        font-size: 0.9rem;
        margin-bottom: 0.4rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------- Session / DB init ----------
@st.cache_resource
def bootstrap_db(reset_token: int):
    return init_database(force_reset=(reset_token > 0))


if "reset_token" not in st.session_state:
    st.session_state.reset_token = 0

counts = bootstrap_db(st.session_state.reset_token)

SAMPLE_QUERIES = {
    "Students per class": """
SELECT c.class_name, COUNT(s.student_id) AS student_count
FROM classes c
LEFT JOIN students s ON s.class_id = c.class_id
GROUP BY c.class_id
ORDER BY student_count DESC;
""".strip(),
    "Attendance by status": """
SELECT status, COUNT(*) AS total
FROM attendance
GROUP BY status
ORDER BY total DESC;
""".strip(),
    "Fee collection summary": """
SELECT fee_type, payment_status,
       COUNT(*) AS records,
       ROUND(SUM(amount), 2) AS total_amount
FROM fees
GROUP BY fee_type, payment_status
ORDER BY fee_type, payment_status;
""".strip(),
    "Top teachers by subject": """
SELECT subject, COUNT(*) AS teachers, ROUND(AVG(salary), 2) AS avg_salary
FROM teachers
GROUP BY subject
ORDER BY teachers DESC;
""".strip(),
    "Daily attendance trend": """
SELECT attend_date, status, COUNT(*) AS count
FROM attendance
GROUP BY attend_date, status
ORDER BY attend_date;
""".strip(),
    "Gender distribution": """
SELECT gender, status, COUNT(*) AS total
FROM students
GROUP BY gender, status;
""".strip(),
}


def extract_tables_from_sql(sql: str, known_tables: list[str]) -> list[str]:
    """Detect which known tables are referenced in the SQL text."""
    if not sql or not sql.strip():
        return []
    # Strip simple comments so table names in comments are ignored
    cleaned = re.sub(r"--.*?$", "", sql, flags=re.MULTILINE)
    cleaned = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.DOTALL)
    lower = cleaned.lower()
    found = []
    for table in known_tables:
        # Match table name as a whole word (FROM/JOIN/UPDATE/INTO etc.)
        if re.search(rf"\b{re.escape(table.lower())}\b", lower):
            found.append(table)
    return found


def expand_connected_tables(schema: dict, seed_tables: list[str]) -> list[str]:
    """
    Add every table linked by a foreign key to any seed table
    (both directions: teachers ← classes, students → fees, etc.).
    """
    if not seed_tables:
        return []
    connected = set(seed_tables)
    for e in schema["edges"]:
        if e["from_table"] in seed_tables:
            connected.add(e["to_table"])
        if e["to_table"] in seed_tables:
            connected.add(e["from_table"])
    # Keep stable order: seeds first, then related alphabetically
    related = sorted(t for t in connected if t not in seed_tables)
    return list(seed_tables) + related


def filter_schema_for_query(
    schema: dict,
    query_tables: list[str],
    include_connected: bool = True,
) -> dict:
    """Keep query tables (+ optionally FK-connected neighbors) and edges between them."""
    if not query_tables:
        return schema
    show = (
        expand_connected_tables(schema, query_tables)
        if include_connected
        else list(query_tables)
    )
    active = set(show)
    tables = [t for t in schema["tables"] if t in active]
    columns = {t: schema["columns"][t] for t in tables}
    edges = [
        e
        for e in schema["edges"]
        if e["from_table"] in active and e["to_table"] in active
    ]
    return {"tables": tables, "columns": columns, "edges": edges}


def schema_to_dot(
    schema: dict,
    query_tables: list[str] | None = None,
    connected_tables: list[str] | None = None,
) -> str:
    """Build Graphviz DOT. Query tables = green ★; connected neighbors = blue."""
    queried = set(query_tables or [])
    related = set(connected_tables or []) - queried
    show_all = not queried and not related
    lines = [
        "digraph schema {",
        "  rankdir=LR;",
        '  graph [bgcolor="transparent", pad="0.3", nodesep="0.45", ranksep="0.7"];',
        '  node [shape=record, style="filled,rounded", fontname="Helvetica", fontsize=11];',
        '  edge [color="#5B7C99", penwidth=1.2, arrowsize=0.8];',
    ]
    for table in schema["tables"]:
        cols = schema["columns"][table]
        fields = "\\l".join(
            f"{'🔑 ' if c['pk'] else ''}{c['name']}: {c['type']}" for c in cols
        )
        if show_all or table in queried:
            fill, color, pen = "#DCFCE7", "#15803D", "2.2"
            title = f"★ {table}" if queried and table in queried else table
        elif table in related:
            fill, color, pen = "#DBEAFE", "#1D4ED8", "2.0"
            title = f"🔗 {table}"
        else:
            fill, color, pen = "#F3F4F6", "#9CA3AF", "1.0"
            title = table
        lines.append(
            f'  "{table}" [label="{{{title}|{fields}\\l}}", '
            f'fillcolor="{fill}", color="{color}", penwidth="{pen}"];'
        )
    focus = queried | related
    for e in schema["edges"]:
        touches_focus = e["from_table"] in focus or e["to_table"] in focus
        both_in_focus = e["from_table"] in focus and e["to_table"] in focus
        if focus and both_in_focus:
            edge_color, edge_width = "#1D4ED8", "2.0"
        elif focus and touches_focus:
            edge_color, edge_width = "#93C5FD", "1.4"
        else:
            edge_color, edge_width = "#5B7C99", "1.2"
        lines.append(
            f'  "{e["from_table"]}" -> "{e["to_table"]}" '
            f'[label="{e["from_col"]} → {e["to_col"]}", '
            f'color="{edge_color}", penwidth="{edge_width}"];'
        )
    lines.append("}")
    return "\n".join(lines)


def build_ai_insights(df: pd.DataFrame, sql: str) -> list[str]:
    """Rule-based 'AI' insights from result shape & values."""
    tips = []
    if df.empty:
        return ["Query returned no rows — try a broader SELECT or check filters."]

    tips.append(f"Result shape: **{len(df):,} rows × {len(df.columns)} columns**.")
    numeric = df.select_dtypes(include="number").columns.tolist()
    categorical = [c for c in df.columns if c not in numeric]

    if numeric:
        for col in numeric[:3]:
            series = pd.to_numeric(df[col], errors="coerce").dropna()
            if series.empty:
                continue
            tips.append(
                f"**{col}** → min `{series.min():,.2f}`, max `{series.max():,.2f}`, "
                f"avg `{series.mean():,.2f}`, sum `{series.sum():,.2f}`."
            )
            if series.std() and series.mean() and (series.std() / abs(series.mean())) > 1.2:
                tips.append(f"High variance on **{col}** — good candidate for outlier review.")

    if categorical:
        for col in categorical[:2]:
            vc = df[col].astype(str).value_counts()
            if len(vc) == 0:
                continue
            top = vc.index[0]
            pct = 100 * vc.iloc[0] / len(df)
            tips.append(
                f"**{col}** is dominated by `{top}` ({pct:.1f}% of rows, {len(vc)} unique values)."
            )

    sql_l = sql.lower()
    if "attendance" in sql_l:
        tips.append("Attendance query detected — compare Present vs Absent rates over dates.")
    if "fee" in sql_l:
        tips.append("Fees query detected — watch Pending/Overdue amounts vs Paid.")
    if "group by" in sql_l:
        tips.append("Grouped result — bar/pie charts usually work best for this output.")
    if len(df) >= 1000:
        tips.append("Large result set — charts sample for speed; use LIMIT in SQL for exploration.")

    return tips


def execute_and_store(sql: str) -> bool:
    """Run SQL, save result + active tables into session. Return True on success."""
    try:
        cols, rows = run_query(sql)
        result_df = pd.DataFrame(rows, columns=cols)
        full_schema = get_schema_info()
        used_tables = extract_tables_from_sql(sql, full_schema["tables"])
        connected = [
            t
            for t in expand_connected_tables(full_schema, used_tables)
            if t not in used_tables
        ]
        st.session_state["last_df"] = result_df
        st.session_state["last_sql"] = sql
        st.session_state["active_tables"] = used_tables
        msg = (
            f"Query OK — {len(result_df):,} row(s) | "
            f"tables: {', '.join(used_tables) if used_tables else 'none'}"
        )
        if connected:
            msg += f" | connected: {', '.join(connected)}"
        st.success(msg)
        return True
    except Exception as e:
        st.error(f"SQL error: {e}")
        return False


def _insert_sql_chip(insert: str) -> None:
    st.session_state.sql_editor = merge_suggestion(
        st.session_state.get("sql_editor", ""), insert
    )


def _use_nl_example() -> None:
    pick = st.session_state.get("nl_example_pick", "")
    if pick and pick != "(choose an example)":
        st.session_state.nl_question = pick


def _convert_nl(run: bool) -> None:
    parsed = natural_language_to_sql(
        st.session_state.get("nl_question", ""), get_schema_info()
    )
    st.session_state["nl_parsed"] = parsed
    if parsed["ok"]:
        st.session_state.sql_editor = parsed["sql"]
        st.session_state.sql_text = parsed["sql"]
        st.session_state["_run_after_nl"] = run
    else:
        st.session_state["_run_after_nl"] = False


def render_auto_charts(df: pd.DataFrame) -> None:
    """Auto-pick charts from column types (AI dashboard)."""
    if df.empty:
        st.info("No data to chart.")
        return

    work = df.copy()
    # Cap for plotting performance
    if len(work) > 5000:
        work = work.sample(5000, random_state=42)
        st.caption("Charting a random sample of 5,000 rows for performance.")

    numeric = work.select_dtypes(include="number").columns.tolist()
    categorical = [c for c in work.columns if c not in numeric]
    date_like = []
    for c in work.columns:
        if "date" in c.lower():
            try:
                work[c] = pd.to_datetime(work[c])
                date_like.append(c)
            except Exception:
                pass

    c1, c2 = st.columns(2)

    with c1:
        if len(categorical) >= 1 and len(numeric) >= 1:
            fig = px.bar(
                work.groupby(categorical[0], as_index=False)[numeric[0]].sum()
                if work[categorical[0]].nunique() < 40
                else work.head(40),
                x=categorical[0],
                y=numeric[0],
                title=f"{numeric[0]} by {categorical[0]}",
                color=categorical[0],
            )
            fig.update_layout(showlegend=False, height=380)
            st.plotly_chart(fig, use_container_width=True)
        elif len(numeric) >= 1:
            fig = px.histogram(work, x=numeric[0], title=f"Distribution of {numeric[0]}")
            fig.update_layout(height=380)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.write("Not enough numeric columns for a bar chart.")

    with c2:
        if len(categorical) >= 1:
            counts = work[categorical[0]].astype(str).value_counts().reset_index()
            counts.columns = [categorical[0], "count"]
            if len(counts) > 12:
                counts = counts.head(12)
            fig = px.pie(
                counts,
                names=categorical[0],
                values="count",
                title=f"Share of {categorical[0]}",
                hole=0.35,
            )
            fig.update_layout(height=380)
            st.plotly_chart(fig, use_container_width=True)
        elif len(numeric) >= 2:
            fig = px.scatter(
                work, x=numeric[0], y=numeric[1], title=f"{numeric[1]} vs {numeric[0]}"
            )
            fig.update_layout(height=380)
            st.plotly_chart(fig, use_container_width=True)

    if date_like and numeric:
        dcol = date_like[0]
        daily = work.groupby(dcol, as_index=False)[numeric[0]].sum().sort_values(dcol)
        fig = px.line(daily, x=dcol, y=numeric[0], title=f"{numeric[0]} over {dcol}")
        fig.update_layout(height=360)
        st.plotly_chart(fig, use_container_width=True)


# ===================== SIDEBAR =====================
with st.sidebar:
    st.title("School Query Lab")
    st.caption("SQL → Results → Schema Flow → AI Dashboard")

    st.markdown("### Database size")
    for name, n in counts.items():
        st.write(f"**{name}**: {n:,}")

    st.markdown("---")
    st.markdown("### Sample queries")
    pick = st.selectbox("Load example", list(SAMPLE_QUERIES.keys()))
    if st.button("Insert sample into editor", use_container_width=True):
        st.session_state.sql_editor = SAMPLE_QUERIES[pick]
        st.session_state.sql_text = SAMPLE_QUERIES[pick]

    st.markdown("---")
    if st.button("Rebuild DB + reseed huge data", type="secondary", use_container_width=True):
        st.cache_resource.clear()
        st.session_state.reset_token += 1
        st.rerun()

    page = st.radio(
        "View",
        ["Query Lab", "Schema Flow", "AI Dashboards", "All-in-one"],
        index=3,
    )


# ===================== MAIN =====================
st.title("School Management — Data Studio")
st.write(
    "Run SQL against the school database, inspect the schema as a flow, "
    "and generate AI-style dashboards from the result."
)

if "sql_editor" not in st.session_state:
    st.session_state.sql_editor = SAMPLE_QUERIES["Students per class"]
if "nl_question" not in st.session_state:
    st.session_state.nl_question = ""
st.session_state.sql_text = st.session_state.sql_editor

# ---------- QUERY LAB ----------
if page in ("Query Lab", "All-in-one"):
    st.header("1) DB Query")
    live_schema = get_schema_info()
    if st.session_state.pop("_run_after_nl", False):
        execute_and_store(st.session_state.get("sql_editor", ""))

    sql_col, nl_col = st.columns(2, gap="large")

    with sql_col:
        st.subheader("Write SQL")
        sql = st.text_area(
            "SQL editor",
            height=180,
            key="sql_editor",
            help="Click a suggestion chip to insert it. SELECT / WITH recommended.",
        )
        st.session_state.sql_text = sql

        st.markdown(
            f'<div class="syntax-hint">💡 {next_syntax_hint(sql)}</div>',
            unsafe_allow_html=True,
        )
        st.caption("Click outside the editor to refresh suggestions as you type.")

        chips = suggest_sql(sql, live_schema)
        if chips:
            st.caption("Click to insert SQL syntax / tables / columns")
            n_cols = 4
            rows = [chips[i : i + n_cols] for i in range(0, len(chips), n_cols)]
            for r_i, row in enumerate(rows):
                bcols = st.columns(n_cols)
                for c_i, item in enumerate(row):
                    with bcols[c_i]:
                        label = item["label"]
                        if len(label) > 28:
                            label = label[:26] + "…"
                        st.button(
                            label,
                            key=f"sug_{r_i}_{c_i}_{item['kind']}",
                            help=f"{item['kind']}: {item['detail'] or item['insert']}",
                            use_container_width=True,
                            on_click=_insert_sql_chip,
                            args=(item["insert"],),
                        )

        with st.expander("SQL syntax cheat-sheet"):
            st.code(SYNTAX_TEMPLATE, language="sql")
            st.caption("Tables: " + ", ".join(live_schema["tables"]))

        if st.button("Run SQL", type="primary", use_container_width=True, key="run_sql_btn"):
            execute_and_store(sql)

    with nl_col:
        st.subheader("Ask in words")
        st.caption("Type a question in English — it becomes SQL and fetches data.")
        st.text_area(
            "Your question",
            height=180,
            key="nl_question",
            placeholder="e.g. show pending fees with student names",
        )

        st.selectbox(
            "Try an example",
            ["(choose an example)"]
            + [
                "how many students per class",
                "show female students in grade 8",
                "list mathematics teachers",
                "pending fees with student names",
                "average salary by subject",
                "top 10 teachers by salary",
                "attendance by status",
                "total paid fees",
                "absent students with class name",
                "students in Grade 5-A",
            ],
            key="nl_example_pick",
        )
        st.button(
            "Use this example",
            use_container_width=True,
            key="use_nl_ex",
            on_click=_use_nl_example,
        )

        conv_col, run_nl_col = st.columns(2)
        with conv_col:
            st.button(
                "Convert to SQL",
                use_container_width=True,
                key="nl_convert",
                on_click=_convert_nl,
                args=(False,),
            )
        with run_nl_col:
            st.button(
                "Convert & run",
                type="primary",
                use_container_width=True,
                key="nl_convert_run",
                on_click=_convert_nl,
                args=(True,),
            )

        parsed = st.session_state.get("nl_parsed")
        if parsed and parsed.get("ok") and parsed.get("sql"):
            st.markdown("**Generated SQL**")
            st.code(parsed["sql"], language="sql")
            st.caption(parsed.get("explanation", ""))
        elif parsed and not parsed.get("ok"):
            st.warning(parsed.get("explanation", "Could not convert that question."))
            st.caption("Examples: " + " · ".join(parsed.get("examples", [])[:4]))

    if "last_df" in st.session_state:
        st.markdown("##### Results")
        st.dataframe(st.session_state["last_df"], use_container_width=True, height=320)

# ---------- SCHEMA FLOW ----------
if page in ("Schema Flow", "All-in-one"):
    st.header("2) Schema Flow (query tables + connected tables)")
    full_schema = get_schema_info()

    # Prefer last successful query; else peek at current editor SQL
    focus_sql = st.session_state.get("last_sql") or st.session_state.get("sql_text", "")
    query_tables = st.session_state.get("active_tables")
    if query_tables is None:
        query_tables = extract_tables_from_sql(focus_sql, full_schema["tables"])

    expanded = expand_connected_tables(full_schema, query_tables)
    connected_only = [t for t in expanded if t not in query_tables]

    show_mode = st.radio(
        "Flow mode",
        [
            "Query + connected tables",
            "Query tables only",
            "Full schema (highlight related)",
        ],
        horizontal=True,
        help="Connected = tables linked by foreign keys (e.g. teachers → classes).",
    )

    if show_mode.startswith("Query +"):
        view_schema = filter_schema_for_query(
            full_schema, query_tables, include_connected=True
        )
    elif show_mode.startswith("Query tables"):
        view_schema = filter_schema_for_query(
            full_schema, query_tables, include_connected=False
        )
    else:
        view_schema = full_schema

    if query_tables:
        msg = f"★ In query: **{' · '.join(query_tables)}**"
        if connected_only:
            msg += f"  |  🔗 Connected: **{' · '.join(connected_only)}**"
        st.info(msg)
    else:
        st.warning("Run a query first — schema flow will show those tables and their connections.")

    left, right = st.columns([2, 1])
    with left:
        try:
            st.graphviz_chart(
                schema_to_dot(
                    view_schema,
                    query_tables=query_tables,
                    connected_tables=connected_only,
                ),
                use_container_width=True,
            )
        except Exception as e:
            st.warning(
                "Graphviz chart could not render in this environment. "
                f"Showing table list instead. ({e})"
            )
            for t in view_schema["tables"]:
                if t in query_tables:
                    mark = " ★ (in query)"
                elif t in connected_only:
                    mark = " 🔗 (connected)"
                else:
                    mark = ""
                st.markdown(f"**{t}{mark}**")
                st.table(pd.DataFrame(view_schema["columns"][t]))
    with right:
        st.caption("★ green = used in SQL · 🔗 blue = FK-connected")
        st.subheader("In this query")
        if query_tables:
            for t in query_tables:
                pk = [c["name"] for c in full_schema["columns"][t] if c["pk"]]
                st.markdown(f"- **{t}** (PK: {', '.join(pk) or '—'})")
        else:
            st.write("No tables detected yet.")

        st.subheader("Connected tables")
        if connected_only:
            for t in connected_only:
                # Explain why it's connected
                reasons = []
                for e in full_schema["edges"]:
                    if e["from_table"] == t and e["to_table"] in query_tables:
                        reasons.append(
                            f"`{t}.{e['from_col']}` → `{e['to_table']}.{e['to_col']}`"
                        )
                    elif e["to_table"] == t and e["from_table"] in query_tables:
                        reasons.append(
                            f"`{e['from_table']}.{e['from_col']}` → `{t}.{e['to_col']}`"
                        )
                st.markdown(f"- **{t}**")
                for r in reasons:
                    st.caption(r)
        else:
            st.write("No FK neighbors for the queried tables.")

        st.subheader("Relationships shown")
        if view_schema["edges"]:
            for e in view_schema["edges"]:
                st.markdown(
                    f"`{e['from_table']}.{e['from_col']}` → "
                    f"`{e['to_table']}.{e['to_col']}`"
                )
        else:
            st.write("No FK links between the selected tables.")

        with st.expander("All DB tables"):
            for t in full_schema["tables"]:
                st.markdown(f"- {t}")

# ---------- AI DASHBOARDS ----------
if page in ("AI Dashboards", "All-in-one"):
    st.header("3) AI Dashboards")
    df = st.session_state.get("last_df")
    last_sql = st.session_state.get("last_sql", "")

    if df is None:
        st.info("Run a query first in the Query Lab — the dashboard uses that result.")
        # Fallback: show global KPI dashboard from DB
        st.subheader("Global KPIs (whole database)")
        try:
            _, rows = run_query(
                """
                SELECT
                  (SELECT COUNT(*) FROM students WHERE status='Active') AS active_students,
                  (SELECT COUNT(*) FROM teachers) AS teachers,
                  (SELECT COUNT(*) FROM classes) AS classes,
                  (SELECT ROUND(SUM(amount),2) FROM fees WHERE payment_status='Paid') AS fees_paid,
                  (SELECT ROUND(SUM(amount),2) FROM fees WHERE payment_status!='Paid') AS fees_outstanding
                """
            )
            k = rows[0]
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Active students", f"{k[0]:,}")
            m2.metric("Teachers", f"{k[1]:,}")
            m3.metric("Classes", f"{k[2]:,}")
            m4.metric("Fees paid", f"₹{k[3]:,.0f}")
            m5.metric("Fees outstanding", f"₹{k[4]:,.0f}")

            _, att = run_query(
                """
                SELECT status, COUNT(*) AS total
                FROM attendance GROUP BY status
                """
            )
            adf = pd.DataFrame(att, columns=["status", "total"])
            fig = px.bar(adf, x="status", y="total", color="status", title="Attendance overall")
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(str(e))
    else:
        st.subheader("AI insights")
        for tip in build_ai_insights(df, last_sql):
            st.markdown(f"- {tip}")
        st.subheader("Auto charts")
        render_auto_charts(df)
