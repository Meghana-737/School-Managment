"""SQL syntax suggestions and natural-language → SQL for the school schema."""

from __future__ import annotations

import re

SQL_KEYWORDS = [
    "SELECT",
    "DISTINCT",
    "FROM",
    "WHERE",
    "AND",
    "OR",
    "NOT",
    "IN",
    "LIKE",
    "BETWEEN",
    "IS NULL",
    "IS NOT NULL",
    "JOIN",
    "LEFT JOIN",
    "INNER JOIN",
    "ON",
    "GROUP BY",
    "HAVING",
    "ORDER BY",
    "ASC",
    "DESC",
    "LIMIT",
    "AS",
    "COUNT(*)",
    "SUM(",
    "AVG(",
    "MIN(",
    "MAX(",
]

SYNTAX_TEMPLATE = """\
SELECT   column, …   | * | DISTINCT col | COUNT(*) | SUM(col) | AVG(col)
FROM     table_name
JOIN     other_table ON table.col = other.col
WHERE    column = 'value'  AND  column > 10  AND  column LIKE '%text%'
GROUP BY column
HAVING   COUNT(*) > 1
ORDER BY column DESC
LIMIT    20;"""

TABLE_SYNONYMS = {
    "student": "students",
    "students": "students",
    "pupil": "students",
    "pupils": "students",
    "kid": "students",
    "kids": "students",
    "learner": "students",
    "learners": "students",
    "teacher": "teachers",
    "teachers": "teachers",
    "faculty": "teachers",
    "staff": "teachers",
    "class": "classes",
    "classes": "classes",
    "grade": "classes",
    "grades": "classes",
    "classroom": "classes",
    "attendance": "attendance",
    "attendances": "attendance",
    "absent": "attendance",
    "present": "attendance",
    "fee": "fees",
    "fees": "fees",
    "payment": "fees",
    "payments": "fees",
    "due": "fees",
    "dues": "fees",
}

VALUE_FILTERS = [
    (r"\bfemale\b|\bgirls?\b|\bwomen\b", "students", "gender", "Female"),
    (r"\bmale\b|\bboys?\b|\bmen\b", "students", "gender", "Male"),
    (r"\bactive\b", "students", "status", "Active"),
    (r"\binactive\b", "students", "status", "Inactive"),
    (r"\bpresent\b", "attendance", "status", "Present"),
    (r"\babsent\b", "attendance", "status", "Absent"),
    (r"\blate\b", "attendance", "status", "Late"),
    (r"\bpaid\b", "fees", "payment_status", "Paid"),
    (r"\bpending\b", "fees", "payment_status", "Pending"),
    (r"\boverdue\b", "fees", "payment_status", "Overdue"),
    (r"\btuition\b", "fees", "fee_type", "Tuition"),
    (r"\blab\b", "fees", "fee_type", "Lab"),
    (r"\btransport\b", "fees", "fee_type", "Transport"),
    (r"\blibrary\b", "fees", "fee_type", "Library"),
    (r"\bsports\b", "fees", "fee_type", "Sports"),
]

SUBJECTS = [
    "Mathematics",
    "Science",
    "English",
    "History",
    "Geography",
    "Physics",
    "Chemistry",
    "Biology",
    "Computer Science",
    "Economics",
    "Art",
    "Physical Education",
    "Hindi",
    "Music",
]

ALIASES = {
    "students": "s",
    "classes": "c",
    "teachers": "t",
    "attendance": "a",
    "fees": "f",
}

NICE_SELECT = {
    frozenset(["students"]): (
        "student_id, full_name, gender, date_of_birth, email, phone, "
        "class_id, enrollment_date, status"
    ),
    frozenset(["teachers"]): (
        "teacher_id, full_name, subject, email, phone, hire_date, salary"
    ),
    frozenset(["classes"]): (
        "class_id, class_name, grade_level, room_number, teacher_id, capacity"
    ),
    frozenset(["attendance"]): (
        "attendance_id, student_id, class_id, attend_date, status"
    ),
    frozenset(["fees"]): (
        "fee_id, student_id, fee_type, amount, due_date, paid_date, payment_status"
    ),
    frozenset(["students", "classes"]): (
        "s.student_id, s.full_name, s.gender, s.status, c.class_name, c.grade_level"
    ),
    frozenset(["classes", "teachers"]): (
        "c.class_name, c.grade_level, t.full_name AS teacher_name, t.subject"
    ),
    frozenset(["students", "fees"]): (
        "s.full_name, f.fee_type, f.amount, f.due_date, f.payment_status"
    ),
    frozenset(["attendance", "students"]): (
        "s.full_name, a.attend_date, a.status"
    ),
    frozenset(["attendance", "classes"]): (
        "c.class_name, a.attend_date, a.status"
    ),
    frozenset(["attendance", "students", "classes"]): (
        "s.full_name, c.class_name, a.attend_date, a.status"
    ),
    frozenset(["fees", "students", "classes"]): (
        "s.full_name, c.class_name, f.fee_type, f.amount, f.payment_status"
    ),
    frozenset(["students", "classes", "teachers"]): (
        "s.full_name, c.class_name, t.full_name AS teacher_name, t.subject"
    ),
}

JOIN_FROM = {
    frozenset(["students", "classes"]): (
        "students s JOIN classes c ON s.class_id = c.class_id"
    ),
    frozenset(["classes", "teachers"]): (
        "classes c JOIN teachers t ON c.teacher_id = t.teacher_id"
    ),
    frozenset(["students", "fees"]): (
        "fees f JOIN students s ON f.student_id = s.student_id"
    ),
    frozenset(["attendance", "students"]): (
        "attendance a JOIN students s ON a.student_id = s.student_id"
    ),
    frozenset(["attendance", "classes"]): (
        "attendance a JOIN classes c ON a.class_id = c.class_id"
    ),
    frozenset(["students", "classes", "teachers"]): (
        "students s JOIN classes c ON s.class_id = c.class_id "
        "JOIN teachers t ON c.teacher_id = t.teacher_id"
    ),
    frozenset(["attendance", "students", "classes"]): (
        "attendance a JOIN students s ON a.student_id = s.student_id "
        "JOIN classes c ON a.class_id = c.class_id"
    ),
    frozenset(["fees", "students", "classes"]): (
        "fees f JOIN students s ON f.student_id = s.student_id "
        "JOIN classes c ON s.class_id = c.class_id"
    ),
    frozenset(["fees", "students", "classes", "teachers"]): (
        "fees f JOIN students s ON f.student_id = s.student_id "
        "JOIN classes c ON s.class_id = c.class_id "
        "JOIN teachers t ON c.teacher_id = t.teacher_id"
    ),
    frozenset(["attendance", "students", "classes", "teachers"]): (
        "attendance a JOIN students s ON a.student_id = s.student_id "
        "JOIN classes c ON a.class_id = c.class_id "
        "JOIN teachers t ON c.teacher_id = t.teacher_id"
    ),
}

GROUP_HINTS = [
    (r"\bper class\b|\bby class\b|\beach class\b|\bclass[- ]wise\b", "classes", "class_name"),
    (r"\bper grade\b|\bby grade\b|\beach grade\b", "classes", "grade_level"),
    (r"\bby subject\b|\bper subject\b", "teachers", "subject"),
    (r"\bby gender\b|\bper gender\b", "students", "gender"),
    (r"\bby status\b|\bper status\b", None, "status"),
    (r"\bby fee type\b|\bper fee type\b|\bby type\b", "fees", "fee_type"),
    (r"\bby payment\b|\bby payment status\b", "fees", "payment_status"),
    (r"\bper day\b|\bby date\b|\bdaily\b", "attendance", "attend_date"),
]


def _strip_sql_comments(sql: str) -> str:
    cleaned = re.sub(r"--.*?$", "", sql, flags=re.MULTILINE)
    return re.sub(r"/\*.*?\*/", "", cleaned, flags=re.DOTALL)


def extract_tables(sql: str, known_tables: list[str]) -> list[str]:
    if not sql or not sql.strip():
        return []
    lower = _strip_sql_comments(sql).lower()
    found = []
    for table in known_tables:
        if re.search(rf"\b{re.escape(table.lower())}\b", lower):
            found.append(table)
    return found


def last_token(sql: str) -> str:
    if not sql or sql[-1] in " \n\t,();":
        return ""
    m = re.search(r"([A-Za-z_][\w.]*)$", sql)
    return m.group(1) if m else ""


def _last_clause(sql: str) -> str:
    text = _strip_sql_comments(sql).upper()
    if not text.strip():
        return "start"
    patterns = [
        ("SELECT", r"\bSELECT\b"),
        ("FROM", r"\bFROM\b"),
        ("JOIN", r"\b(?:LEFT|INNER|RIGHT)\s+JOIN\b|\bJOIN\b"),
        ("ON", r"\bON\b"),
        ("WHERE", r"\bWHERE\b"),
        ("GROUP BY", r"\bGROUP\s+BY\b"),
        ("HAVING", r"\bHAVING\b"),
        ("ORDER BY", r"\bORDER\s+BY\b"),
        ("LIMIT", r"\bLIMIT\b"),
    ]
    last_name, last_pos = "start", -1
    for name, pat in patterns:
        for m in re.finditer(pat, text):
            if m.start() >= last_pos:
                last_pos = m.start()
                last_name = name
    return last_name


def next_syntax_hint(sql: str) -> str:
    """One-line hint for the next SQL clause."""
    s = sql.strip()
    if not s:
        return "Start with SELECT — e.g. SELECT * FROM students"
    clause = _last_clause(s)
    upper = _strip_sql_comments(s).upper()
    has_from = bool(re.search(r"\bFROM\b", upper))
    has_select = bool(re.search(r"\bSELECT\b", upper))
    if not has_select:
        return "Queries usually start with SELECT columns FROM table"
    if clause == "SELECT" or (has_select and not has_from):
        return "Next: FROM table_name  — e.g. FROM students"
    if clause == "FROM":
        return "Next: WHERE filter  |  JOIN table ON …  |  GROUP BY  |  ORDER BY  |  LIMIT n"
    if clause == "JOIN":
        return "Next: ON left.col = right.col  — needed to link the tables"
    if clause == "ON":
        return "Next: AND more join keys  |  WHERE  |  GROUP BY  |  ORDER BY  |  LIMIT n"
    if clause == "WHERE":
        return "Next: AND / OR more filters  |  GROUP BY  |  ORDER BY  |  LIMIT n"
    if clause == "GROUP BY":
        return "Next: HAVING agg_filter  |  ORDER BY  |  LIMIT n"
    if clause == "HAVING":
        return "Next: ORDER BY column  |  LIMIT n"
    if clause == "ORDER BY":
        return "Next: ASC or DESC  |  LIMIT n"
    if clause == "LIMIT":
        return "Looks complete — click Run query"
    return "Optional: WHERE, JOIN, GROUP BY, ORDER BY, LIMIT"


def merge_suggestion(current: str, suggestion: str) -> str:
    if not current.strip():
        return suggestion
    token = last_token(current)
    if token and suggestion.lower().startswith(token.lower()) and suggestion.lower() != token.lower():
        return current[: -len(token)] + suggestion
    if current[-1] in " \n\t(":
        return current + suggestion
    return current + " " + suggestion


def suggest_sql(sql: str, schema: dict) -> list[dict]:
    """
    Return suggestion chips:
    {kind, label, insert, detail}
    """
    tables = schema.get("tables", [])
    columns = schema.get("columns", {})
    edges = schema.get("edges", [])
    used = extract_tables(sql, tables)
    clause = _last_clause(sql)
    token = last_token(sql)
    token_l = token.lower()
    items: list[dict] = []

    def add(kind: str, label: str, insert: str, detail: str = "") -> None:
        items.append(
            {"kind": kind, "label": label, "insert": insert, "detail": detail}
        )

    if not sql.strip():
        add("snippet", "SELECT * FROM", "SELECT * FROM ", "all columns")
        add("snippet", "SELECT COUNT(*) FROM", "SELECT COUNT(*) FROM ", "count rows")
        add("snippet", "SELECT DISTINCT", "SELECT DISTINCT ", "unique values")
        for t in tables:
            add("table", t, f"SELECT * FROM {t};", f"preview {t}")
        return items[:12]

    # Prefix autocomplete for the word being typed
    if token_l:
        for kw in SQL_KEYWORDS:
            if kw.lower().startswith(token_l) and kw.lower() != token_l:
                add("keyword", kw, kw, "SQL keyword")
        for t in tables:
            if t.lower().startswith(token_l) and t.lower() != token_l:
                add("table", t, t, "table")
        col_source = used or tables
        seen = set()
        for t in col_source:
            for col in columns.get(t, []):
                name = col["name"]
                if name.lower().startswith(token_l) and name.lower() not in seen:
                    seen.add(name.lower())
                    add("column", name, name, f"column ({t})")

    if clause in ("start", "SELECT") or (
        re.search(r"\bSELECT\b", sql, re.I) and not re.search(r"\bFROM\b", sql, re.I)
    ):
        add("keyword", "FROM", "FROM ", "specify table")
        add("snippet", "*", "*", "all columns")
        add("snippet", "COUNT(*)", "COUNT(*)", "row count")
        add("snippet", "DISTINCT", "DISTINCT ", "unique values")
        for t in used or tables:
            for col in columns.get(t, [])[:6]:
                add("column", col["name"], col["name"], f"{t}")

    if clause == "FROM" or (
        re.search(r"\bFROM\s+$", sql, re.I)
        or re.search(r"\bFROM\s+\w*$", sql.strip(), re.I)
    ):
        for t in tables:
            add("table", t, t, "FROM table")

    if clause in ("FROM", "ON", "WHERE") or used:
        add("keyword", "WHERE", "WHERE ", "filter rows")
        add("keyword", "JOIN", "JOIN ", "inner join")
        add("keyword", "LEFT JOIN", "LEFT JOIN ", "keep unmatched rows")
        add("keyword", "GROUP BY", "GROUP BY ", "aggregate")
        add("keyword", "ORDER BY", "ORDER BY ", "sort")
        add("keyword", "LIMIT 20", "LIMIT 20", "cap rows")

    if clause in ("JOIN", "FROM") and used:
        for e in edges:
            if e["from_table"] in used and e["to_table"] not in used:
                insert = (
                    f"JOIN {e['to_table']} ON {e['from_table']}.{e['from_col']} "
                    f"= {e['to_table']}.{e['to_col']}"
                )
                add("join", f"JOIN {e['to_table']}", insert, "foreign key")
            elif e["to_table"] in used and e["from_table"] not in used:
                insert = (
                    f"JOIN {e['from_table']} ON {e['from_table']}.{e['from_col']} "
                    f"= {e['to_table']}.{e['to_col']}"
                )
                add("join", f"JOIN {e['from_table']}", insert, "foreign key")

    if clause == "JOIN":
        for t in tables:
            if t not in used:
                add("table", t, t, "join table")

    if clause == "ON" and used:
        for e in edges:
            if e["from_table"] in used or e["to_table"] in used:
                cond = (
                    f"{e['from_table']}.{e['from_col']} = "
                    f"{e['to_table']}.{e['to_col']}"
                )
                add("snippet", cond, cond, "join condition")

    if clause == "WHERE":
        add("keyword", "AND", "AND ", "extra filter")
        add("keyword", "OR", "OR ", "alternate filter")
        add("snippet", "LIKE", "LIKE '%'", "text match")
        add("snippet", "IN (...)", "IN ()", "list of values")
        for t in used or tables:
            for col in columns.get(t, []):
                add("column", f"{t}.{col['name']}", f"{t}.{col['name']}", col["type"])

    if clause == "GROUP BY":
        add("keyword", "HAVING", "HAVING ", "filter groups")
        add("keyword", "ORDER BY", "ORDER BY ", "sort")
        for t in used or tables:
            for col in columns.get(t, []):
                add("column", col["name"], col["name"], t)

    if clause == "ORDER BY":
        add("keyword", "ASC", "ASC", "low to high")
        add("keyword", "DESC", "DESC", "high to low")
        add("keyword", "LIMIT 20", "LIMIT 20", "cap rows")
        for t in used or tables:
            for col in columns.get(t, []):
                add("column", col["name"], col["name"], t)

    # Deduplicate by label while keeping order
    seen_labels = set()
    unique = []
    for it in items:
        key = (it["kind"], it["label"])
        if key in seen_labels:
            continue
        seen_labels.add(key)
        unique.append(it)
    return unique[:18]


def _col(table: str, name: str, use_alias: bool) -> str:
    if use_alias:
        return f"{ALIASES[table]}.{name}"
    return name


def natural_language_to_sql(question: str, schema: dict) -> dict:
    """
    Convert a plain-English question into SQL for this school database.
    Returns {sql, explanation, ok, examples}.
    """
    raw = (question or "").strip()
    if not raw:
        return {
            "ok": False,
            "sql": "",
            "explanation": "Type a question in words, e.g. “how many students per class”.",
            "examples": _examples(),
        }

    q = raw.lower()
    q = q.replace("?", " ").replace("'", " ")
    q = re.sub(r"\s+", " ", q).strip()

    # High-value canned patterns (match the sample queries)
    canned = _canned_sql(q)
    if canned:
        return canned

    tables: list[str] = []
    for word, table in TABLE_SYNONYMS.items():
        if re.search(rf"\b{re.escape(word)}\b", q) and table not in tables:
            tables.append(table)

    filters: list[tuple[str, str, str, str]] = []
    for pat, table, col, val in VALUE_FILTERS:
        if re.search(pat, q):
            filters.append((table, col, "=", val))
            if table not in tables:
                tables.append(table)

    for subj in SUBJECTS:
        if subj.lower() in q:
            filters.append(("teachers", "subject", "=", subj))
            if "teachers" not in tables:
                tables.append("teachers")

    grade_m = re.search(r"\bgrade\s*(\d{1,2})\s*[-]?\s*([a-d])?\b", q)
    if grade_m:
        g = int(grade_m.group(1))
        sec = grade_m.group(2)
        if "classes" not in tables:
            tables.append("classes")
        if sec:
            filters.append(("classes", "class_name", "=", f"Grade {g}-{sec.upper()}"))
        else:
            filters.append(("classes", "grade_level", "=", str(g)))
        if "student" in q or "pupil" in q or "kid" in q:
            if "students" not in tables:
                tables.append("students")

    group_table, group_col = None, None
    for pat, gtable, gcol in GROUP_HINTS:
        if re.search(pat, q):
            group_col = gcol
            group_table = gtable
            if gtable and gtable not in tables:
                tables.append(gtable)
            break

    if group_col == "status" and group_table is None:
        if "attendance" in tables:
            group_table = "attendance"
        elif "fees" in tables:
            group_table, group_col = "fees", "payment_status"
        elif "students" in tables:
            group_table = "students"
        else:
            group_table = "attendance"
            if "attendance" not in tables:
                tables.append("attendance")

    agg_fn, agg_col, agg_alias = None, None, None
    if re.search(r"\bhow many\b|\bcount\b|\bnumber of\b|\btotal number\b", q):
        agg_fn, agg_col, agg_alias = "COUNT", "*", "total"
    elif re.search(r"\baverage\b|\bavg\b|\bmean\b", q):
        if "salary" in q or "teachers" in tables:
            agg_fn, agg_col, agg_alias = "AVG", "salary", "avg_salary"
            if "teachers" not in tables:
                tables.append("teachers")
        elif "fees" in tables or "amount" in q or "fee" in q:
            agg_fn, agg_col, agg_alias = "AVG", "amount", "avg_amount"
            if "fees" not in tables:
                tables.append("fees")
        else:
            agg_fn, agg_col, agg_alias = "AVG", "salary", "avg_value"
    elif re.search(r"\btotal\b|\bsum\b|\bcollected\b", q) and (
        "fee" in q or "amount" in q or "paid" in q or "fees" in tables
    ):
        agg_fn, agg_col, agg_alias = "SUM", "amount", "total_amount"
        if "fees" not in tables:
            tables.append("fees")
    elif re.search(r"\bhighest\b|\bmaximum\b|\bmax\b", q) and "salary" in q:
        agg_fn, agg_col, agg_alias = "MAX", "salary", "max_salary"
        if "teachers" not in tables:
            tables.append("teachers")
    elif re.search(r"\blowest\b|\bminimum\b|\bmin\b", q) and "salary" in q:
        agg_fn, agg_col, agg_alias = "MIN", "salary", "min_salary"
        if "teachers" not in tables:
            tables.append("teachers")

    # “per/by/each” without explicit group still implies grouping if we have a hint
    if agg_fn and group_col is None and re.search(r"\b(per|each|by|wise)\b", q):
        if "class" in q:
            group_table, group_col = "classes", "class_name"
            if "classes" not in tables:
                tables.append("classes")
            if "students" not in tables and agg_fn == "COUNT":
                tables.append("students")

    names_only = bool(re.search(r"\bnames?\b", q)) and not agg_fn

    order_col, order_dir = None, None
    if re.search(r"\bhighest\b|\btop\b|\bmost\b|\bdesc(?:ending)?\b", q):
        order_dir = "DESC"
    elif re.search(r"\blowest\b|\bleast\b|\bcheapest\b|\basc(?:ending)?\b", q):
        order_dir = "ASC"
    if "salary" in q:
        order_col = ("teachers", "salary")
        if "teachers" not in tables:
            tables.append("teachers")
    elif "amount" in q or ("fee" in q and order_dir):
        order_col = ("fees", "amount")
        if "fees" not in tables:
            tables.append("fees")

    limit = None
    lim = re.search(r"\b(?:top|first|last|limit)\s+(\d{1,4})\b", q)
    if lim:
        limit = int(lim.group(1))
        if order_dir is None:
            order_dir = "DESC"
    elif re.search(r"\btop\b|\bhighest\b|\blowest\b", q) and not agg_fn:
        limit = 10

    if not tables:
        return {
            "ok": False,
            "sql": "",
            "explanation": (
                "I could not tell which table you mean. Mention students, "
                "teachers, classes, attendance, or fees."
            ),
            "examples": _examples(),
        }

    # If grouping by class for a student count, keep both tables
    if group_table and group_table not in tables:
        tables.append(group_table)

    for ft, *_ in filters:
        if ft not in tables:
            tables.append(ft)

    # Stable table order for joins
    preferred = ["students", "classes", "teachers", "attendance", "fees"]
    tables = [t for t in preferred if t in tables]

    use_alias = len(tables) > 1
    from_sql = JOIN_FROM.get(frozenset(tables))
    if from_sql is None:
        if len(tables) == 1:
            from_sql = tables[0]
            use_alias = False
        else:
            return {
                "ok": False,
                "sql": "",
                "explanation": (
                    f"I understood tables {', '.join(tables)} but cannot join them yet. "
                    "Try a simpler question, or write SQL on the left."
                ),
                "examples": _examples(),
            }

    select_sql = None
    if agg_fn:
        if agg_col == "*":
            agg_expr = f"{agg_fn}(*) AS {agg_alias}"
        else:
            atable = "teachers" if agg_col == "salary" else "fees"
            if atable not in tables:
                atable = tables[0]
            agg_expr = f"{agg_fn}({_col(atable, agg_col, use_alias)}) AS {agg_alias}"
        if group_col:
            gtable = group_table or tables[0]
            if gtable not in tables:
                gtable = tables[0]
            gexpr = _col(gtable, group_col, use_alias)
            select_sql = f"{gexpr}, {agg_expr}"
        else:
            select_sql = agg_expr
    elif names_only and len(tables) == 1:
        name_table = tables[0]
        name_col = "full_name" if name_table in ("students", "teachers") else "class_name"
        select_sql = _col(name_table, name_col, use_alias)
    else:
        select_sql = NICE_SELECT.get(frozenset(tables), "*")

    where_parts = []
    for table, col, op, val in filters:
        left = _col(table, col, use_alias)
        if op == "=":
            if val.isdigit():
                where_parts.append(f"{left} = {val}")
            else:
                where_parts.append(f"{left} = '{val}'")
        else:
            where_parts.append(f"{left} {op} {val}")

    sql_parts = [f"SELECT {select_sql}", f"FROM {from_sql}"]
    if where_parts:
        sql_parts.append("WHERE " + " AND ".join(where_parts))
    if agg_fn and group_col:
        gtable = group_table or tables[0]
        sql_parts.append(f"GROUP BY {_col(gtable, group_col, use_alias)}")
    if order_col and not agg_fn:
        ot, oc = order_col
        if ot in tables:
            sql_parts.append(f"ORDER BY {_col(ot, oc, use_alias)} {order_dir or 'DESC'}")
    elif agg_fn and group_col:
        sql_parts.append(f"ORDER BY {agg_alias} DESC")
    if limit and not (agg_fn and not group_col):
        sql_parts.append(f"LIMIT {limit}")

    sql = "\n".join(sql_parts) + ";"
    bits = [f"tables: {', '.join(tables)}"]
    if filters:
        bits.append("filters: " + ", ".join(f"{t}.{c}={v}" for t, c, _, v in filters))
    if agg_fn:
        bits.append(f"aggregate: {agg_fn}")
    if group_col:
        bits.append(f"group by: {group_col}")
    return {
        "ok": True,
        "sql": sql,
        "explanation": "Interpreted as " + " · ".join(bits) + ".",
        "examples": _examples(),
    }


def _canned_sql(q: str) -> dict | None:
    pairs = [
        (
            r"student.+(per|by|each) class|class[- ]wise student|students in each class",
            """SELECT c.class_name, COUNT(s.student_id) AS student_count
FROM classes c
LEFT JOIN students s ON s.class_id = c.class_id
GROUP BY c.class_id
ORDER BY student_count DESC;""",
            "Count of students in every class (includes empty classes).",
        ),
        (
            r"attendance by status|attendance summary|present vs absent",
            """SELECT status, COUNT(*) AS total
FROM attendance
GROUP BY status
ORDER BY total DESC;""",
            "Attendance grouped by Present / Absent / Late.",
        ),
        (
            r"fee collection|fees by type|fee summary",
            """SELECT fee_type, payment_status,
       COUNT(*) AS records,
       ROUND(SUM(amount), 2) AS total_amount
FROM fees
GROUP BY fee_type, payment_status
ORDER BY fee_type, payment_status;""",
            "Fee amounts grouped by type and payment status.",
        ),
        (
            r"teachers by subject|teacher.+per subject",
            """SELECT subject, COUNT(*) AS teachers, ROUND(AVG(salary), 2) AS avg_salary
FROM teachers
GROUP BY subject
ORDER BY teachers DESC;""",
            "Teacher count and average salary per subject.",
        ),
        (
            r"daily attendance|attendance trend",
            """SELECT attend_date, status, COUNT(*) AS count
FROM attendance
GROUP BY attend_date, status
ORDER BY attend_date;""",
            "Attendance counts for each day and status.",
        ),
        (
            r"gender distribution|students by gender",
            """SELECT gender, status, COUNT(*) AS total
FROM students
GROUP BY gender, status;""",
            "Student counts by gender and status.",
        ),
    ]
    for pat, sql, expl in pairs:
        if re.search(pat, q):
            return {"ok": True, "sql": sql, "explanation": expl, "examples": _examples()}
    return None


def _examples() -> list[str]:
    return [
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
    ]
