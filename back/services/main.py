from sql_generator import init_db_pool, get_sql
from db_pool import FixedDBPool as DBPool
import sys

def main():
    # 1. 初始化连接池（以 SQLite 为例）
    # init_db_pool('sqlite', sqlite_path='F:\\pycode\\JTSPGL\\back\\services\\mysqldemos.db')
    init_db_pool('mysql', host='127.0.0.1',port='3306',
                         user='root', password='DSds178200++', database='mysqldemo')

    # 2. 生成 SQL
    requirement = input("请输入功能需求: ").strip()
    if not requirement:
         print("错误: 功能需求不能为空")
         sys.exit(1)
    sql = get_sql(requirement)
    print("[DEBUG] Generated SQL:\n", sql)

    # 3. 直接执行 SQL 并打印结果
    with DBPool.get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(sql)
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description] if cur.description else []
            print("\t".join(cols))
            for row in rows:
                print("\t".join(str(v) for v in row))
        finally:
            cur.close()

if __name__ == '__main__':
    main()
