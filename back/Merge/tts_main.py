import sql_generator
from db_pool import FixedDBPool as DBPool
import sys

def text_to_sqlite(text: str):
    sql = sql_generator.get_sql(text)
    print("[DEBUG] Generated SQL:\n", sql)
    
    return sql
    # 3. 直接执行 SQL 并打印结果
    with DBPool.get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(sql)
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description] if cur.description else []

            strings = "\t".join(cols)
            print("\t".join(cols))
            print(strings)
            for row in rows:
                strings += "\t".join(str(v) for v in row)
                print("\t".join(str(v) for v in row))
                print(strings)
    
        except Exception as e:
            return str(e)
        
        finally:
            cur.close()
    return sql