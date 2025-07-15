'''
    仓库补货
    向inventory_log表中添加记录，并更新warehouse_inventory表项
    ===(为什么用的是/api/replenish？？？？)===

    传入
    {
        str:product: 商品编号
        str:quantity: 补货数量
        str:warehouse_id: 仓库编号
    }
    返回
    {
        int:successType: (0:商品编号不存在 1:补货成功 2:出错)
    }
'''

from flask import jsonify
from database import DBPool
from API_Funcs_Light.API_of_API.InvLog_idGen import id_format, get_id

def API_WarehouseReplenish(request):
    data = request.get_json()
    product_id = data.get('product', '')
    quantity = data.get('quantity', '')
    warehouse_id = data.get('warehouse_id', '')

    try:
        with DBPool.get_connection() as conn:
            with conn.cursor() as cur:
                
                # 商品编号是否存在
                query = """
                    SELECT product_name
                    FROM product
                    WHERE product_id = %s;
                """
                cur.execute(query, (product_id,))
                result = cur.fetchone()
                if result is None:
                    return jsonify({
                        "successType" : 0
                    })
                
                # 获取当日的下一个编号
                query = """
                    SELECT COUNT(*) AS count
                    FROM inventory_log
                    WHERE log_id LIKE %s
                """
                cur.execute(query, (id_format('LOG') + '%', ))
                cnt = cur.fetchone()[0] + 1
                log_id = get_id('LOG', cnt)

                # 更新库存日志表
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

                # 更新仓库日志表
                update_sql = """
                    UPDATE warehouse_inventory
                    SET quantity = quantity + %s
                    WHERE warehouse_id = %s
                    AND product_id = %s
                """
                cur.execute(update_sql, (quantity, warehouse_id, product_id))
                conn.commit()
                return jsonify({
                    "successType" : 1
                })
    except Exception as e:
        return jsonify({
            "successType" : 2,
            "err": str(e)
        }), 500