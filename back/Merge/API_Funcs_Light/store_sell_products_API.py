'''
    查询仓库对应的商店

    传入
    {
        str:store_id: 商店编号
        str:product: 商品编号
        int:quantity: 贩卖数量
    }
    返回
    {
        int:successType: (
            0:商品编号不存在
            1:商店无相关商品库存记录
            2:商店内商品库存不足
            3:出售成功
            4:出错
        )
        int:num: 当为库存不足的情况时，返回库存量
    }
'''

from flask import jsonify
from database import DBPool
from API_Funcs_Light.API_of_API.InvLog_idGen import id_format, get_id
from datetime import datetime

def API_StoreSellProducts(request):
    data = request.get_json()
    store_id = data.get('store_id', '')
    product_id = data.get('product_id', '')
    quantity = data.get('quantity', '')
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
                
                # 判断商店里是否有商品
                query = """
                    SELECT stock_quantity
                    FROM store_inventory
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

                # 更新商店库存
                update_sql = """
                    UPDATE store_inventory
                    SET stock_quantity = stock_quantity - %s
                    WHERE store_id = %s
                    AND product_id = %s
                """
                cur.execute(update_sql, (quantity, store_id, product_id))
                
                # 查询单价
                query_sql = """
                    SELECT unit_price
                    FROM product
                    WHERE product_id = %s
                """
                cur.execute(query_sql, (product_id,))
                unit_price = cur.fetchone()[0]
                
                # 生成交易编号
                query_sql = """
                    SELECT COUNT(*)
                    FROM sales
                    WHERE sales_id LIKE %s
                """
                cur.execute(query_sql, (id_format('SL') + '%',))
                sales_id = get_id('SL', cur.fetchone()[0] + 1)
                
                # 更新Sales表
                update_sql = """
                    INSERT INTO sales (
                        sales_id,
                        store_id,
                        product_id,
                        sale_date,
                        quantity,
                        unit_price
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """
                cur.execute(update_sql, (sales_id, store_id, product_id, datetime.now().date(), quantity, unit_price))
                conn.commit()
                return jsonify({
                    "successType" : 3
                })
    except Exception as e:
        print(str(e))
        return jsonify({"successType" : 4, "err": str(e)}), 500