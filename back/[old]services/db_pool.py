import sqlite3
from mysql.connector.pooling import MySQLConnectionPool
from psycopg2.pool import ThreadedConnectionPool
from contextlib import contextmanager


class SQLiteConnectionPool:
    """
    简易 SQLite 连接池
    """
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
        self.pool.clear()


class MySQLConnectionPoolWrapper:
    """
    MySQL 连接池包装类，基于 mysql-connector-python 自带 Pool
    """
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
        # 归还连接
        conn.close()

    def closeall(self):
        # mysql connector 自动管理连接，通常不需手动关闭
        pass


class FixedDBPool:
    """
    统一数据库连接池管理
    """
    _connection_pool = None

    @classmethod
    def init_pool(cls, db_type=None, **kwargs):
        if db_type == 'sqlite':
            cls._connection_pool = SQLiteConnectionPool(
                kwargs['sqlite_path'], kwargs.get('maxconn', 5)
            )
        elif db_type == 'postgres':
            cls._connection_pool = ThreadedConnectionPool(
                minconn=kwargs.get('minconn', 3),
                maxconn=kwargs.get('maxconn', 20),
                host=kwargs['host'],
                port=kwargs['port'],
                database=kwargs['database'],
                user=kwargs['user'],
                password=kwargs['password'],
            )
        elif db_type == 'mysql':
            cls._connection_pool = MySQLConnectionPoolWrapper(
                host=kwargs['host'],
                port=kwargs['port'],
                user=kwargs['user'],
                password=kwargs['password'],
                database=kwargs['database'],
                pool_size=kwargs.get('maxconn', 10)
            )
        else:
            raise ValueError(f"不支持的数据库类型: {db_type}")

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
        if hasattr(cls._connection_pool, 'closeall'):
            cls._connection_pool.closeall()