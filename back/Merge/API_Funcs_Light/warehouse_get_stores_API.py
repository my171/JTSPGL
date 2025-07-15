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

def API_GetStoreByWarehouse(request):
    try:
        warehouse_id = request.args.get('warehouseId', '')
        with DBPool.get_connection() as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT store_id, store_name
                    FROM store
                    WHERE store.warehouse_id = %s
                """
                cur.execute(query, (warehouse_id,))
                return jsonify([(
                    row[0],
                    row[1]
                ) for row in cur.fetchall()])
    except Exception as e:
        return jsonify({"err": str(e)}), 500