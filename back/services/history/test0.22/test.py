import mysql.connector
from openai import OpenAI

# —— 1. 配置 OpenAI 和 MySQL —— #
client = OpenAI(api_key="sk-3f5e62ce34084f25ba2772f0f2958f75", base_url="https://api.deepseek.com")

db_config = {
    "host":     "127.0.0.1",
    "port":     3306,
    "user":     "root",
    "password": "DSds178200++",
    "database": "mysqldemo",  # 确保这个数据库存在
}

sql_file_path = "update_products.sql"

# —— 2. 调用 OpenAI 生成 SQL —— #
def generate_sql_via_ai():
    # 修正提示词，明确指定数据库名称
    prompt = """
请为 MySQL 数据库 mysqldemo生成一份 SQL 文件，满足以下需求：
1. 将表中的内容完整输出
请输出完整可执行的 SQL 语句，不要包含任何非SQL内容（如代码块标记），只需纯SQL语句和注释。
"""
    try:
        resp = client.chat.completions.create(
            model="deepseek-reasoner",
            messages=[{"role": "system", "content": "你是一个专业的MySQL DBA，只输出纯SQL代码。"},
                      {"role": "user",   "content": prompt}],
            temperature=0.0,
        )
        sql_text = resp.choices[0].message.content.strip()
        
        # 清理Markdown代码块标记
        if sql_text.startswith("```sql"):
            sql_text = sql_text[6:]  # 移除开头的```sql
        if sql_text.endswith("```"):
            sql_text = sql_text[:-3]  # 移除结尾的```
        
        return sql_text
    except Exception as e:
        print(f"API调用失败: {e}")
        # 返回示例SQL作为备选方案
        return """
-- 示例SQL（API调用失败时使用）
USE mysqldemo;

-- 1. 添加stock字段
ALTER TABLE products ADD COLUMN stock INT DEFAULT 0;

-- 2. 初始化所有库存为100
UPDATE products SET stock = 100;

-- 3. 高价商品库存清零
UPDATE products SET stock = 0 WHERE price > 1000;
"""

# —— 3. 写入到 .sql 文件 —— #
def write_sql_file(sql_text: str):
    with open(sql_file_path, "w", encoding="utf-8") as f:
        f.write(sql_text)
    print(f"已写入 SQL 文件：{sql_file_path}")

# —— 4. 读取并执行 SQL —— #
def execute_sql_file():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        # 验证表是否存在
        # cursor.execute("SHOW TABLES LIKE 'products'")
        # if not cursor.fetchone():
        #     print("错误：数据库中没有 'products' 表")
        #     return
        
        # 读取SQL文件并清理
        with open(sql_file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
            # 移除所有Markdown代码块标记
            content = content.replace("```sql", "").replace("```", "")
            
            # 分割SQL语句
            statements = [stmt.strip() for stmt in content.split(";") 
                         if stmt.strip() and not stmt.strip().startswith("--")]
        
        # 执行每条SQL语句
        for stmt in statements:
            
            if not stmt:  # 跳过空语句
                continue
                
            print(f"执行 SQL：{stmt[:60]}{'...' if len(stmt) > 60 else ''}")
            try:
                cursor.execute(stmt)
                conn.commit()
            except mysql.connector.Error as err:
                print(f"执行出错: {err}")
                conn.rollback()
        
        print("SQL 执行完毕。")
    except Exception as e:
        print(f"数据库连接失败: {e}")
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

if __name__ == "__main__":
    # 生成 SQL
    sql = generate_sql_via_ai()
    print("生成的SQL内容:")
    print(sql)
    print("-" * 50)
    
    # 写文件
    write_sql_file(sql)
    
    # 执行到 MySQL
    execute_sql_file()