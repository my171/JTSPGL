from sql_generator import init_db_pool, get_sql
from db_pool import FixedDBPool as DBPool
import subprocess
import sys

def main():
    # 1. 初始化连接池（以 SQLite 为例）
    # init_db_pool('sqlite', sqlite_path='F:\\pycode\\JTSPGL\\back\\services\\mysqldemos.db')
    init_db_pool('postgres', host='127.0.0.1',port='5432',
                         user='u2', password='ab12AB!@', database='postgres')

    # 2. 生成 SQL
    requirement = input("请输入功能需求: ").strip()
    if not requirement:
         print("错误: 功能需求不能为空")
         sys.exit(1)
    sql = get_sql(requirement)
    print("[DEBUG] Generated SQL:\n", sql)

    #
    script_path = "back/services/db_backup.py"
    if sys.platform.startswith("win"):
        script_path = script_path.replace("/","\\")  # Windows 使用反斜杠

    # 执行命令
    result = subprocess.run(
        [sys.executable, script_path, "backup"],  # sys.executable 确保使用当前 Python 解释器
        capture_output=True,
        text=True
    )

    # 输出结果
    print("Return code:", result.returncode)
    print("Output:", result.stdout)
    if result.stderr:
        print("Error:", result.stderr)
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
