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
            auto_inc_columns = []  # 新增：存储自增列信息

            # SQLite
            if isinstance(conn, sqlite3.Connection):
                # ... 前面的代码保持不变 ...
                
                # 在列信息循环中添加自增识别
                cur.execute(f"PRAGMA table_info('{tbl}');")
                col_rows = cur.fetchall()
                # 识别自增主键列
                pk_columns = [row for row in col_rows if row[5] > 0]  # 第5列是pk值
                pk_count = len(pk_columns)
                for cid, name, ctype, notnull, dflt, pk in col_rows:
                    is_auto_increment = False
                    # SQLite的自增主键识别：单列主键且类型为INTEGER
                    if pk > 0 and pk_count == 1 and ctype.upper() in ['INTEGER', 'INT']:
                        is_auto_increment = True
                        auto_inc_columns.append(name)
                    
                    cols_info.append({
                        'column': name,
                        'type': ctype,
                        'not_null': bool(notnull),
                        'default': dflt,
                        'is_primary': bool(pk),
                        'is_foreign': False,
                        'references': None,
                        'is_auto_increment': is_auto_increment  # 新增字段
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
                    is_auto_increment = False
                    # PostgreSQL的自增识别：serial类型或默认值包含nextval
                    if dtype.lower() in ['serial', 'bigserial', 'smallserial'] or \
                    (dflt and 'nextval' in dflt):
                        is_auto_increment = True
                        auto_inc_columns.append(name)
                    
                    cols_info.append({
                        'column': name,
                        'type': dtype,
                        'not_null': not notnull,  # 注意：这里原代码有误，应保持不变
                        'default': dflt,
                        'is_primary': is_pk,
                        'is_foreign': False,
                        'references': None,
                        'is_auto_increment': is_auto_increment  # 新增字段
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
                    is_auto_increment = False
                    # MySQL的自增识别：extra字段包含auto_increment
                    if extra and 'auto_increment' in extra.lower():
                        is_auto_increment = True
                        auto_inc_columns.append(name)
                    
                    cols_info.append({
                        'column': name,
                        'type': ctype,
                        'not_null': (null == 'NO'),
                        'default': dflt,
                        'is_primary': (key == 'PRI'),
                        'is_foreign': False,
                        'references': None,
                        'is_auto_increment': is_auto_increment  # 新增字段
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
def remove_auto_increment_columns(sql: str, schema: dict) -> str:
    """
    移除INSERT语句中的自增主键列
    """
    # 匹配INSERT INTO语句
    pattern = r"INSERT\s+INTO\s+(\w+)\s*\(([^)]+)\)\s*VALUES\s*(\([^)]+\))(?:\s*,\s*\([^)]+\))*\s*;"
    match = re.search(pattern, sql, re.IGNORECASE)
    if not match:
        return sql  # 不是标准INSERT语句，直接返回

    table_name = match.group(1)
    columns_str = match.group(2)
    values_str = match.group(3)

    # 获取该表的自增列列表
    if table_name not in schema:
        return sql
    auto_inc_columns = [col['column'] for col in schema[table_name]['columns'] 
                      if col.get('is_auto_increment', False)]

    if not auto_inc_columns:
        return sql

    # 解析列名
    cols = [col.strip() for col in columns_str.split(',')]
    # 移除自增列
    new_cols = []
    removed_indices = []
    for idx, col in enumerate(cols):
        if col in auto_inc_columns:
            removed_indices.append(idx)
        else:
            new_cols.append(col)

    if not removed_indices:
        return sql

    # 解析值列表并移除对应位置的值
    values = [v.strip() for v in values_str.strip('()').split(',')]
    new_values = [val for idx, val in enumerate(values) 
                if idx not in removed_indices]

    # 重建SQL语句
    new_cols_str = ', '.join(new_cols)
    new_values_str = '(' + ', '.join(new_values) + ')'
    new_sql = sql.replace(columns_str, new_cols_str, 1)
    new_sql = new_sql.replace(values_str, new_values_str, 1)
    return new_sql

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
            "1. 使用明确的列名而不是SELECT *\n"
            "2. 大表查询添加LIMIT限制\n"
            "3. 注意JOIN条件避免笛卡尔积\n\n"
        )
    }
        # 构建自增列提示信息
    auto_inc_prompt = ""
    for table_name, table_info in schema.items():
        auto_inc_cols = [col['column'] for col in table_info['columns'] 
                        if col.get('is_auto_increment', False)]
        if auto_inc_cols:
            auto_inc_prompt += f"表 '{table_name}' 有自增主键列: {', '.join(auto_inc_cols)}，在INSERT语句中不要包含这些列。\n"
    
    if auto_inc_prompt:
        auto_inc_prompt = "### 自增主键列提示（不要插入）:\n" + auto_inc_prompt + "\n"
    

    # 构建基础提示词
    base_prompt = (
        "# 数据库 schema:\n"
        f"{json.dumps(schema, indent=2)}\n\n"
        "# 示例数据 (每表前几行):\n"
        f"{json.dumps(samples, indent=2, default=str)}\n\n"
        "# 请根据以下需求生成完整的、可直接运行的SQL脚本,无需其他格式内容\n\n"
        f"{auto_inc_prompt}"  # 新增的自增列提示
        f"### 检测到的操作类型: {operation_type}\n"
        f"{operation_prompts[operation_type]}"
        f"需求: {requirement}\n"
    )
    # 第一步：生成任务规划
    planning_prompt = (
        f"{base_prompt}\n"
        "### 任务规划步骤:\n"
        "1. 请先生成一个详细的任务规划，包括：\n"
        "   - 理解需求的关键点\n"
        "   - 确定需要使用的表和字段\n"
        "   - 考虑必要的JOIN操作\n"
        "   - 考虑过滤条件和排序要求\n"
        "2. 规划完成后，再生成SQL语句"
    )
    #输出提示词
    #print("\n\n"+prompt+"\n\n")
    # 尝试生成任务规划
    plan = None
    try:
        plan_resp = client.chat.completions.create(
            model="Qwen/Qwen2.5-72B-Instruct",
            messages=[
                {'role': 'system', 'content': '你是数据库操作专家。'},
                {'role': 'user', 'content': planning_prompt}
            ],
            timeout=120
        )
        plan = plan_resp.choices[0].message.content
    except Exception as e:
        print(f"生成任务规划时出错: {str(e)}")
    print(plan)
    # 构建最终提示词（包含规划）
    final_prompt = base_prompt
    if plan:
        final_prompt += (
            "\n### 任务规划（由AI生成）:\n"
            f"{plan}\n\n"
            "请基于以上规划生成SQL语句:"
        )
    
    backoff = 1.0
    sql = None
    error_occurred = False
    error_message = ""
    
    for attempt in range(1, max_retries + 1):
        try:
            # 如果是重试且有错误信息，添加到提示词中
            retry_prompt = final_prompt
            if error_occurred:
                retry_prompt = (
                    f"{final_prompt}\n\n"
                    "### 上次生成的SQL执行出错，请修正:\n"
                    f"错误信息: {error_message}\n"
                    f"上次生成的SQL: {sql}\n"
                    "请分析错误原因并生成修正后的SQL:"
                )
            
            # 调用AI生成SQL
            resp = client.chat.completions.create(
                model="Qwen/Qwen2.5-72B-Instruct",
                messages=[
                    {'role': 'system', 'content': '你是数据库操作专家。'},
                    {'role': 'user', 'content': retry_prompt}
                ],
                timeout=300
            )
            content = resp.choices[0].message.content
            sql = extract_sql(content)
            
            # 后处理：如果是INSERT语句，移除自增列
            if operation_type == "INSERT":
                sql = remove_auto_increment_columns(sql, schema)
            if isinstance(DBPool.get_connection(), sqlite3.Connection):
                # 1) 把 LPAD(TO_HEX(...),5,'0') 换成 printf
                sql = re.sub(
                    r"LPAD\s*\(\s*TO_HEX\s*\(\s*([^)]+)\)\s*,\s*5\s*,\s*'0'\s*\)",
                    r"printf('%05X', abs(\1) % 1048576)",
                    sql,
                    flags=re.IGNORECASE
                )
                # 2) 把 PostgreSQL 式的 round(x,2) 换成 SQLite 式
                sql = re.sub(
                    r"ROUND\s*\(\s*([^)]+)\s*,\s*2\s*\)",
                    r"ROUND(\1, 2)",
                    sql,
                    flags=re.IGNORECASE
                )
            # 测试生成的SQL（不实际执行，只验证语法）
            try:
                with DBPool.get_connection() as conn:
                    cur = conn.cursor()
                    if operation_type.upper() == "SELECT":
                        # 用 EXPLAIN 来校验查询语法
                        explain_sql = f"EXPLAIN {sql}" if "EXPLAIN" not in sql.upper() else sql
                        cur.execute(explain_sql)
                        _ = cur.fetchall()
                    else:
                        # 对于 INSERT/UPDATE/DELETE，开个 SAVEPOINT，执行后回滚
                        cur.execute("SAVEPOINT validate_sp;")
                        cur.execute(sql)
                        cur.execute("ROLLBACK TO SAVEPOINT validate_sp;")
                    cur.close()
                # 验证通过，返回 SQL
                return sql
            except Exception as e:
                error_occurred = True
                error_message = str(e)
                print(f"SQL验证失败（尝试 {attempt}/{max_retries}）: {error_message}")
                if attempt == max_retries:
                    raise ValueError(f"最终生成的SQL验证失败: {error_message}")
        
        except (APIConnectionError, APIError, ReadTimeout, ValueError) as e:
            # 如果是最后一次尝试，直接抛出异常
            if attempt == max_retries:
                raise
            # 记录错误信息
            error_occurred = True
            error_message = str(e)
            print(f"API调用失败（尝试 {attempt}/{max_retries}）: {error_message}")
            time.sleep(backoff)
            backoff *= 2
    
    return sql