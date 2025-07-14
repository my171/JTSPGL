'''
    查询仓库对应的商店

    传入
    {
        str:warehouseId: 仓库编号
    }
    返回
    {
        bool:success: 是否登录成功
        array(str, str): 商店编号, 商店名称
    }
'''

from flask import jsonify
from database import DBPool
from datetime import datetime

def id_format(prefix) -> str:
    current_date = datetime.now().date()
    year = current_date.year
    month = current_date.month
    day = current_date.day
    log_format = f"{prefix}{year % 100:02d}{month:02d}{day:02d}"
    return log_format

def get_id(prefix, cnt) -> str:
    current_date = datetime.now().date()
    year = current_date.year
    month = current_date.month
    day = current_date.day
    id = f"{prefix}{year % 100:02d}{month:02d}{day:02d}{cnt}"
    return id

def API_GetStoreByWarehouse(request):
    data = request.get_json()
    product_id = data.get('product', '')
    quantity = data.get('quantity', '')
    warehouse_id = data.get('warehouse_id', '')

    try:
        # Update the database
        with DBPool.get_connection() as conn:
            with conn.cursor() as cur:
                # Get the order
                query = """
                    SELECT COUNT(*) AS count
                    FROM inventory_log
                    WHERE log_id LIKE %s
                """
                cur.execute(query, (id_format('LOG') + '%', ))
                cnt = cur.fetchone()[0] + 1
                log_id = get_id('LOG', cnt)
                # Update the inventory_log table
                insert_sql = """
                    INSERT INTO inventory_log (
                        log_id,
                        product_id,
                        location_id,
                        change_type,
                        change_quantity
                    )
                    VALUES (%s, %s, %s, %s, %s)
                """
                cur.execute(insert_sql, (log_id, product_id, warehouse_id, 'IN', quantity))
                # Update the warehouse_inventory table
                update_sql = """
                    UPDATE warehouse_inventory
                    SET quantity = quantity + %s
                    WHERE warehouse_id = %s
                    AND product_id = %s
                """
                cur.execute(update_sql, (quantity, warehouse_id, product_id))
                conn.commit()
    except Exception as e:
        return jsonify({"err": str(e)}), 500