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
import numpy as np
import faiss
import pickle
from contextlib import contextmanager
from psycopg2.pool import ThreadedConnectionPool
import mysql.connector
from mysql.connector.pooling import MySQLConnectionPool

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
class FixedDBPool:
    _connection_pool = None
    
    @classmethod
    def init_pool(cls, db_type=None, **kwargs):
        if db_type == 'sqlite':
            cls._connection_pool = SQLiteConnectionPool(kwargs['sqlite_path'], kwargs.get('maxconn', 5))
        elif db_type == 'postgres':
            cls._connection_pool = ThreadedConnectionPool(
                minconn=kwargs.get('minconn', 3),
                maxconn=kwargs.get('maxconn', 20),
                host=kwargs['host'],
                port=kwargs['port'],
                database=kwargs['database'],
                user=kwargs['user'],
                password=kwargs['password']
            )
        elif db_type == 'mysql':
            cls._connection_pool = MySQLConnectionPoolWrapper(
                host=kwargs['host'],
                port=kwargs['port'],
                user=kwargs['user'],
                password=kwargs['password'],
                database=kwargs['database'],
                pool_size=kwargs.get('maxconn', 20)
            )
    
    @classmethod
    @contextmanager
    def get_connection(cls):
        conn = cls._connection_pool.getconn()
        try:
            yield conn
        finally:
            cls._connection_pool.putconn(conn)
    
    @classmethod
    def close_all(cls):
        if cls._connection_pool:
            cls._connection_pool.closeall()

class SQLiteConnectionPool:
    def __init__(self, db_path, maxconn=5):
        self.db_path = db_path
        self.maxconn = maxconn
        self.pool = []
        
    def getconn(self):
        if not self.pool:
            return sqlite3.connect(self.db_path)
        return self.pool.pop()
    
    def putconn(self, conn):
        if len(self.pool) < self.maxconn:
            self.pool.append(conn)
        else:
            conn.close()
    
    def closeall(self):
        for conn in self.pool:
            conn.close()
        self.pool = []

class MySQLConnectionPoolWrapper:
    def __init__(self, host, port, user, password, database, pool_size=10):
        self.pool = MySQLConnectionPool(
            pool_name="mysql_pool",
            pool_size=pool_size,
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            autocommit=False
        )
    
    def getconn(self):
        return self.pool.get_connection()
    
    def putconn(self, conn):
        conn.close()
    
    def closeall(self):
        pass

DBPool = FixedDBPool

class NLDatabaseManager:
    def __init__(self, db_path: str, indexer):
        self.db_path = db_path
        self.indexer = indexer

    def process_nl(self, command: str):
        prompt = (
            "将以下自然语言指令解析为 JSON，对应 action(create/read/update/delete),"
            " table, conditions, data 键，无多余文字输出："
            f"\n指令: {command}\nJSON:")
        try:
            resp = client.chat.completions.create(
                model="deepseek-reasoner",
                messages=[{"role":"user", "content": prompt}]
            )
            content = resp.choices[0].message.content
            
            # 调试输出
            print(f"API 原始响应: {content}")  # 添加调试输出
            
            # 尝试提取 JSON 部分
            if content.startswith("```json"):
                content = content.split("```json")[1].split("```")[0].strip()
            
            parsed = json.loads(content)
        except Exception as e:
            return f"解析指令失败: {str(e)}"

        action = parsed.get("action")
        table = parsed.get("table")
        cond = parsed.get("conditions", "1=1")
        data = parsed.get("data", {})

        try:
            with DBPool.get_connection() as conn:
                cur = conn.cursor()
                if action == "create":
                    cols, vals = zip(*data.items())
                    placeholders = ",".join(["?" for _ in vals])
                    cur.execute(
                        f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders})",
                        tuple(vals)
                    )
                elif action == "read":
                    cur.execute(f"SELECT * FROM {table} WHERE {cond}")
                    return cur.fetchall()
                elif action == "update":
                    sets = ",".join([f"{k}=?" for k in data])
                    cur.execute(
                        f"UPDATE {table} SET {sets} WHERE {cond}",
                        tuple(data.values())
                    )
                elif action == "delete":
                    cur.execute(f"DELETE FROM {table} WHERE {cond}")
                else:
                    raise ValueError(f"未知操作: {action}")
                conn.commit()
        except Exception as e:
            return f"执行SQL失败: {str(e)}"

        try:
            self.indexer.reindex_table(table)
            self.indexer.save()
            return f"操作 {action} 完成，并更新了 {table} 的向量索引。"
        except Exception as e:
            return f"操作 {action} 完成，但更新索引失败: {str(e)}"

class UniversalDbVectorIndexer:
    def __init__(self, db_path, openai_api_key, embedding_model="text-embedding-multilingual",  # 修改这里
                index_path="universal_faiss.index", idmap_path="universal_faiss_ids.pkl"):
        self.db_path = db_path
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
        try:
            resp = client.embeddings.create(
                model=self.embedding_model,
                input=texts
            )
            return np.array([r.embedding for r in resp.data], dtype='float32')
        except Exception as e:
            print(f"Embedding失败: {str(e)}")
            return np.zeros((len(texts), 768))

    def index_all(self):
        try:
            with DBPool.get_connection() as conn:
                if isinstance(conn, sqlite3.Connection):
                    cur = conn.cursor()
                    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
                    tables = [r[0] for r in cur.fetchall()]
                elif 'psycopg2' in str(type(conn)):
                    cur = conn.cursor()
                    cur.execute("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname='public';")
                    tables = [r[0] for r in cur.fetchall()]
                elif 'mysql' in str(type(conn)):
                    cur = conn.cursor()
                    cur.execute("SHOW TABLES;")
                    tables = [r[0] for r in cur.fetchall()]
                else:
                    print("未知数据库类型，无法索引")
                    return

            self.index = None
            self.id_map.clear()
            all_embs, all_ids = [], []
            for tbl in tables:
                embs, ids = self._embed_table(tbl)
                all_embs.append(embs)
                all_ids.extend(ids)
            if all_embs:
                all_embs = np.vstack(all_embs)
                self._init_index(all_embs.shape[1])
                self.index.add_with_ids(all_embs, np.array(all_ids))
                for rid in all_ids:
                    self.id_map[rid] = tbl
        except Exception as e:
            print(f"索引创建失败: {str(e)}")

    def _embed_table(self, table):
        try:
            with DBPool.get_connection() as conn:
                cur = conn.cursor()
                
                if isinstance(conn, sqlite3.Connection):
                    cur.execute(f"PRAGMA table_info('{table}');")
                    cols = [c[1] for c in cur.fetchall()]
                elif 'psycopg2' in str(type(conn)):
                    cur.execute(
                        "SELECT column_name FROM information_schema.columns WHERE table_name = %s;",
                        (table,)
                    )
                    cols = [c[0] for c in cur.fetchall()]
                elif 'mysql' in str(type(conn)):
                    cur.execute(f"DESCRIBE {table};")
                    cols = [c[0] for c in cur.fetchall()]
                
                cur.execute(f"SELECT * FROM {table} LIMIT 100")
                rows = cur.fetchall()
                columns = [d[0] for d in cur.description] if cur.description else []

            texts, ids = [], []
            for r in rows:
                texts.append(" | ".join(str(v) for v in r if v is not None))
                ids.append(abs(hash(f"{table}.{r}")))
            return self._embed(texts), ids
        except Exception as e:
            print(f"表嵌入失败: {str(e)}")
            return np.zeros((0, 768)), []

    def reindex_table(self, table):
        self.index_all()

    def save(self):
        if self.index:
            faiss.write_index(self.index, self.index_path)
            with open(self.idmap_path, 'wb') as f:
                pickle.dump(self.id_map, f)

    def load(self):
        if os.path.exists(self.index_path) and os.path.exists(self.idmap_path):
            self.index = faiss.read_index(self.index_path)
            with open(self.idmap_path, 'rb') as f:
                self.id_map = pickle.load(f)
            self.dimension = self.index.d

    def search(self, query, top_k=5):
        emb = self._embed([query])
        if self.index is None:
            return []
        d, idxs = self.index.search(emb, top_k)
        return [(self.id_map.get(int(i)), float(dist)) for i, dist in zip(idxs[0], d[0])]

def get_schema_and_samples(limit=5):
    schema = {}
    samples = {}
    with DBPool.get_connection() as conn:
        if isinstance(conn, sqlite3.Connection):
            table_sql = "SELECT name FROM sqlite_master WHERE type='table';"
        elif 'psycopg2' in str(type(conn)):
            table_sql = (
                "SELECT tablename as name "
                "FROM pg_catalog.pg_tables "
                "WHERE schemaname='public';"
            )
        elif 'mysql' in str(type(conn)):
            table_sql = "SHOW TABLES;"
        else:
            print("未知数据库类型")
            return {}, {}

        cur = conn.cursor()
        try:
            cur.execute(table_sql)
            tables = [row[0] for row in cur.fetchall()]
        finally:
            cur.close()

        for tbl in tables:
            cur = conn.cursor()
            try:
                if isinstance(conn, sqlite3.Connection):
                    cur.execute(f"PRAGMA table_info('{tbl}');")
                    cols = [(row[1], row[2]) for row in cur.fetchall()]
                elif 'psycopg2' in str(type(conn)):
                    cur.execute(
                        """
                        SELECT column_name, data_type
                        FROM information_schema.columns
                        WHERE table_name = %s;
                        """, (tbl,)
                    )
                    cols = cur.fetchall()
                elif 'mysql' in str(type(conn)):
                    cur.execute(f"DESCRIBE {tbl};")
                    cols = [(row[0], row[1]) for row in cur.fetchall()]
                
                schema[tbl] = cols
                
                cur.execute(f"SELECT * FROM {tbl} LIMIT {limit}")
                rows = cur.fetchall()
                columns = [d[0] for d in cur.description] if cur.description else []
                samples[tbl] = {"columns": columns, "rows": rows}
            except Exception as e:
                print(f"获取表 {tbl} 信息失败: {str(e)}")
            finally:
                cur.close()
    return schema, samples

def generate_script(requirement: str, schema: dict, samples: dict,
                    model: str = "deepseek-reasoner",
                    max_retries: int = 2,
                    initial_backoff: float = 1.0) -> str:
    prompt = (
        "# 数据库 schema:\n"
        f"{json.dumps(schema, indent=2)}\n\n"
        "# 示例数据 (每表前几行):\n"
        f"{json.dumps(samples, indent=2, default=str)}\n\n"
        "# 请根据以下需求生成完整的、可直接运行的 Python 脚本，"
        "需在脚本中使用 DBPool 获取连接并执行必要的 SQL。"
        "重要提示：脚本开头必须导入 DBPool，使用 'from ai_db import DBPool'\n"  # 添加明确的导入说明
        "脚本中包含失败时的错误处理和执行成功的提示。\n\n"
        f"需求: {requirement}\n"
    )
    
    backoff = initial_backoff
    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是数据库操作专家，输出可直接运行的 Python 脚本。"},
                    {"role": "user", "content": prompt}
                ],
                stream=False,
                timeout=300
            )

            if response.choices and response.choices[0].message.content:
                return response.choices[0].message.content
            else:
                raise RuntimeError("API 返回空响应")

        except (APIConnectionError, APIError, ReadTimeout) as e:
            print(f"[尝试 {attempt}/{max_retries}] 调用失败，{backoff}s 后重试… 详情: {str(e)}")
            time.sleep(backoff)
            backoff *= 2

        except Exception as e:
            raise RuntimeError(f"脚本生成过程出现不可恢复错误：{str(e)}") from e

    raise RuntimeError(f"调用 DeepSeek 接口失败，已重试 {max_retries} 次，请检查网络或稍后再试。")

class AIScriptGenerator:
    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com"):
        global client
        client = OpenAI(api_key=api_key, base_url=base_url)
        self.db_info = None
        self.indexer = None
        self.mgr = None
    
    def init_db_pool(self, db_config: dict):
        """初始化数据库连接池
        
        :param db_config: 数据库配置字典，包含以下键值:
            - db_type: 'sqlite'/'postgres'/'mysql'
            - 其他数据库特定参数:
                sqlite: sqlite_path
                postgres/mysql: host, port, user, password, database
        """
        db_type = db_config['db_type']
        self.db_info = db_config
        
        if db_type == 'sqlite':
            if not os.path.isfile(db_config['sqlite_path']):
                raise FileNotFoundError(f"SQLite 文件 {db_config['sqlite_path']} 不存在")
            DBPool.init_pool(db_type='sqlite', sqlite_path=db_config['sqlite_path'], maxconn=5)
        elif db_type == 'postgres':
            DBPool.init_pool(
                db_type='postgres',
                host=db_config['host'],
                port=int(db_config['port']),
                user=db_config['user'],
                password=db_config['password'],
                database=db_config['database']
            )
        elif db_type == 'mysql':
            DBPool.init_pool(
                db_type='mysql',
                host=db_config['host'],
                port=int(db_config.get('port', 3306)),
                user=db_config['user'],
                password=db_config['password'],
                database=db_config['database'],
                maxconn=20
            )
        else:
            raise ValueError("不支持的数据库类型")
        
        # 初始化向量索引（如果支持）
        if db_type in ['sqlite', 'mysql']:
            db_path = db_config.get('sqlite_path', '') if db_type == 'sqlite' else ''
            self.indexer = UniversalDbVectorIndexer(db_path, client.api_key)
            self.indexer.index_all()
            self.mgr = NLDatabaseManager(db_path, self.indexer)
    
    def nl_database_operation(self, command: str):
        """执行自然语言数据库操作（仅支持SQLite和MySQL）
        
        :param command: 自然语言指令
        :return: 操作结果字符串
        """
        if not self.mgr:
            return "自然语言操作仅支持SQLite和MySQL数据库"
        return self.mgr.process_nl(command)
    
    def generate_script(self, requirement: str) -> dict:
        """根据需求生成Python脚本
        
        :param requirement: 功能需求描述
        :return: 包含脚本内容和元数据的字典
        """
        if not self.db_info:
            raise RuntimeError("请先初始化数据库连接池")
        
        print("[AI] 正在获取数据库 schema...")
        schema, samples = get_schema_and_samples()
        print(f"[AI] 已获取 {len(schema)} 张表的结构及示例数据。")
        
        print("[AI] 正在调用大模型生成脚本...")
        script_content = generate_script(requirement, schema, samples)
        
        # 提取代码块
        segments = re.split(r"```(?:python)?", script_content)
        if len(segments) >= 3:
            script_to_write = segments[1].split('```')[0].strip() + '\n'
        else:
            print("警告: 未检测到代码块，写入完整响应")
            script_to_write = script_content
        
        ts = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = f"generated_{ts}.py"
        
        return {
            "filename": filename,
            "content": script_to_write,
            "full_response": script_content,
            "timestamp": ts
        }
    
    def save_script(self, script_data: dict, output_dir: str = "."):
        """保存生成的脚本到文件
        
        :param script_data: generate_script方法返回的数据
        :param output_dir: 输出目录
        :return: 文件路径
        """
        filepath = os.path.join(output_dir, script_data["filename"])
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(script_data["content"])
        return filepath
    
    def execute_script(self, script_path: str) -> dict:
        """执行生成的Python脚本
        
        :param script_path: 脚本文件路径
        :return: 执行结果字典
        """
        if not self.db_info:
            raise RuntimeError("请先初始化数据库连接池")
        
        # 备份数据库（仅SQLite）
        backup_path = None
        if self.db_info['db_type'] == 'sqlite':
            bak_path = self.db_info['sqlite_path'] + ".bak"
            shutil.copy(self.db_info['sqlite_path'], bak_path)
            backup_path = bak_path
            print(f"[AI] 已备份 SQLite 数据库到 {bak_path}")
        elif self.db_info['db_type'] == 'mysql':
            print("[AI] MySQL 不自动备份，请手动执行 mysqldump。")
        else:
            print("[AI] PostgreSQL 不自动备份，请手动执行 pg_dump。")
        
        # 执行脚本
        result = {"backup_path": backup_path}
        try:
            process = subprocess.run(
                [sys.executable, script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30
            )
            result["stdout"] = process.stdout
            result["stderr"] = process.stderr
            result["returncode"] = process.returncode
            
            if process.returncode != 0:
                print(f"[AI] 脚本执行失败，错误信息：\n{process.stderr}")
            else:
                print("[AI] 脚本执行成功！")
        except subprocess.TimeoutExpired as e:
            result["error"] = "脚本执行超时"
            result["details"] = str(e)
            print("[AI] 脚本执行超时，已终止")
        except Exception as e:
            result["error"] = "脚本执行出错"
            result["details"] = str(e)
            print(f"[AI] 脚本执行出错: {str(e)}")
        
        return result
    
    def close(self):
        """清理资源"""
        DBPool.close_all()
        print("数据库连接池已关闭")