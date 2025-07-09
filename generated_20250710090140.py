import json
import pymysql
from dbutils.pooled_db import PooledDB

# 数据库配置 - 根据实际环境修改
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "DSds178200++",
    "database": "mysqldemo",
    "charset": "utf8mb4"
}

# 创建数据库连接池
db_pool = PooledDB(
    creator=pymysql,
    maxconnections=10,
    **DB_CONFIG
)

def describe_database_schema():
    """获取并返回数据库schema的JSON结构"""
    schema = {}
    conn = None
    try:
        # 获取数据库连接
        conn = db_pool.connection()
        cursor = conn.cursor()
        
        # 获取所有表名
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        
        # 获取每个表的列信息
        for table in tables:
            cursor.execute(f"DESCRIBE {table}")
            columns = []
            for row in cursor.fetchall():
                columns.append([row[0], row[1]])  # [字段名, 数据类型]
            schema[table] = columns
        
        return json.dumps(schema, indent=2, ensure_ascii=False)
    
    except Exception as e:
        print(f"数据库操作失败: {str(e)}")
        return None
    
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    schema_json = describe_database_schema()
    if schema_json:
        print("数据库描述成功:")
        print(schema_json)
    else:
        print("未能获取数据库描述")
