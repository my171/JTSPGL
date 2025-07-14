'''
    获取仓库物品存量

    传入
    {
        str:storeId: 商店编号 --> ST___
        str:productId: 商品编号 --> P____
    }
    返回
    {
        int:successType: (0:商品编号不存在 1:此商品在该商店无销售记录 2:查询到对应销售记录)
        str:name: 当存在相应编号商品时，为商品名称，否则无该属性
        int:quantity: 当商店存在相应销售记录时，为销售数量，否则无该属性
        float:unit_price: 当商店存在相应销售记录时，为产品销售单价，否则无该属性
    }
'''
from flask import jsonify
from database import DBPool

def API_GetStoreProduct(request):
    store_id = request.args.get('storeId', '')
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
                    SELECT 
                    SUM(quantity) AS total_quantity,
                    unit_price
                    FROM sales
                    WHERE product_id = %s
                    AND store_id = %s
                    GROUP BY unit_price
                """

                cur.execute(query, (product_id, store_id))
                result = cur.fetchone()
                if result is None:
                    return jsonify({
                        "successType" : 1,
                        "name" : name
                    })
                
                quantity = result[0]
                unit_price = result[1]
                return jsonify({
                    "successType" : 2,
                    "name" : name,
                    "quantity": quantity,
                    "unit_price": unit_price
                })
    except Exception as e:
        return jsonify({"err": str(e)}), 500