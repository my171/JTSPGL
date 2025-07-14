# -*- coding: utf-8 -*-
from psycopg2.pool import ThreadedConnectionPool
from contextlib import contextmanager
from config import Config

class DBPool:
    _connection_pool = None
    
    @classmethod
    def initialize(cls):
        cls._connection_pool = ThreadedConnectionPool(
            minconn=3,  # 最小连接数
            maxconn=20,  # 最大连接数
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            database=Config.DB_NAME,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD
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

# 初始化连接池
DBPool.initialize()