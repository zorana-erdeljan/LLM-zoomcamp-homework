import duckdb
import pandas as pd
import re
import json
import ast

DB_PATH = "logfire_pipeline.duckdb"
SCHEMA = "agent_traces"
TABLE = "traces"

conn = duckdb.connect(DB_PATH)

df = conn.sql(f"""
SELECT *
FROM {SCHEMA}.{TABLE}
""").df()

print("Rows:", len(df))
print("Columns:", len(df.columns))

# 1. Pronađi moguće kolone za ime spana
name_candidates = [
    col for col in df.columns
    if "name" in col.lower()
]

name_col = None

for col in name_candidates:
    values = df[col].astype(str)
    if values.str.contains("chat|gpt|llm|openai|agent|tool|search", case=False, na=False).any():
        name_col = col
        break

print("\nName candidates:")
for col in name_candidates:
    print(" -", col)

print("\nChosen name_col:", name_col)

# 2. Pronađi moguće input token kolone
input_token_cols = [
    col for col in df.columns
    if "input" in col.lower()
    and "token" in col.lower()
]

usage_token_cols = [
    col for col in df.columns
    if "token" in col.lower()
    or "usage" in col.lower()
    or "gen_ai" in col.lower()
    or "attributes" in col.lower()
]

print("\nInput token column candidates:")
for col in input_token_cols:
    print(" -", col)

print("\nAll usage/token/gen_ai/attributes candidates:")
for col in usage_token_cols:
    print(" -", col)

# 3. Ako postoji direktna input token kolona, koristi nju
def range_answer(total):
    if 100 <= total <= 500:
        return "100 - 500"
    if 1500 <= total <= 5000:
        return "1500 - 5000"
    if 10000 <= total <= 20000:
        return "10000 - 20000"
    if 50000 <= total <= 100000:
        return "50000 - 100000"
    return "outside listed ranges"

if input_token_cols:
    input_col = input_token_cols[0]
    print("\nChosen input_col:", input_col)

    if name_col:
        llm_df = df[
            df[name_col].astype(str).str.contains("chat|gpt|llm|openai", case=False, na=False)
        ].copy()
    else:
        llm_df = df.copy()

    print("\nLLM rows used:")
    cols_to_show = []
    for col in ["trace_id", "span_id", name_col, input_col]:
        if col and col in llm_df.columns and col not in cols_to_show:
            cols_to_show.append(col)

    print(llm_df[cols_to_show].to_string(index=False))

    total = pd.to_numeric(llm_df[input_col], errors="coerce").fillna(0).sum()

    print("\nTotal input tokens:", int(total))
    print("Q3 answer:", range_answer(total))
    raise SystemExit

# 4. Ako nema direktne input token kolone, traži u vrednostima svih kolona
print("\nNo direct input token column found. Searching inside values...")

patterns = [
    r"gen_ai\.usage\.input_tokens['\"]?\s*[:=]\s*(\d+)",
    r"input_tokens['\"]?\s*[:=]\s*(\d+)",
    r"input tokens['\"]?\s*[:=]\s*(\d+)",
]

def parse_possible(value):
    if isinstance(value, (dict, list)):
        return value

    if isinstance(value, str):
        text = value.strip()
        if text.startswith("{") or text.startswith("["):
            try:
                return json.loads(text)
            except Exception:
                try:
                    return ast.literal_eval(text)
                except Exception:
                    return value

    return value

def find_input_tokens(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_text = str(key).lower()

            if (
                "input" in key_text
                and "token" in key_text
            ) or key == "gen_ai.usage.input_tokens":
                try:
                    return int(value)
                except Exception:
                    pass

            nested = find_input_tokens(value)
            if nested is not None:
                return nested

    if isinstance(obj, list):
        for item in obj:
            nested = find_input_tokens(item)
            if nested is not None:
                return nested

    if isinstance(obj, str):
        for pattern in patterns:
            match = re.search(pattern, obj)
            if match:
                return int(match.group(1))

    return None

tokens = []

for idx, row in df.iterrows():
    row_name = ""
    if name_col:
        row_name = str(row.get(name_col, ""))

    # Brojimo samo LLM/chat spanove ako možemo da prepoznamo name kolonu
    if name_col and not re.search("chat|gpt|llm|openai", row_name, re.IGNORECASE):
        continue

    found = None

    for col in df.columns:
        value = parse_possible(row[col])
        found = find_input_tokens(value)
        if found is not None:
            break

    if found is not None:
        tokens.append({
            "row_index": idx,
            "trace_id": row.get("trace_id", None),
            "span_id": row.get("span_id", None),
            "name": row_name,
            "input_tokens": found,
        })

tokens_df = pd.DataFrame(tokens)

print("\nExtracted token rows:")
print(tokens_df.to_string(index=False))

if tokens_df.empty:
    print("\nCould not find input tokens.")
    print("Run this to inspect columns:")
    print("python - <<'PY'")
    print("import duckdb")
    print("conn = duckdb.connect('logfire_pipeline.duckdb')")
    #print("print(conn.sql("DESCRIBE agent_traces.traces").df().to_string())")
    print("PY")
    raise SystemExit

total = tokens_df["input_tokens"].sum()

print("\nTotal input tokens:", int(total))
print("Q3 answer:", range_answer(total))
