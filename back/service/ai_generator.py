import os
import sys
import re
import time
import json
import shutil
import subprocess
import sqlite3
from httpx import ReadTimeout
from openai import OpenAI, APIConnectionError, APIError
from datetime import datetime
from database import DBPool
import openai
import numpy as np
import faiss
import pickle


client = OpenAI(api_key="sk-3f5e62ce34084f25ba2772f0f2958f75", base_url="https://api.deepseek.com")
class NLDatabaseManager:
    def __init__(self, db_path: str, indexer):
        self.db_path = db_path
        self.indexer = indexer
        openai.api_key = client.api_key

    def process_nl(self, command: str):
        # 调用 ChatCompletion 解析 CRUD 指令
        prompt = (
            "将以下自然语言指令解析为 JSON，对应 action(create/read/update/delete),"
            " table, conditions, data 键，无多余文字输出："
            f"\n指令: {command}\nJSON:" )
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role":"user", "content": prompt}]
        )
        parsed = json.loads(resp.choices[0].message.content)
        action = parsed.get("action")
        table = parsed.get("table")
        cond = parsed.get("conditions", "1=1")
        data = parsed.get("data", {})

        # 执行 SQL
        with DBPool.get_connection() as conn:
            cur = conn.cursor()
            if action=="create":
                cols, vals = zip(*data.items())
                placeholders = ",".join(["?" for _ in vals])
                cur.execute(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders})", tuple(vals))
            elif action=="read":
                cur.execute(f"SELECT * FROM {table} WHERE {cond}")
                return cur.fetchall()
            elif action=="update":
                sets = ",".join([f"{k}=?" for k in data])
                cur.execute(f"UPDATE {table} SET {sets} WHERE {cond}", tuple(data.values()))
            elif action=="delete":
                cur.execute(f"DELETE FROM {table} WHERE {cond}")
            else:
                raise ValueError(f"未知操作: {action}")
            conn.commit()

        # 更新向量索引：仅重新索引受影响表
        self.indexer.reindex_table(table)
        self.indexer.save()
        return f"操作 {action} 完成，并更新了 {table} 的向量索引。"

# 在原有的 UniversalDbVectorIndexer 中增加分表重建功能
class UniversalDbVectorIndexer:
    def __init__(self, db_path, openai_api_key, embedding_model="text-embedding-ada-002",
                 index_path="universal_faiss.index", idmap_path="universal_faiss_ids.pkl"):
        self.db_path = db_path
        openai.api_key = openai_api_key
        self.embedding_model = embedding_model
        self.index_path = index_path
        self.idmap_path = idmap_path
        self.index = None
        self.id_map = {}
        self.dimension = 0

    def _init_index(self, dim):
        base = faiss.IndexFlatL2(dim)
        self.index = faiss.IndexIDMap(base)
        self.dimension = dim

    def _embed(self, texts):
        # 简化版 embedding
        resp = openai.Embedding.create(input=texts, model=self.embedding_model)
        return np.array([r.embedding for r in resp.data], dtype='float32')

    def index_all(self):
        # 原 load_and_index 重命名
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [r[0] for r in cur.fetchall()]
        conn.close()
        self.index = None
        self.id_map.clear()
        all_embs, all_ids = [], []
        for tbl in tables:
            embs, ids = self._embed_table(tbl)
            all_embs.append(embs); all_ids.extend(ids)
        all_embs = np.vstack(all_embs)
        self._init_index(all_embs.shape[1])
        self.index.add_with_ids(all_embs, np.array(all_ids))
        for rid in all_ids: self.id_map[rid] = tbl

    def _embed_table(self, table):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(f"PRAGMA table_info('{table}');")
        cols = [c[1] for c in cur.fetchall()]
        cur.execute(f"SELECT * FROM {table};")
        rows = cur.fetchall()
        conn.close()
        texts, ids = [], []
        for r in rows:
            texts.append(" | ".join(str(v) for v in r if v is not None))
            ids.append(abs(hash(f"{table}.{r}")))
        return self._embed(texts), ids

    def reindex_table(self, table):
        # 从现有索引中移除 table 对应的 id
        # 这里只简单重建整个索引，也可按需实现删除
        self.index_all()

    def save(self):
        faiss.write_index(self.index, self.index_path)
        with open(self.idmap_path,'wb') as f: pickle.dump(self.id_map,f)

    def load(self):
        self.index = faiss.read_index(self.index_path)
        with open(self.idmap_path,'rb') as f: self.id_map=pickle.load(f)
        self.dimension = self.index.d

    def search(self, query, top_k=5):
        emb = self._embed([query])
        d, idxs = self.index.search(emb, top_k)
        return [(self.id_map.get(int(i)), float(dist)) for i, dist in zip(idxs[0],d[0])]
def init_db_pool():
    """
    初始化数据库连接池，需要在调用 DBPool.get_connection() 前执行
    """
    db_info = {}
    db_type = input("请选择数据库类型 (sqlite/postgres): ").strip().lower()
    db_info['db_type'] = db_type
    if db_type == 'sqlite':
        db_path = input("请输入 sqlite 数据库文件路径: ").strip()
        if not os.path.isfile(db_path):
            print(f"错误: sqlite 文件 {db_path} 不存在")
            sys.exit(1)
        DBPool.init_pool(sqlite_path=db_path, maxconn=5)
        db_info['db_path'] = db_path
    elif db_type == 'postgres':
        host = input("host: ").strip()
        port = input("port: ").strip()
        user = input("user: ").strip()
        password = input("password: ").strip()
        dbname = input("dbname: ").strip()
        DBPool.init_pool(
            db_type='postgres',
            host=host,
            port=int(port),
            user=user,
            password=password,
            database=dbname
        )
        # postgres 不提供文件备份路径
        db_info.update({
            'host': host,
            'port': port,
            'user': user,
            'password': password,
            'database': dbname
        })
    else:
        print("错误: 不支持的数据库类型")
        sys.exit(1)

    return db_info


def get_schema_and_samples(limit=5):
    """
    查询当前数据库的表结构，返回类似：
    {
      'table1': [('col1','INTEGER'), ('col2','TEXT'), ...],
      'table2': [...]
    }
    """
    schema = {}
    samples = {}
    # 从连接池获取一个连接
    with DBPool.get_connection() as conn:
        # 1. 先拿到所有表名
        # 对 sqlite 和 PG 用不同的 SQL
        if hasattr(conn, 'execute'):  # sqlite3.Connection
            table_sql = "SELECT name FROM sqlite_master WHERE type='table';"
        else:
            table_sql = (
                "SELECT tablename as name "
                "FROM pg_catalog.pg_tables "
                "WHERE schemaname='public';"
            )

        cur = conn.cursor()
        try:
            cur.execute(table_sql)
            tables = [row[0] for row in cur.fetchall()]
        finally:
            cur.close()

        # 2. 遍历每张表，取列信息
        for tbl in tables:
            cur = conn.cursor()
            try:
                if hasattr(conn, 'execute'):  # sqlite
                    cur.execute(f"PRAGMA table_info('{tbl}');")
                    # PRAGMA 返回 (cid, name, type, notnull, dflt_value, pk)
                    cols = [(row[1], row[2]) for row in cur.fetchall()]
                else:  # psycopg2
                    cur.execute(f"""
                        SELECT column_name, data_type
                        FROM information_schema.columns
                        WHERE table_name = %s;
                    """, (tbl,)
                    )
                    cols = cur.fetchall()
                schema[tbl] = cols
                # 获取示例数据
                cur.execute(f"SELECT * FROM {tbl} LIMIT {limit}")
                rows = cur.fetchall()
                columns = [d[0] for d in cur.description]
                samples[tbl] = {"columns": columns, "rows": rows}
            finally:
                cur.close()

    return schema, samples

def print_schema(schema: dict):
    """
    以可读形式输出数据库表结构
    """
    print("[AI] 当前数据库表结构：")
    for table, cols in schema.items():
        print(f"- 表: {table}")
        for col_name, col_type in cols:
            print(f"    • {col_name}: {col_type}")
    print()

def generate_script(requirement: str, schema: dict,samples: dict,
                    model: str = "deepseek-reasoner",
                    max_retries: int = 2,
                    initial_backoff: float = 1.0) -> str:
    """
    使用 DeepSeek R1 生成 Python 脚本内容，用于修改数据库。
    """
    prompt = (
        "# 数据库 schema:\n"
        f"{schema}\n\n"
        "# 示例数据 (每表前几行):\n"
        f"{samples}\n\n"
        "# 请根据以下需求生成完整的、可直接运行的 Python 脚本，"
        "需在脚本中使用 DBPool 获取连接并执行必要的 SQL。"
        "脚本中包含失败时的错误处理和执行成功的提示。\n\n"
        f"需求: {requirement}\n"
    )
    print(samples)
    backoff = initial_backoff
    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是数据库操作专家，输出可直接运行的 Python 脚本。数据库地址为F:\pycode\output\example\mysqldemo.db"},
                    {"role": "user",   "content": prompt}
                ],
                stream=False,
                timeout=300  # 连接+读取超时，单位秒
            )

            # 直接获取完整响应内容
            if response.choices and response.choices[0].message.content:
                return response.choices[0].message.content
            else:
                raise RuntimeError("API 返回空响应")

        except (APIConnectionError, APIError, ReadTimeout) as e:
            print(f"[尝试 {attempt}/{max_retries}] 调用失败，{backoff}s 后重试… 详情: {e}")
            time.sleep(backoff)
            backoff *= 2

        except Exception as e:
            # 捕获其他不可预期错误
            raise RuntimeError(f"脚本生成过程出现不可恢复错误：{e}") from e

    raise RuntimeError(f"调用 DeepSeek 接口失败，已重试 {max_retries} 次，请检查网络或稍后再试。")
def main():
    # 初始化数据库连接池
    db_info = init_db_pool()
    
    # 初始化
    indexer = UniversalDbVectorIndexer(db_info['db_path'], client.api_key)
    indexer.index_all()
    mgr = NLDatabaseManager(db_info['db_path'], indexer)

    # 处理自然语言指令
    res = mgr.process_nl("新增客户，姓名张三，地址北京")
    print(res)

    # 读取功能需求
    requirement = input("请输入功能需求: ").strip()
    if not requirement:
        print("错误: 功能需求不能为空")
        sys.exit(1)

    # 获取 schema
    print("[AI] 正在获取数据库 schema...")
    schema, samples = get_schema_and_samples()
    print(f"[AI] 已获取 {len(schema)} 张表的结构及示例数据。")

    # 输出表结构
    print_schema(schema)

    # 调用模型生成脚本
    print("[AI] 正在调用大模型生成脚本...")
    script_content = generate_script(requirement, schema, samples)

    segments = re.split(r"```(?:python)?", script_content)
    if len(segments) >= 3:
        # segments[1] 是首个代码块内容，去掉结尾的 ```
        script_to_write = segments[1].split('```')[0].strip() + '\n'
    else:
        print("警告: 未检测到代码块，写入完整响应")
        script_to_write = script_content

    ts = datetime.now().strftime('%Y%m%d%H%M%S')
    filename = f"generated_{ts}.py"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(script_to_write)
    print(f"[AI] 脚本已保存为 {filename}")

    # # —— 自动调用 run_generated.py
    # run_gen = os.path.join(os.path.dirname(__file__), filename)
    # if not os.path.isfile(run_gen):
    #     print(f"错误: 找不到 run_generated.py ({run_gen})，请检查路径")
    #     sys.exit(1)

    # resp = input("是否现在备份并执行该脚本？(y/n): ").strip().lower()
    # if resp == 'y':
    #     try:
    #         subprocess.run(
    #             [sys.executable, run_gen, filename],
    #             check=True
    #         )
    #     except subprocess.CalledProcessError as e:
    #         print(f"运行失败: Return code={e.returncode}")
    #         sys.exit(1)
    # else:
    #     print("已跳过自动执行。")
    # 询问是否备份并执行
    resp = input("是否现在备份并执行该脚本？(y/n): ").strip().lower()
    if resp == 'y':
        # 1. 备份
        if db_info['db_type'] == 'sqlite':
            bak_path = db_info['db_path'] + ".bak"
            shutil.copy(db_info['db_path'], bak_path)
            print(f"[AI] 已备份 SQLite 数据库到 {bak_path}")
        else:
            print("[AI] PostgreSQL 不自动备份，请手动执行 pg_dump。")

        # 2. 执行并捕获输出
        result = subprocess.run(
            [sys.executable, filename],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print(result.stdout)
        if result.returncode != 0:
            print(f"[AI] 脚本执行失败，错误信息：\n{result.stderr}")
            sys.exit(result.returncode)
        else:
            print("[AI] 脚本执行成功！")
    else:
        print("已跳过自动执行。")
               
if __name__ == '__main__':
    main()