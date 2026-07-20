import os
import json
import dlt
from dotenv import load_dotenv
from logfire.experimental.query_client import LogfireQueryClient


load_dotenv(".env", override=True)

read_token = os.getenv("LOGFIRE_READ_TOKEN")

print("Read token exists:", read_token is not None)
print("Read token length:", len(read_token) if read_token else 0)

client = LogfireQueryClient(read_token=read_token)


def parse_value(value):
    if isinstance(value, str):
        value_clean = value.strip()

        if value_clean.startswith("{") or value_clean.startswith("["):
            try:
                return json.loads(value_clean)
            except json.JSONDecodeError:
                return value

    return value


def columnar_to_rows(data):
    columns = data["columns"]

    column_names = [column["name"] for column in columns]
    column_values = [column["values"] for column in columns]

    row_count = len(column_values[0])

    rows = []

    for i in range(row_count):
        row = {}

        for name, values in zip(column_names, column_values):
            row[name] = parse_value(values[i])

        rows.append(row)

    return rows


data = client.query_json("SELECT * FROM records")

print("Data type:", type(data))
print("Data keys:", data.keys())
print("Columns count:", len(data["columns"]))
print("First column name:", data["columns"][0]["name"])

rows = columnar_to_rows(data)

print("Rows prepared:", len(rows))
print("First row type:", type(rows[0]))
print("First row keys:", list(rows[0].keys())[:10])

pipeline = dlt.pipeline(
    pipeline_name="logfire_pipeline",
    destination="duckdb",
    dataset_name="agent_traces"
)

load_info = pipeline.run(
    rows,
    table_name="traces",
    write_disposition="replace"
)

print(load_info)
