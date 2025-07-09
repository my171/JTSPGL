import os
import pymysql
from pymysql import Error
from pymysql.connections import Connection
from contextlib import contextmanager
from typing import Optional, Iterator

# 数据库连接配置 (从环境变量获取)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "inventory_db")

class DBPool:
    """简易数据库连接池"""
    def __init__(self, size: int = 5):
        self.size = size
        self._pool = []
        self._initialize_pool()

    def _initialize_pool(self):
        for _ in range(self.size):
            conn = pymysql.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            self._pool.append(conn)

    @contextmanager
    def get_connection(self) -> Iterator[Connection]:
        """从连接池获取连接"""
        if not self._pool:
            raise RuntimeError("No available connections in pool")
        
        conn = self._pool.pop()
        try:
            yield conn
        finally:
            self._pool.append(conn)

    def close_all(self):
        """关闭所有连接"""
        for conn in self._pool:
            if conn.open:
                conn.close()
        self._pool.clear()

def describe_database():
    """获取并打印数据库版本信息"""
    pool = DBPool()
    try:
        with pool.get_connection() as conn, conn.cursor() as cursor:
            # 执行数据库版本查询
            cursor.execute("SELECT VERSION() AS db_version")
            result = cursor.fetchone()
            
            if result:
                version = result["db_version"]
                print(f"数据库连接成功！版本信息: {version}")
            else:
                print("未获取到数据库版本信息")
                
    except Error as e:
        print(f"数据库操作失败: {e}")
    finally:
        pool.close_all()

if __name__ == "__main__":
    describe_database()
    print("脚本执行完毕")
