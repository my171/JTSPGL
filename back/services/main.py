from sql_generator import init_db_pool, get_sql

# 初始化连接池（以 SQLite 为例）
init_db_pool('sqlite', sqlite_path='F:\\pycode\\JTSPGL\\back\\services\\mysqldemos.db')

# 获取 SQL
sql = get_sql('查询过去一周内月销售额最高的前十个产品')
print(sql)
