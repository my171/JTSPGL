import psycopg2
import requests # 导入 requests 库
import time
import sys
import json

# --- 配置区 ---

# 1. PostgreSQL 数据库配置
DB_CONFIG = {
    "host": "localhost",
    "dbname": "your_database_name",
    "user": "your_username",
    "password": "your_password"
}

# 2. API 接口配置
# !!! 重要：请将此 URL 替换为您接收报警信息的前端 API 端点 !!!
API_ENDPOINT = "http://your-api-server.com/api/v1/inventory-alerts"

# 检查间隔时间（秒）
CHECK_INTERVAL_SECONDS = 60


# --- 核心功能函数 ---

def send_alert_to_api(alert_type, details):
    """
    构建 JSON 数据并将警报发送到指定的 API 端点。
    """
    headers = {
        'Content-Type': 'application/json'
    }

    # 根据警报类型构建不同的 payload
    if alert_type == "warehouse":
        warehouse_id, product_id, quantity, warn_quantity = details
        payload = {
            "type": "warehouse_alert",
            "location_id": warehouse_id,
            "product_id": product_id,
            "current_quantity": quantity,
            "threshold": warn_quantity
        }
    elif alert_type == "store":
        store_id, product_id, stock_quantity, safety_stock = details
        payload = {
            "type": "store_alert",
            "location_id": store_id,
            "product_id": product_id,
            "current_quantity": stock_quantity,
            "threshold": safety_stock
        }
    else:
        # 如果类型未知，则不执行任何操作
        return

    try:
        # 发送 HTTP POST 请求，设置超时时间为 10 秒
        response = requests.post(API_ENDPOINT, headers=headers, data=json.dumps(payload), timeout=10)
        
        # 检查 API 的响应状态码
        if response.status_code >= 200 and response.status_code < 300:
            print(f"✅ 成功发送警报到 API: {payload['location_id']} - {payload['product_id']}")
        else:
            # 如果 API 返回错误，打印出来方便排查
            print(f"❌ 发送警报到 API 失败。状态码: {response.status_code}, 响应: {response.text}")

    except requests.exceptions.RequestException as e:
        # 捕获网络连接错误，如超时、DNS错误等
        print(f"❌ API 连接错误: {e}")


def check_inventory_levels():
    """
    连接数据库，检查库存，并为每条低库存记录调用 API 发送警报。
    """
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # 1. 检查仓库库存
        cursor.execute("""
            SELECT warehouse_id, product_id, quantity, warn_quantity
            FROM warehouse_inventory
            WHERE quantity <= warn_quantity AND warn_quantity IS NOT NULL
        """)
        low_stock_warehouses = cursor.fetchall()
        for item in low_stock_warehouses:
            send_alert_to_api("warehouse", item)

        # 2. 检查门店库存
        cursor.execute("""
            SELECT store_id, product_id, stock_quantity, safety_stock
            FROM store_inventory
            WHERE stock_quantity <= safety_stock AND safety_stock IS NOT NULL
        """)
        low_stock_stores = cursor.fetchall()
        for item in low_stock_stores:
            send_alert_to_api("store", item)

    except psycopg2.Error as e:
        print(f"❌ 数据库错误: {e}")
    except Exception as e:
        print(f"❌ 发生未知错误: {e}")
    finally:
        if conn:
            conn.close()

# --- 主程序 ---
if __name__ == "__main__":
    print(f"库存监控脚本已启动。警报将被发送到: {API_ENDPOINT}")
    print(f"每 {CHECK_INTERVAL_SECONDS} 秒检查一次。按 Ctrl+C 停止脚本。")
    
    try:
        while True:
            # print(f"\n--- {time.ctime()}: 开始检查库存 ---") # 如果需要每次都看到检查日志，可以取消这行注释
            check_inventory_levels()
            time.sleep(CHECK_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\n脚本已停止。")
        sys.exit(0)