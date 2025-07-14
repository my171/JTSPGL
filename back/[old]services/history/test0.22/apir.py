# example_usage.py
# 示例脚本：演示如何使用 AIScriptGenerator 和 NLDatabaseManager

import os
import sys
from pathlib import Path

# 请将下面的 import 修改为实际代码文件所在路径或包名
# 假设上面提供的所有类都保存在 ai_db.py 同一目录下
sys.path.append(os.path.dirname(__file__))
from ai_db import AIScriptGenerator


def main():
    # 从环境变量或在这里直接填写你的 DeepSeek/OpenAI API Key
    api_key="sk-3f5e62ce34084f25ba2772f0f2958f75"

    # 数据库配置示例：可切换为 sqlite, mysql, 或 postgres
    db_config = {
        "db_type": "sqlite",               # 可选：'sqlite' / 'mysql' / 'postgres'
        "sqlite_path": "F:\\pycode\\JTSPGL\\back\\services\\test\\mysqldemos.db",       # sqlite 文件路径
        # 以下字段仅在 mysql/postgres 时需要：
        # "host": "localhost",
        # "port": 3306,
        # "user": "your_user",
        # "password": "your_password",
        # "database": "your_database"
    }

    # 初始化生成器和数据库连接池
    generator = AIScriptGenerator(api_key=api_key)
    try:
        generator.init_db_pool(db_config)
    except Exception as e:
        print(f"无法初始化数据库连接池：{e}")
        sys.exit(1)

    # 示例 1：自然语言数据库操作
    nl_command = "在你认为合适的表中插入一条新记录：name 为 '张三', age 为 30"
    print("执行自然语言操作：", nl_command)
    try:
        result = generator.nl_database_operation(nl_command)
        print("操作结果：", result)
    except Exception as e:
        print(f"自然语言操作出错：{e}")

    # # 示例 2：根据需求生成脚本
    # requirement = "查询所有年龄大于25的用户，并打印结果"
    # print("生成脚本需求：", requirement)
    # try:
    #     script_data = generator.generate_script(requirement)
    #     script_file = Path(script_data["filename"] )
    #     script_file.write_text(script_data["content"], encoding="utf-8")
    #     print(f"已生成脚本并保存到：{script_file}")
    # except Exception as e:
    #     print(f"脚本生成失败：{e}")

    # # 示例 3：执行生成的脚本
    # if script_file.exists():
    #     print(f"执行脚本：{script_file}")
    #     exec_result = generator.execute_script(str(script_file))
    #     print("脚本执行结果：", exec_result)

    # 关闭连接池
    generator.close()


if __name__ == "__main__":
    main()
