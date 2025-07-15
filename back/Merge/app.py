# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify
from config import Config
from datetime import datetime
from database import DBPool
from predict import predict_future_sales
from flask_cors import CORS
from tts_main import text_to_sqlite
#from _1_Entry import API_RAG_TextGen

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
CORS(app)  # 允许跨域请求
app.config.from_object(Config)

def is_positive_integer(num):
    return (type(num) == int and num > 0)

@app.route('/api/verify', methods = ['POST'])
def UserVerify():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    # If not connected to database, use the following account
    if (username == 'admin' and password == '123456'):
        return jsonify({
                "success" : True,
                "role" : 'ADMIN',
        })

    try:
        with DBPool.get_connection() as conn:
            with conn.cursor() as cur:
                # Query the user_type and detail_info
                query = f"""
                    SELECT user_type, detail_info
                    FROM users
                    WHERE user_id = %s
                    AND pass_word = %s
                """
                cur.execute(query, (username, password, ))
                result = cur.fetchone()
                if result is None:
                    return jsonify({
                        "success" : False
                    })
                role = result[0]
                detail = result[1]

                return jsonify({
                    "success" : True,
                    "role" : role,
                    "detail" : detail,
                })

    except Exception as e:
        print(str(e))
        return jsonify({"err": str(e)}), 500

# Chatting Box Routing
@app.route('/chatting', methods = ['POST'])
def chatting():
    try:
        input_text = request.get_json().get('text', '')
        
        if not input_text:
            return jsonify({'error': '输入文本为空'}), 400
        
        #result = API_RAG_TextGen(input_text)
        return jsonify({'result': result})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Predict the future sales
@app.route('/api/predict', methods = ['POST'])
def predict():
    # Fetch the data
    data = request.get_json()
    store_id = data.get('warehouse_id', '')
    product_id = data.get('product_id', '')

    # Get the time
    current_time = datetime.now()

    # Get the query_params
    previous_months = []
    for i in range(1, 5):
        month = current_time.month - i
        year = current_time.year
        if month < 1:
            month += 12
            year -= 1
        previous_months.append((year, month))
    query_params = []
    for year_month_pair in previous_months:
        query_params.append((product_id, store_id, year_month_pair[0], year_month_pair[1]))

    try:
        with DBPool.get_connection() as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT 
                    SUM(quantity) AS total_quantity,
                    FROM sales
                    WHERE product_id = %s
                    AND store_id = %s
                    AND EXTRACT(YEAR FROM sale_date) = %s
                    AND EXTRACT(MONTH FROM sale_date) = %s
                """
                cur.execute(query, query_params)


# Fetch the list of stores by warehouse
@app.route('/api/warehouses/<warehouse_id>/stores', methods = ['GET'])
def get_stores_by_warehouse_id(warehouse_id):
    try:
        with DBPool.get_connection() as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT store_id, store_name
                    FROM store
                    WHERE store.warehouse_id = %s
                """
                cur.execute(query, (warehouse_id, ))
                return jsonify([row for row in cur.fetchall()])
    except Exception as e:
        return jsonify({"err": str(e)}), 500

# Query the inventory and the name of a certain product
@app.route('/api/warehouses/<warehouse_id>/products', methods = ['GET'])
def get_product_inventory(warehouse_id):
    product_id = request.args.get('query', '')
    # Check if the parameter exists
    if len(product_id) < 1:
        return jsonify({
            "successType": 3
        })

    try:
        with DBPool.get_connection() as conn:
            with conn.cursor() as cur:
                # Query the product name
                query = """
                    SELECT product_name
                    FROM product
                    WHERE product_id = %s;
                """
                cur.execute(query, (product_id, ))
                result = cur.fetchone()
                # Check if the product exists
                if result is None:
                    return jsonify({
                        "successType" : 0
                    })
                name = result[0]
                # Query the warehouse inventory
                query = """
                    SELECT quantity
                    FROM warehouse_inventory
                    WHERE product_id = %s
                    AND warehouse_id = %s
                """
                cur.execute(query, (product_id, warehouse_id, ))
                quantity = cur.fetchone()[0]
                # Check if there is inventory
                if quantity == 0:
                    return jsonify({
                        "successType" : 1,
                        "name" : name
                    })
                # Normal return
                return jsonify({
                    "successType" : 2,
                    "name" : name,
                    "quantity": quantity
                })

    except Exception as e:
        return jsonify({"err": str(e)}), 500

# Functions regarding id
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
    id = f"{prefix}{year % 100:02d}{month:02d}{day:02d}{cnt:03d}"
    return id

# Replenish Stocks
@app.route('/api/replenish', methods = ['POST'])
def replenish():
    # Fetch the data
    data = request.get_json()
    product_id = data.get('product', '')
    quantity = data.get('quantity', '')
    # Check if the quantity is correct
    if not (is_positive_integer(quantity)):
        return jsonify({
            "successType": 3
        })
    warehouse_id = data.get('warehouse_id', '')

    try:
        # Update the database
        with DBPool.get_connection() as conn:
            with conn.cursor() as cur:
                # Check if the product exists
                check = """
                    SELECT EXISTS(
                        SELECT 1 
                        FROM product 
                        WHERE product_id = %s
                    ) AS is_product_exists
                """
                cur.execute(check, (product_id, ))
                if not cur.fetchone()[0]:
                    return jsonify({
                        "successType": 0
                    })
                # Get the log_id
                query = """
                    SELECT COUNT(*) AS count
                    FROM inventory_log
                    WHERE log_id LIKE %s
                """
                cur.execute(query, (id_format('LOG') + '%', ))
                log_id = get_id('LOG', cur.fetchone()[0] + 1)
                # Insert into the inventory_log table
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
                cur.execute(insert_sql, (log_id, product_id, warehouse_id, 'IN', quantity, ))
                # Update the warehouse_inventory table
                update_sql = """
                    UPDATE warehouse_inventory
                    SET 
                        quantity = quantity + %s,
                        record_date = CURRENT_DATE
                    WHERE warehouse_id = %s
                    AND product_id = %s
                """
                cur.execute(update_sql, (quantity, warehouse_id, product_id, ))
                conn.commit()
                return (jsonify({
                    "successType": 1
                }))
    except Exception as e:
        return jsonify({
            "successType": 2,
            "err": str(e)
        }), 500

# Get Name of a Certain Store
@app.route('/api/store/name', methods = ['GET'])
def get_store_name_by_id():
    store_id = request.args.get('store_id', '')
    
    try:
        with DBPool.get_connection() as conn:
            with conn.cursor() as cur:
                # Check if the product exists
                check = """
                    SELECT store_name 
                    FROM store 
                    WHERE store_id = %s
                """
                cur.execute(check, (store_id, ))
                result = cur.fetchone()
                name = result[0]
                return jsonify({
                    "name": name, 
                })
    except Exception as e:
        print(str(e))
        return jsonify({
            "err": str(e)}), 500

# Query the product info of a certain store 
@app.route('/api/store/products', methods = ['GET'])
def get_product_info():
    # Fetch the data
    store_id = request.args.get('store_id', '')
    product_id = request.args.get('query', '')
    # Check if it lacks parameter
    if len(product_id) < 1:
        return jsonify({
            "successType": 3,    
        }), 400

    #Get the time
    current_date = datetime.now().date()
    year = current_date.year
    month = current_date.month

    try:
        with DBPool.get_connection() as conn:
            with conn.cursor() as cur:
                # Check if the product exists
                check = """
                    SELECT product_name 
                    FROM product 
                    WHERE product_id = %s
                """
                cur.execute(check, (product_id, ))
                name = cur.fetchone()[0]
                if not name:
                    return jsonify({
                        "successType": 0
                    })
                # Query the store inventory
                query = """
                    SELECT stock_quantity
                    FROM store_inventory
                    WHERE store_id = %s
                    AND product_id = %s
                """
                cur.execute(query, (store_id, product_id, ))
                store_inventory = cur.fetchone()[0]
                # Check if the sales records exists
                check = """
                    SELECT EXISTS(
                        SELECT 1 
                        FROM sales 
                        WHERE product_id = %s
                        AND store_id = %s
                        AND EXTRACT(YEAR FROM sale_date) = %s
                        AND EXTRACT(MONTH FROM sale_date) = %s
                    ) AS is_sales_records_exists
                """
                cur.execute(check, (product_id, store_id, year, month, ))
                if not cur.fetchone()[0]:
                    return jsonify({
                        "successType": 1,
                        "name": name, 
                        "inventory": store_inventory
                    })
                # Query the quantity and price
                query = """
                    SELECT 
                    SUM(quantity) AS total_quantity,
                    unit_price
                    FROM sales
                    WHERE product_id = %s
                    AND store_id = %s
                    AND EXTRACT(YEAR FROM sale_date) = %s
                    AND EXTRACT(MONTH FROM sale_date) = %s
                    GROUP BY unit_price
                """
                cur.execute(query, (product_id, store_id, year, month, ))
                result = cur.fetchone()
                quantity = result[0]
                unit_price = result[1]
                return jsonify({
                    "successType": 2, 
                    "name": name, 
                    "quantity": quantity,
                    "unit_price": unit_price, 
                    "store_inventory": store_inventory
                })
    except Exception as e:
        print(str(e))
        return jsonify({
            "successType": 4,
            "err": str(e)}), 500

# Sell products
@app.route('/api/store/sell', methods = ['POST'])
def sell():
    # Fetch the data
    data = request.get_json()
    store_id = data.get('store_id', '')
    product_id = data.get('product_id', '')
    quantity = data.get('quantity', '')
    # Check if the quantity is correct
    if not (is_positive_integer(quantity)):
        return jsonify({
            "successType": 1
        })

    # Get the date
    current_date = datetime.now().date()

    try:
        with DBPool.get_connection() as conn:
            with conn.cursor() as cur:
                # Check if the product exists
                check = """
                    SELECT EXISTS(
                        SELECT 1 
                        FROM product 
                        WHERE product_id = %s
                    ) AS is_product_exists
                """
                cur.execute(check, (product_id, ))
                if not cur.fetchone()[0]:
                    return jsonify({
                        "successType": 0
                    })
                # Query the inventory of the product
                query_sql = """
                    SELECT stock_quantity
                    FROM store_inventory
                    WHERE store_id = %s
                    AND product_id = %s
                """
                cur.execute(query_sql, (store_id, product_id, ))
                rest_quantity = cur.fetchone()[0]
                # Check if the inventory is sufficient
                if quantity > rest_quantity:
                    return jsonify({
                        "successType": 2
                    })
                # Update the store_inventory table
                update_sql = """
                    UPDATE store_inventory
                    SET
                        stock_quantity = stock_quantity - %s, 
                        last_updated = CURRENT_TIMESTAMP
                    WHERE store_id = %s
                    AND product_id = %s
                """
                cur.execute(update_sql, (quantity, store_id, product_id))
                # Query the unit price
                query_sql = """
                    SELECT unit_price
                    FROM product
                    WHERE product_id = %s
                    GROUP BY unit_price
                """
                cur.execute(query_sql, (product_id, ))
                unit_price = cur.fetchone()[0]
                #Query the sales_id
                query_sql = """
                    SELECT COUNT(*)
                    FROM sales
                    WHERE sales_id LIKE %s
                """
                cur.execute(query_sql, (id_format('SL') + '%', ))
                sales_id = get_id('SL', cur.fetchone()[0] + 1)
                # Insert into the sales table
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
                cur.execute(update_sql, (sales_id, store_id, product_id, current_date, quantity, unit_price, ))
                conn.commit()
                return jsonify({
                    "successType": 3
                })
    except Exception as e:
        return jsonify({
            "successType": 4, 
            "err": str(e)
        }), 500

# Send request
@app.route('/api/request', methods = ['POST'])
def request_approval():
    # Fetch the data
    data = request.get_json()
    quantity = data.get('quantity', '')
    # Check if the quantity is correct
    if not (is_positive_integer(quantity)):
        return jsonify({
            "successType": 2
        })
    from_location_id = data.get('from_id', '')
    to_location_id = data.get('to_id', '')
    product_id = data.get('product_id', '')

    # Get the time
    current_time = datetime.now()

    try:
        with DBPool.get_connection() as conn:
            with conn.cursor() as cur:
                # Check if the product_id exists
                query = """
                    SELECT EXISTS(
                        SELECT 1 
                        FROM product 
                        WHERE product_id = %s
                    ) AS is_product_exists;
                """
                cur.execute(query, (product_id, ))
                if not(cur.fetchone()[0]):
                    return jsonify({
                        "successType": 1
                    })
                # Get the approval_id
                query = """
                    SELECT COUNT(*) AS count
                    FROM transfer_approval
                    WHERE approval_id LIKE %s
                """
                cur.execute(query, (id_format('AP') + '%', ))
                approval_id = get_id('AP', cur.fetchone()[0] + 1)
                # Insert into the transfer_approval table
                insert_sql = """
                    INSERT INTO transfer_approval (
                        approval_id,
                        product_id,
                        from_location_id,
                        to_location_id,
                        quantity,
                        status,
                        request_time
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s
                    )
                """
                print(approval_id, product_id, from_location_id, to_location_id, quantity, '待审核', current_time)
                cur.execute(insert_sql, (approval_id, product_id, from_location_id, to_location_id, quantity, '待审核', current_time, ))
                conn.commit()
                return jsonify({
                    "successType": 3,
                    "request_time": current_time,
                    "approval_id": approval_id
                })
    except Exception as e:
        print(str(e))
        return jsonify({
            "sucessType": 4,
            "err": str(e)
        }), 500

# Accept the approval
@app.route('/api/approval/accepted', methods = ['POST'])
def accepted():
    #Fetch the data
    approval_id = request.get_json().get('approval_id', '')

    # Get the time
    current_time = datetime.now()

    try:
        with DBPool.get_connection() as conn:
            with conn.cursor() as cur:
                # Update the transfer_approval table
                update_sql = """
                    UPDATE transfer_approval
                    SET
                        status = %s,
                        approval_time = %s
                    WHERE approval_id = %s
                """
                cur.execute(update_sql, ('待发货', current_time, approval_id, ))
                conn.commit()
                return jsonify({
                    "successType": 0,
                    "approval_time": current_time
                })
    except Exception as e:
        return jsonify({
            "successType": 1,
            "err": str(e)
        }), 500

@app.route('/api/approval/rejected', methods = ['POST'])
def rejected():
    # Fetch the data
    approval_id = request.get_json().get('approval_id', '')

    # Get the time
    current_time = datetime.now()

    try:
        with DBPool.get_connection() as conn:
            with conn.cursor() as cur:
                # Update the transfer_approval table
                update_sql = """
                    UPDATE transfer_approval
                    SET
                        status = %s,
                        approval_time = %s
                    WHERE approval_id = %s
                """
                cur.execute(update_sql, ('已取消', current_time, approval_id, ))
                conn.commit()
                return jsonify({
                    "successType": 0,
                    "approval_time": current_time
                })
                
    except Exception as e:
        return jsonify({
            "sucessType": 1,
            "err": str(e)
        }), 500

@app.route('/api/approval/cancel', methods = ['POST'])
def cancel():
    # Fetch the data
    approval_id = request.get_json().get('approval_id', '')

    # Get the time
    current_time = datetime.now()

    try:
        with DBPool.get_connection() as conn:
            with conn.cursor() as cur:
                # Update the transfer_approval table
                update_sql = """
                    UPDATE transfer_approval
                    SET
                        status = %s,
                        approval_time = %s
                    WHERE approval_id = %s
                """
                cur.execute(update_sql, ('已取消', current_time, approval_id, ))
                conn.commit()
                return jsonify({
                    "successType": 0
                })
                
    except Exception as e:
        return jsonify({
            "sucessType": 1,
            "err": str(e)
        }), 500

@app.route('/api/shipment', methods = ['POST'])
def shipment():
    # Fetch the data
    approval_id = request.get_json().get('approval_id', '')

    # Get the time
    current_time = datetime.now()
    current_date = current_time.date()

    try:
        with DBPool.get_connection() as conn:
            with conn.cursor() as cur:
                # Query the approval data
                query = """
                    SELECT quantity, product_id, from_location_id
                    FROM transfer_approval
                    WHERE approval_id = %s
                """
                cur.execute(query, (approval_id, ))
                approval_data = cur.fetchone()[0]
                quantity, product_id, from_location_id = approval_data
                # Query the inventory
                query = """
                    SELECT quantity
                    FROM warehouse_inventory
                    WHERE warehouse_id = %s
                    AND product_id = %s
                """
                cur.execute(query, (from_location_id, product_id, ))
                rest_quantity = cur.fetchone()[0]
                # Check if the inventory is sufficient
                if quantity < rest_quantity:
                    return jsonify({
                        "successType": 1,
                    })
                # Update the transfer_approval table
                update_sql = """
                    UPDATE transfer_approval
                    SET
                        status = %s,
                        shipment_time = %s
                    WHERE approval_id = %s
                """
                cur.execute(update_sql, ('待收货', current_time, approval_id, ))
                # Get the log_id
                query = """
                    SELECT COUNT(*) AS count
                    FROM inventory_log
                    WHERE log_id LIKE %s
                """
                cur.execute(query, (id_format('LOG') + '%', ))
                log_id = get_id('LOG', cur.fetchone()[0] + 1)
                # Insert into the inventory_log table
                insert_params = (log_id, product_id, from_location_id, 'OUT', quantity)
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
                cur.execute(insert_sql, [insert_params, ])
                # Update the warehouse_inventory table
                update_params = (-quantity, current_date, from_location_id, product_id)
                update_sql = """
                    UPDATE warehouse_inventory
                    SET 
                        quantity = quantity + %s,
                        record_date = %s
                    WHERE warehouse_id = %s
                    AND product_id = %s
                """
                cur.execute(update_sql, [update_params, ])
                conn.commit()
                return jsonify({
                    "successType": 0,
                    "shipment_time": current_time
                })

    except Exception as e:
        return jsonify({
            "successType": 2,
            "err": str(e)
        }), 500

@app.route('/api/receipt/warehouse', methods = ['POST'])
def receipt_warehouse():
    # Fetch the data
    approval_id = request.get_json().get('approval_id', '')

    # Get the time
    current_time = datetime.now()
    current_date = current_time.date()

    try:
        with DBPool.get_connection() as conn:
            with conn.cursor() as cur:
                # Query the approval data
                query = """
                    SELECT quantity, product_id, to_location_id
                    FROM transfer_approval
                    WHERE approval_id = %s
                """
                cur.execute(query, (approval_id, ))
                approval_data = cur.fetchone()[0]
                quantity, product_id, to_location_id = approval_data
                # Update the transfer_approval table
                update_sql = """
                    UPDATE transfer_approval
                    SET
                        status = %s,
                        receipt_time = %s
                    WHERE approval_id = %s
                """
                cur.execute(update_sql, ('已收货', current_time, approval_id, ))
                # Get the log_id
                query = """
                    SELECT COUNT(*) AS count
                    FROM inventory_log
                    WHERE log_id LIKE %s
                """
                cur.execute(query, (id_format('LOG') + '%', ))
                log_id = get_id('LOG', cur.fetchone()[0] + 1)
                # Insert into the inventory_log table
                insert_params = (log_id, product_id, to_location_id, 'IN', quantity)
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
                cur.execute(insert_sql, [insert_params, ])
                # Update the warehouse_inventory table
                update_params = (quantity, current_date, to_location_id, product_id)
                update_sql = """
                    UPDATE warehouse_inventory
                    SET 
                        quantity = quantity + %s,
                        record_date = %s
                    WHERE warehouse_id = %s
                    AND product_id = %s
                """
                cur.execute(update_sql, [update_params, ])
                conn.commit()
                return jsonify({
                    "successType": 0,
                    "receipt_time": current_time
                })

    except Exception as e:
        return jsonify({
            "successType": 1,
            "err": str(e)
        }), 500

@app.route('/api/receipt/store', methods = ['POST'])
def receipt_store():
    # Fetch the data
    approval_id = request.get_json().get('approval_id', '')

    # Get the time
    current_time = datetime.now()

    try:
        with DBPool.get_connection() as conn:
            with conn.cursor() as cur:
                # Query the approval data
                query = """
                    SELECT quantity, product_id, from_location_id, to_location_id
                    FROM transfer_approval
                    WHERE approval_id = %s
                """
                cur.execute(query, (approval_id, ))
                approval_data = cur.fetchone()[0]
                quantity, product_id, from_location_id, store_id = approval_data
                # Update the transfer_approval table
                update_sql = """
                    UPDATE transfer_approval
                    SET
                        status = %s,
                        receipt_time = %s
                    WHERE approval_id = %s
                """
                cur.execute(update_sql, ('已收货', current_time, approval_id, ))
                # Update the store_inventory table
                update_sql = """
                    UPDATE store_inventory
                    SET 
                        store_quantity = store_quantity + %s,
                        last_updated = %s
                    WHERE store_id = %s
                    AND product_id = %s
                """
                cur.execute(update_sql, (quantity, current_time, store_id, product_id))
                # Get the replenishment_id
                query = """
                    SELECT COUNT(*) AS count
                    FROM replenishment
                    WHERE replenishment_id LIKE %s
                """
                cur.execute(query, (id_format('RP') + '%', ))
                RP_id = get_id('RP', cur.fetchone()[0] + 1)
                # Insert into the replenishment table
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
                cur.execute(insert_sql, (RP_id, from_location_id, store_id, product_id, datetime.now().date(), quantity, quantity, ))
                conn.commit()
                return jsonify({
                    "successType": 0,
                    "receipt_time": current_time
                })

    except Exception as e:
        return jsonify({
            "successType": 1,
            "err": str(e)
        }), 500


if __name__ == '__main__':
    app.run(debug=True)