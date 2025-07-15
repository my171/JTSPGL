import sql_generator
from database import DBPool
import sys
def text_to_sqlite(requirement: str, max_retries: int = 2):
    """
    将文本需求转换为 SQL，并在 SQLite 中执行；若执行报错，则将错误信息与原 SQL 反馈给 AI，生成修复后的 SQL，直至成功或达到重试上限。
    """
    sql = None
    for attempt in range(1, max_retries + 1):
        # 第一次生成或错误后重试生成 SQL
        if sql is None:
            sql = sql_generator.get_sql(requirement)
        else:
            # 反馈错误与原 SQL，提示 AI 修复
            fix_prompt = (
                f"需求: {requirement}\n"
                f"请修复下列错误: {last_error}\n"
                f"原 SQL:\n{sql}\n"
            )
            sql = sql_generator.get_sql(fix_prompt)

        print(f"[DEBUG] Attempt {attempt} - Generated SQL:\n{sql}\n")

        # 执行生成的 SQL
        with DBPool.get_connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute(sql)
                if cur.description is None:
                    conn.commit()
                    return '运行完毕'
                else:
                    rows = cur.fetchall()
                    cols = [d[0] for d in cur.description] if cur.description else []

                    # 格式化输出
                    header = "\t".join(cols)
                    print(header)
                    result_str = header
                    for row in rows:
                        line = "\t".join(str(v) for v in row)
                        print(line)
                        result_str += "\n" + line
                    return result_str

                # return result_str
                # # # 尝试获取结果集
                # # rows = cur.fetchall()
                # cols = [d[0] for d in cur.description] if cur.description else []

                # # 格式化输出
                # header = "\t".join(cols)
                # print(header)
                # result_str = header
                # for row in rows:
                #     line = "\t".join(str(v) for v in row)
                #     print(line)
                #     result_str += "\n" + line

                # return result_str

            except Exception as e:
                # 捕获错误，记录并进行下一次重试
                last_error = str(e)
                print(f"[ERROR] SQL 执行失败: {last_error}\n")
                if attempt == max_retries:
                    # 最后一次失败后返回错误与 SQL
                    return f"执行失败: {last_error}\n原 SQL:\n{sql}"
            finally:
                cur.close()


#text_to_sqlite("描述数据库")