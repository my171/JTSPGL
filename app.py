# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, jsonify, redirect, url_for
from models import Warehouse, Store, Product, Inventory, Sales, Supply
from config import Config
from datetime import datetime, timedelta
from database import DBPool

import sys
import locale

# 设置默认编码为UTF-8
if sys.version_info[0] < 3:
    reload(sys)
    sys.setdefaultencoding('utf8')
else:
    sys.stdout.reconfigure(encoding='utf-8')

# 设置locale
locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

app = Flask(__name__)
app.config.from_object(Config)

@app.route('/')
def dashboard():
    warehouses = Warehouse.get_all()
    stores = Store.get_all()
    low_inventory = Inventory.get_low_inventory()
    return render_template('dashboard.html',
                         warehouses=warehouses,
                         stores=stores,
                         low_inventory=low_inventory)

@app.route('/api/inventory', methods=['GET', 'POST'])
def inventory_api():
    if request.method == 'GET':
        threshold = request.args.get('threshold', default=10, type=int)
        items = Inventory.get_low_inventory(threshold)
        return jsonify(items)
    
    elif request.method == 'POST':
        data = request.get_json()
        try:
            success = Inventory.transfer(
                data['from_warehouse'],
                data['to_warehouse'],
                data['product_id'],
                data['amount']
            )
            return jsonify({"success": success, "message": "库存调拨成功"})
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 400

@app.route('/api/sales/<product_id>')
def sales_api(product_id):
    try:
        months = request.args.get('months', default=12, type=int)
        trend_data = Sales.get_sales_trend(product_id, months)
        return jsonify(trend_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 404

@app.route('/api/sales/store/<store_id>')
def store_sales_api(store_id):
    try:
        months = request.args.get('months', default=12, type=int)
        sales_data = Sales.get_store_sales(store_id, months)
        return jsonify(sales_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 404

@app.route('/api/supply/<warehouse_id>')
def supply_api(warehouse_id):
    try:
        months = request.args.get('months', default=6, type=int)
        supply_data = Supply.get_supply_records(warehouse_id, months)
        return jsonify(supply_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 404

# 商品管理API
@app.route('/api/products', methods=['POST'])
def add_product():
    data = request.get_json()
    try:
        product_id = Product.create(
            product_name=data['product_name'],
            unit_price=float(data['unit_price'])
        )
        return jsonify({"success": True, "product_id": product_id})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route('/api/products/<product_id>', methods=['PUT', 'DELETE'])
def manage_product(product_id):
    if request.method == 'PUT':
        data = request.get_json()
        try:
            success = Product.update(
                product_id=product_id,
                product_name=data.get('product_name'),
                unit_price=data.get('unit_price')
            )
            return jsonify({"success": success, "message": "商品更新成功" if success else "无更新"})
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 400
    
    elif request.method == 'DELETE':
        try:
            success = Product.delete(product_id)
            return jsonify({"success": success, "message": "商品删除成功" if success else "商品不存在"})
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 400


@app.route('/api/warehouses')
def get_warehouses():
    warehouses = Warehouse.get_all()
    return jsonify([{
        'warehouse_id': w.warehouse_id,
        'warehouse_name': w.warehouse_name,
        'address': w.address
    } for w in warehouses])

@app.route('/api/stores')
def get_stores():
    stores = Store.get_all()
    return jsonify([{
        'store_id': s.store_id,
        'store_name': s.store_name,
        'address': s.address
    } for s in stores])

# 仓库商品管理API
@app.route('/api/warehouses/<warehouse_id>/products', methods=['POST', 'DELETE'])
def manage_warehouse_product(warehouse_id):
    data = request.get_json()
    product_id = data['product_id']
    
    if request.method == 'POST':
        try:
            success = Product.add_to_warehouse(
                product_id=product_id,
                warehouse_id=warehouse_id,
                quantity=int(data.get('quantity', 0)))
            return jsonify({"success": success, "message": "商品已添加到仓库"})
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 400
    
    elif request.method == 'DELETE':
        try:
            success = Product.remove_from_warehouse(
                product_id=product_id,
                warehouse_id=warehouse_id,
                quantity=data.get('quantity'))
            return jsonify({"success": success, "message": "商品已从仓库移除"})
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 400

# 商店商品管理API
@app.route('/api/stores/<store_id>/products', methods=['POST', 'DELETE'])
def manage_store_product(store_id):
    data = request.get_json()
    product_id = data['product_id']
    
    if request.method == 'POST':
        try:
            success = Product.add_to_store(
                product_id=product_id,
                store_id=store_id)
            return jsonify({"success": success, "message": "商品已添加到商店"})
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 400
    
    elif request.method == 'DELETE':
        try:
            success = Product.remove_from_store(
                product_id=product_id,
                store_id=store_id)
            return jsonify({"success": success, "message": "商品已从商店移除"})
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 400

@app.route('/api/inventory')
def inventory_query():
    product_id = request.args.get('product_id')
    warehouse_id = request.args.get('warehouse_id')
    
    if not product_id and not warehouse_id:
        return jsonify({"error": "需要提供product_id或warehouse_id参数"}), 400
    
    with DBPool.get_connection() as conn:
        with conn.cursor() as cur:
            query = """
                SELECT i.warehouse_id, w.warehouse_name, 
                       i.product_id, p.product_name, 
                       i.date, i.quantity
                FROM inventory i
                JOIN warehouse w ON i.warehouse_id = w.warehouse_id
                JOIN product p ON i.product_id = p.product_id
                WHERE 1=1
            """
            params = []
            
            if product_id:
                query += " AND i.product_id = %s"
                params.append(product_id)
            
            if warehouse_id:
                query += " AND i.warehouse_id = %s"
                params.append(warehouse_id)
            
            query += " ORDER BY i.date DESC"
            
            cur.execute(query, params)
            columns = [desc[0] for desc in cur.description]
            return jsonify([dict(zip(columns, row)) for row in cur.fetchall()])

@app.route('/products')
def product_search():
    keyword = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    products, total = Product.search(keyword, page, per_page)
    return render_template('products.html',
                         products=products,
                         keyword=keyword,
                         pagination={
                             'page': page,
                             'per_page': per_page,
                             'total': total,
                             'pages': (total + per_page - 1) // per_page
                         })

if __name__ == '__main__':
    app.run(debug=True)