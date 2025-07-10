import os
import sys
import re
import time
import json
import sqlite3
from httpx import ReadTimeout
from openai import OpenAI, APIConnectionError, APIError
from datetime import datetime

# 从外部脚本引入连接池
from database import DBPool

# 初始化 OpenAI 客户端

client = OpenAI(api_key="sk-ubjkrzodjlihepttrgdmmqsxaulmoktrzvmvzzwpkaftmtcn", 
                base_url="https://api.siliconflow.cn/v1")
#client = OpenAI(api_key="sk-3f5e62ce34084f25ba2772f0f2958f75", base_url="https://api.deepseek.com")



def get_schema_and_samples(limit: int = 5) -> tuple[dict, dict]:
    """
    获取数据库表结构(schema)和示例数据(samples)。
    返回: schema: {table: [(col_name, data_type), ...]},
          samples: {table: {'columns': [], 'rows': []}}
    """
    schema: dict = {}
    samples: dict = {}
    with DBPool.get_connection() as conn:
        # 列出表名
        if isinstance(conn, sqlite3.Connection):
            table_sql = "SELECT name FROM sqlite_master WHERE type='table';"
        elif 'psycopg2' in str(type(conn)):
            table_sql = "SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname='public';"
        else:
            table_sql = "SHOW TABLES;"

        cur = conn.cursor()
        cur.execute(table_sql)
        tables = [r[0] for r in cur.fetchall()]
        cur.close()

        for tbl in tables:
            cur = conn.cursor()
            # 获取列信息
            if isinstance(conn, sqlite3.Connection):
                cur.execute(f"PRAGMA table_info('{tbl}');")
                cols = [(r[1], r[2]) for r in cur.fetchall()]
            elif 'psycopg2' in str(type(conn)):
                cur.execute(
                    "SELECT column_name, data_type FROM information_schema.columns WHERE table_name=%s;",
                    (tbl,)
                )
                cols = cur.fetchall()
            else:
                cur.execute(f"DESCRIBE {tbl};")
                cols = [(r[0], r[1]) for r in cur.fetchall()]
            schema[tbl] = cols

            # 获取示例数据
            cur.execute(f"SELECT * FROM {tbl} LIMIT {limit}")
            rows = cur.fetchall()
            cols_names = [d[0] for d in cur.description] if cur.description else []
            samples[tbl] = {'columns': cols_names, 'rows': rows}
            cur.close()

    return schema, samples


def extract_sql(script: str) -> str:
    """
    从模型返回的脚本文本中提取纯 SQL 部分。
    """
    # 假设 SQL 语句位于 ```sql 块中或纯文本
    parts = re.split(r"```(?:sql)?", script)
    if len(parts) >= 3:
        return parts[1].strip()
    return script.strip()


def get_sql(requirement: str, model: str = 'deepseek-reasoner', max_retries: int = 2) -> str:
    """
    根据需求(requirement)生成对应的 SQL 语句。
    返回生成的 SQL 文本。
    """
    schema, samples = get_schema_and_samples()
    prompt = (
        "# 数据库 schema:\n"
        f"{json.dumps(schema, indent=2)}\n\n"
        "# 示例数据 (每表前几行):\n"
        f"{json.dumps(samples, indent=2, default=str)}\n\n"
        "# 请根据以下需求生成完整的、可直接运行的SQL脚本,无需其他格式内容"
        "\n\n"
        f"需求: {requirement}\n"
    )
    backoff = 1.0
    for attempt in range(1, max_retries + 1):
        try:
            resp = client.chat.completions.create(
                # model='Pro/deepseek-ai/DeepSeek-R1',
                model="Qwen/Qwen2.5-72B-Instruct",
                messages=[
                    {'role': 'system', 'content': '你是数据库操作专家。'},
                    {'role': 'user', 'content': prompt}
                ],
                timeout=300
            )
            '''
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {'role': 'system', 'content': '你是数据库操作专家。'},
                    {'role': 'user', 'content': prompt}
                ],
                timeout=300
            )
            '''
            content = resp.choices[0].message.content
            return extract_sql(content)
        except (APIConnectionError, APIError, ReadTimeout) as e:
            if attempt == max_retries:
                raise
            time.sleep(backoff)
            backoff *= 2
