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
    返回: schema: {table: [{...col_info..., 'uniques': [...], 'checks': [...]}]},
          samples: {table: {'columns': [], 'rows': []}}
    """
    schema: dict = {}
    samples: dict = {}

    with DBPool.get_connection() as conn:
        # 列出表名
        if isinstance(conn, sqlite3.Connection):
            table_sql = "SELECT name FROM sqlite_master WHERE type='table';"
            quote = '"'
        elif 'psycopg2' in str(type(conn)):
            table_sql = "SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname='public';"
            quote = '"'
        else:
            table_sql = "SHOW TABLES;"
            quote = '`'

        cur = conn.cursor()
        cur.execute(table_sql)
        tables = [r[0] for r in cur.fetchall()]
        cur.close()

        for tbl in tables:
            cur = conn.cursor()
            cols_info = []
            uniques = []
            checks = []

            # SQLite
            if isinstance(conn, sqlite3.Connection):
                # 列信息
                cur.execute(f"PRAGMA table_info('{tbl}');")
                col_rows = cur.fetchall()
                for cid, name, ctype, notnull, dflt, pk in col_rows:
                    cols_info.append({
                        'column': name,
                        'type': ctype,
                        'not_null': bool(notnull),
                        'default': dflt,
                        'is_primary': bool(pk),
                        'is_foreign': False,
                        'references': None
                    })
                # 外键
                cur.execute(f"PRAGMA foreign_key_list('{tbl}');")
                fk_rows = cur.fetchall()
                for fk in fk_rows:
                    _, _, ref_table, from_col, to_col, *_ = fk
                    for col in cols_info:
                        if col['column'] == from_col:
                            col['is_foreign'] = True
                            col['references'] = {'table': ref_table, 'column': to_col}
                # 唯一约束 via index
                cur.execute(f"PRAGMA index_list('{tbl}')")
                for idx_name, unique, *rest in cur.fetchall():
                    if unique:
                        cur.execute(f"PRAGMA index_info('{idx_name}')")
                        idx_cols = [r[2] for r in cur.fetchall()]
                        uniques.append({'index': idx_name, 'columns': idx_cols})
                # 检查约束 via 表创建SQL
                cur.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{tbl}';")
                create_sql = cur.fetchone()[0] or ''
                import re
                for match in re.finditer(r'CHECK\s*\(([^)]+)\)', create_sql, re.IGNORECASE):
                    checks.append(match.group(1).strip())

            # PostgreSQL
            elif 'psycopg2' in str(type(conn)):
                # 列、PK、NOT NULL、DEFAULT
                cur.execute(
                    "SELECT a.attname, format_type(a.atttypid,a.atttypmod), a.attnotnull,"
                    " pg_get_expr(d.adbin, d.adrelid) AS default_val,"
                    " t.constraint_type = 'PRIMARY KEY' AS is_pk"
                    " FROM pg_attribute a"
                    " LEFT JOIN pg_attrdef d ON a.attrelid = d.adrelid AND a.attnum = d.adnum"
                    " LEFT JOIN ("
                    "   SELECT kcu.column_name, tc.constraint_type"
                    "   FROM information_schema.table_constraints tc"
                    "   JOIN information_schema.key_column_usage kcu"
                    "     ON tc.constraint_name = kcu.constraint_name"
                    "   WHERE tc.constraint_type = 'PRIMARY KEY' AND tc.table_name = %s"
                    " ) t ON a.attname = t.column_name"
                    " WHERE a.attrelid = %s::regclass AND a.attnum>0 AND NOT a.attisdropped;",
                    (tbl, tbl)
                )
                for name, dtype, notnull, dflt, is_pk in cur.fetchall():
                    cols_info.append({
                        'column': name,
                        'type': dtype,
                        'not_null': not notnull,
                        'default': dflt,
                        'is_primary': is_pk,
                        'is_foreign': False,
                        'references': None
                    })
                # 外键
                cur.execute(
                    "SELECT kcu.column_name, ccu.table_name, ccu.column_name"
                    " FROM information_schema.table_constraints tc"
                    " JOIN information_schema.key_column_usage kcu ON tc.constraint_name=kcu.constraint_name"
                    " JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name=tc.constraint_name"
                    " WHERE tc.constraint_type='FOREIGN KEY' AND tc.table_name=%s;",
                    (tbl,)
                )
                for col_name, f_table, f_col in cur.fetchall():
                    for col in cols_info:
                        if col['column'] == col_name:
                            col['is_foreign'] = True
                            col['references'] = {'table': f_table, 'column': f_col}
                # UNIQUE
                cur.execute(
                    "SELECT kcu.column_name"
                    " FROM information_schema.table_constraints tc"
                    " JOIN information_schema.key_column_usage kcu ON tc.constraint_name=kcu.constraint_name"
                    " WHERE tc.constraint_type='UNIQUE' AND tc.table_name=%s;",
                    (tbl,)
                )
                uniques = [r[0] for r in cur.fetchall()]
                # CHECK
                cur.execute(
                    "SELECT cc.check_clause"
                    " FROM information_schema.check_constraints cc"
                    " JOIN information_schema.table_constraints tc ON cc.constraint_name=tc.constraint_name"
                    " WHERE tc.constraint_type='CHECK' AND tc.table_name=%s;",
                    (tbl,)
                )
                checks = [r[0] for r in cur.fetchall()]

            # MySQL
            else:
                # 列、PK、NOT NULL、DEFAULT
                cur.execute(f"SHOW COLUMNS FROM {quote}{tbl}{quote};")
                for name, ctype, null, key, dflt, extra in cur.fetchall():
                    cols_info.append({
                        'column': name,
                        'type': ctype,
                        'not_null': (null == 'NO'),
                        'default': dflt,
                        'is_primary': (key == 'PRI'),
                        'is_foreign': False,
                        'references': None
                    })
                # 外键
                cur.execute(
                    "SELECT column_name, referenced_table_name, referenced_column_name"
                    " FROM information_schema.key_column_usage"
                    " WHERE table_schema=DATABASE() AND table_name=%s AND referenced_table_name IS NOT NULL;",
                    (tbl,)
                )
                for col_name, f_table, f_col in cur.fetchall():
                    for col in cols_info:
                        if col['column'] == col_name:
                            col['is_foreign'] = True
                            col['references'] = {'table': f_table, 'column': f_col}
                # UNIQUE
                cur.execute(
                    "SELECT kcu.COLUMN_NAME"
                    " FROM information_schema.TABLE_CONSTRAINTS tc"
                    " JOIN information_schema.KEY_COLUMN_USAGE kcu ON tc.CONSTRAINT_NAME=kcu.CONSTRAINT_NAME"
                    " WHERE tc.CONSTRAINT_TYPE='UNIQUE' AND tc.TABLE_NAME=%s AND tc.TABLE_SCHEMA=DATABASE();",
                    (tbl,)
                )
                uniques = [r[0] for r in cur.fetchall()]
                # CHECK
                cur.execute(
                    "SELECT cc.CHECK_CLAUSE"
                    " FROM information_schema.CHECK_CONSTRAINTS cc"
                    " JOIN information_schema.TABLE_CONSTRAINTS tc ON cc.CONSTRAINT_NAME=tc.CONSTRAINT_NAME"
                    " WHERE tc.CONSTRAINT_TYPE='CHECK' AND tc.TABLE_NAME=%s AND tc.TABLE_SCHEMA=DATABASE();",
                    (tbl,)
                )
                checks = [r[0] for r in cur.fetchall()]

            # 组织结果
            schema[tbl] = {
                'columns': cols_info,
                'uniques': uniques,
                'checks': checks
            }

            # 获取示例数据
            sample_query = f"SELECT * FROM {quote}{tbl}{quote} LIMIT {limit};"
            cur.execute(sample_query)
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
    
    # 操作类型检测
    operation_type = "SELECT"  # 默认查询操作
    operation_keywords = {
        "INSERT": ["插入", "新增", "增加", "添加", "创建", "新建", "insert", "add", "create"],
        "DELETE": ["删", "删除", "移除", "去掉", "del", "delete", "remove"],
        "UPDATE": ["更新", "修改", "编辑", "update", "change", "modify", "edit"],
        "SELECT": ["查", "查询", "查找", "搜索", "列出", "显示", "select", "search", "find", "list", "show"]
    }
    
    # 检测操作类型
    req_lower = requirement.lower()
    for op, keywords in operation_keywords.items():
        if any(keyword in req_lower for keyword in keywords):
            operation_type = op
            break
    
    # 根据操作类型添加特定提示
    operation_prompts = {
        "INSERT": (
            "### 重要提示: \n"
            "1. 如果表中有自增主键(如id)，不要在INSERT语句中指定自增主键列\n"
            "2. 插入应插入在空位"
            "3. 不要为自增主键提供值\n"
            "4. 只需列出需要插入的列名和值\n\n"
        ),
        "UPDATE": (
            "### 重要提示: \n"
            "1. 更新操作必须包含WHERE条件\n"
            "2. WHERE条件应该足够具体，避免更新过多记录\n"
            "3. 不要尝试更新主键值\n\n"
        ),
        "DELETE": (
            "### 重要提示: \n"
            "1. 删除操作必须包含WHERE条件\n"
            "2. WHERE条件应该足够具体，避免删除过多记录\n"
            "3. 考虑使用软删除(更新状态字段)而不是物理删除\n\n"
        ),
        "SELECT": (
            "### 重要提示: \n"
            "1. 尽可能给出所有的信息\n"
            "2. 注意JOIN条件避免笛卡尔积\n"
            "3. 尽可能使用模糊查询\n"
        )
    }
    
    # 构建提示词
    prompt = (
        "# 数据库 schema:\n"
        f"{json.dumps(schema, indent=2)}\n\n"
        "# 示例数据 (每表前几行):\n"
        f"{json.dumps(samples, indent=2, default=str)}\n\n"
        "# 请根据以下需求生成完整的、可直接运行的SQL脚本,无需其他格式内容\n\n"
        f"### 检测到的操作类型: {operation_type}\n"
        f"{operation_prompts[operation_type]}"
        f"需求: {requirement}\n"
    )
    #输出提示词
    #print("\n\n"+prompt+"\n\n")
    backoff = 1.0
    for attempt in range(1, max_retries + 1):
        try:
            resp = client.chat.completions.create(
                model="Qwen/Qwen2.5-72B-Instruct",
                messages=[
                    {'role': 'system', 'content': '你是数据库操作专家。'},
                    {'role': 'user', 'content': prompt}
                ],
                timeout=300
            )
            content = resp.choices[0].message.content
            return extract_sql(content)
        except (APIConnectionError, APIError, ReadTimeout) as e:
            if attempt == max_retries:
                raise
            time.sleep(backoff)
            backoff *= 2