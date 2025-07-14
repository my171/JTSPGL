'''
    获取仓库物品存量

    传入
    {
        str:warehouseId: 仓库编号 --> WH___
        str:productId: 商品编号 --> P____
    }
    返回
    {
        int:successType: (0:商品编号不存在 1:仓库内无对应商品 2:查询到对应商品)
        str:name: 当存在相应编号商品时，为商品名称，否则无该属性
        int:quantity: 当仓库内存在相应商品时，为商品数量，否则无该属性
    }
'''

from flask import jsonify
from database import DBPool
from datetime import datetime

def API_GetWarehouseProduct(request):
    current_time = datetime.now().date()
    year = current_time.year
    month = current_time.month
    warehouse_id = request.args.get('warehouseId', '')
    product_id = request.args.get('productId', '')
    if len(product_id) < 1:
        return jsonify("error", "缺少查询参数")

    try:
        with DBPool.get_connection() as conn:
            with conn.cursor() as cur:
                
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
                    
                name = result[0]
                query = """
                    SELECT quantity
                    FROM warehouse_inventory
                    WHERE product_id = %s
                    AND warehouse_id = %s
                    AND EXTRACT(YEAR FROM record_date) = %s
                    AND EXTRACT(MONTH FROM record_date) = %s;
                """

                cur.execute(query, (product_id, warehouse_id, year, month))
                result = cur.fetchone()
                if result is None:
                    return jsonify({
                        "successType" : 1,
                        "name" : name
                    })
                quantity = result[0]

                return jsonify({
                    "successType" : 2,
                    "name" : name,
                    "quantity": quantity
                })

    except Exception as e:
        print(str(e))
        return jsonify({"err": str(e)}), 500