'''
    由{from_warehouse_id}分配{quantity}个编号为{product_id}的商品至商店{store_id}
    将修改warehouse_inventory和store_inventory的对应库存数量
    将在replenishment表和inventory_log表中新增日志

    传入
    {
        str:from_warehouse_id: 仓库编号
        str:quantity: 商品数量
        str:product_id: 货物编号
        str:store_id: 商店编号
    }
    返回
    {
        int:successType: (
            0:商品编号不存在
            1:仓库无相关商品库存记录
            2:仓库内商品库存不足
            3:调货成功
            4:出错
        )
        int:num: 当为库存不足的情况时，返回库存量
    }
'''

from flask import jsonify
from database import DBPool
from API_Funcs_Light.API_of_API.InvLog_idGen import id_format, get_id
from API_Funcs_Light.API_of_API.InitialFunctions import Init_Sales_GetSafetyStock
from datetime import datetime

def API_StoreTransferIn(request):
    data = request.get_json()
    store_id = data.get('store_id', '')
    product_id = data.get('product_id', '')
    quantity = data.get('quantity', '')
    warehouse_id = data.get('from_warehouse_id', '')

    try:
        with DBPool.get_connection() as conn:
            with conn.cursor() as cur:
                # 判断对应商品是否存在
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
                
                #判断仓库里是否有商品
                query = """
                    SELECT quantity
                    FROM warehouse_inventory
                    WHERE product_id = %s;
                """
                
                cur.execute(query, (product_id,))
                result = cur.fetchone()
                if result is None:
                    return jsonify({
                        "successType" : 1
                    })
                
                if result[0] <= quantity:
                    return jsonify({
                        "successType" : 2,
                        "num" : result[0]
                    })

                # 将相应仓库的库存减少
                update_sql = """
                    UPDATE warehouse_inventory
                    SET quantity = quantity - %s
                    WHERE warehouse_id = %s
                    AND product_id = %s
                """
                cur.execute(update_sql, (quantity, warehouse_id, product_id))



                
                query = """
                    SELECT stock_quantity
                    FROM store_inventory
                    WHERE product_id = %s;
                """
                cur.execute(query, (product_id,))
                result = cur.fetchone()
                if result is None:
                    # 当商店中不存在相关商品的库存记录时，插入相应记录
                    update_sql = """
                        INSERT INTO store_inventory (
                            store_id,
                            product_id,
                            last_updated,
                            stock_quantity,
                            safety_stock,
                        )
                        VALUES (%s, %s, %s, %s, %s)
                    """
                    cur.execute(update_sql, (store_id, product_id, datetime.now().date(), quantity, Init_Sales_GetSafetyStock(product_id)))
                else:
                    # 当商店中存在相关商品的库存记录时，将相应商店的库存增加
                    update_sql = """
                        UPDATE store_inventory
                        SET stock_quantity = stock_quantity + %s
                        WHERE store_id = %s
                        AND product_id = %s
                    """
                    cur.execute(update_sql, (quantity, store_id, product_id))

                # 更新补货表replenishment
                query = """
                    SELECT COUNT(*) AS count
                    FROM replenishment
                    WHERE replenishment_id LIKE %s
                """
                cur.execute(query, (id_format('RP') + '%', ))
                cnt = cur.fetchone()[0] + 1
                RP_id = get_id('RP', cnt)
                
                insert_sql = """
                    INSERT INTO replenishment (
                        replenishment_id,
                        warehouse_id,
                        store_id,
                        product_id,
                        shipment_date,
                        shipped_quantity,
                        received_quantity
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cur.execute(insert_sql, (RP_id, warehouse_id, store_id, product_id, datetime.now().date(), quantity, quantity))
                
                # 更新库存日志
                query = """
                    SELECT COUNT(*) AS count
                    FROM inventory_log
                    WHERE log_id LIKE %s
                """
                cur.execute(query, (id_format('LOG') + '%', ))
                cnt = cur.fetchone()[0] + 1
                log_id = get_id('LOG', cnt)
                
                insert_sql = """
                    INSERT INTO inventory_log (
                        log_id,
                        product_id,
                        location_id,
                        change_type,
                        change_quantity,
                        reference_no
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                cur.execute(insert_sql, (log_id, product_id, warehouse_id, 'OUT', quantity, RP_id))
                conn.commit()
                
                return jsonify({
                    "successType" : 3
                })
    except Exception as e:
        return jsonify({"successType" : 4, "err": str(e)}), 500