# -*- coding: utf-8 -*-
from datetime import date, datetime
from typing import List, Dict, Optional, Tuple
from database import DBPool

class Warehouse:
    def __init__(self, warehouse_id: str, warehouse_name: str, address: str):
        self.warehouse_id = warehouse_id
        self.warehouse_name = warehouse_name
        self.address = address
    
    @classmethod
    def get_all(cls) -> List['Warehouse']:
        with DBPool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT warehouse_id, warehouse_name, address 
                    FROM warehouse 
                    ORDER BY warehouse_name
                """)
                return [cls(*row) for row in cur.fetchall()]
    
    @classmethod
    def get_by_id(cls, warehouse_id: str) -> Optional['Warehouse']:
        with DBPool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT warehouse_id, warehouse_name, address FROM warehouse WHERE warehouse_id = %s",
                    (warehouse_id,)
                )
                row = cur.fetchone()
                return cls(*row) if row else None
    
    @classmethod
    def create(cls, warehouse_name: str, address: str) -> str:
        with DBPool.get_connection() as conn:
            with conn.cursor() as cur:
                warehouse_id = f"WH{datetime.now().strftime('%Y%m%d%H%M%S')}"
                cur.execute(
                    "INSERT INTO warehouse (warehouse_id, warehouse_name, address) VALUES (%s, %s, %s)",
                    (warehouse_id, warehouse_name, address)
                )
                conn.commit()
                return warehouse_id

class Store:
    def __init__(self, store_id: str, store_name: str, address: str):
        self.store_id = store_id
        self.store_name = store_name
        self.address = address
    
    @classmethod
    def get_all(cls) -> List['Store']:
        with DBPool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT store_id, store_name, address 
                    FROM store 
                    ORDER BY store_name
                """)
                return [cls(*row) for row in cur.fetchall()]

class Product:
    def __init__(self, product_id: str, product_name: str, unit_price: float):
        self.product_id = product_id
        self.product_name = product_name
        self.unit_price = unit_price
    
    @classmethod
    def get_by_id(cls, product_id: str) -> Optional['Product']:
        with DBPool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT product_id, product_name, unit_price FROM product WHERE product_id = %s",
                    (product_id,)
                )
                row = cur.fetchone()
                return cls(*row) if row else None
    
    @classmethod
    def search(cls, keyword: str, page: int = 1, per_page: int = 10) -> Tuple[List['Product'], int]:
        with DBPool.get_connection() as conn:
            with conn.cursor() as cur:
                offset = (page - 1) * per_page
                cur.execute(
                    """SELECT product_id, product_name, unit_price 
                    FROM product 
                    WHERE product_name ILIKE %s OR product_id ILIKE %s
                    ORDER BY product_name
                    LIMIT %s OFFSET %s""",
                    (f"%{keyword}%", f"%{keyword}%", per_page, offset)
                )
                products = [cls(*row) for row in cur.fetchall()]
                
                cur.execute(
                    "SELECT COUNT(*) FROM product WHERE product_name ILIKE %s OR product_id ILIKE %s",
                    (f"%{keyword}%", f"%{keyword}%")
                )
                total = cur.fetchone()[0]
                
                return products, total
            
    @classmethod
    def create(cls, product_name: str, unit_price: float) -> str:
        with DBPool.get_connection() as conn:
            with conn.cursor() as cur:
                product_id = f"PD{datetime.now().strftime('%Y%m%d%H%M%S')}"
                cur.execute(
                    "INSERT INTO product (product_id, product_name, unit_price) VALUES (%s, %s, %s)",
                    (product_id, product_name, unit_price)
                )
                conn.commit()
                return product_id

    @classmethod
    def update(cls, product_id: str, product_name: str = None, unit_price: float = None) -> bool:
        with DBPool.get_connection() as conn:
            with conn.cursor() as cur:
                updates = []
                params = []
                if product_name:
                    updates.append("product_name = %s")
                    params.append(product_name)
                if unit_price is not None:
                    updates.append("unit_price = %s")
                    params.append(unit_price)
                
                if not updates:
                    return False
                
                params.append(product_id)
                query = f"UPDATE product SET {', '.join(updates)} WHERE product_id = %s"
                cur.execute(query, params)
                conn.commit()
                return cur.rowcount > 0

    @classmethod
    def delete(cls, product_id: str) -> bool:
        with DBPool.get_connection() as conn:
            try:
                with conn.cursor() as cur:
                    conn.autocommit = False
                    # 先删除相关记录
                    cur.execute("DELETE FROM inventory WHERE product_id = %s", (product_id,))
                    cur.execute("DELETE FROM sales WHERE product_id = %s", (product_id,))
                    cur.execute("DELETE FROM supply WHERE product_id = %s", (product_id,))
                    # 再删除商品
                    cur.execute("DELETE FROM product WHERE product_id = %s", (product_id,))
                    conn.commit()
                    return cur.rowcount > 0
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                conn.autocommit = True

    @classmethod
    def add_to_warehouse(cls, product_id: str, warehouse_id: str, quantity: int) -> bool:
        with DBPool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO inventory (warehouse_id, product_id, date, quantity)
                    VALUES (%s, %s, CURRENT_DATE, %s)
                    ON CONFLICT (warehouse_id, product_id, date) 
                    DO UPDATE SET quantity = inventory.quantity + EXCLUDED.quantity
                """, (warehouse_id, product_id, quantity))
                conn.commit()
                return cur.rowcount > 0

    @classmethod
    def remove_from_warehouse(cls, product_id: str, warehouse_id: str, quantity: int = None) -> bool:
        with DBPool.get_connection() as conn:
            try:
                with conn.cursor() as cur:
                    conn.autocommit = False
                    
                    if quantity is None:
                        # 完全移除
                        cur.execute(
                            "DELETE FROM inventory WHERE product_id = %s AND warehouse_id = %s",
                            (product_id, warehouse_id)
                        )
                    else:
                        # 减少指定数量
                        cur.execute(
                            "UPDATE inventory SET quantity = quantity - %s WHERE product_id = %s AND warehouse_id = %s AND quantity >= %s",
                            (quantity, product_id, warehouse_id, quantity)
                        )
                        if cur.rowcount == 0:
                            raise ValueError("库存不足或不存在")
                    
                    conn.commit()
                    return True
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                conn.autocommit = True

    @classmethod
    def add_to_store(cls, product_id: str, store_id: str) -> bool:
        # 添加到商店意味着可以销售，这里简单实现为添加到销售表
        with DBPool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO sales (store_id, product_id, month, monthly_sales)
                    VALUES (%s, %s, CURRENT_DATE, 0)
                    ON CONFLICT (store_id, product_id, month) DO NOTHING
                """, (store_id, product_id))
                conn.commit()
                return cur.rowcount > 0

    @classmethod
    def remove_from_store(cls, product_id: str, store_id: str) -> bool:
        with DBPool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM sales WHERE product_id = %s AND store_id = %s",
                    (product_id, store_id)
                )
                conn.commit()
                return cur.rowcount > 0

class Inventory:
    @staticmethod
    def get_low_inventory(threshold: int = 10) -> List[Dict]:
        with DBPool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT i.warehouse_id, w.warehouse_name, 
                           i.product_id, p.product_name, 
                           i.date, i.quantity
                    FROM inventory i
                    JOIN warehouse w ON i.warehouse_id = w.warehouse_id
                    JOIN product p ON i.product_id = p.product_id
                    WHERE i.quantity < %s
                    ORDER BY i.quantity ASC
                """, (threshold,))
                columns = [desc[0] for desc in cur.description]
                return [dict(zip(columns, row)) for row in cur.fetchall()]
    
    @staticmethod
    def transfer(from_warehouse: str, to_warehouse: str, product_id: str, amount: int) -> bool:
        with DBPool.get_connection() as conn:
            try:
                with conn.cursor() as cur:
                    conn.autocommit = False
                    
                    # 检查源库存
                    cur.execute(
                        """SELECT quantity FROM inventory 
                        WHERE warehouse_id = %s AND product_id = %s 
                        AND date = CURRENT_DATE FOR UPDATE""",
                        (from_warehouse, product_id)
                    )
                    current_qty = cur.fetchone()
                    
                    if not current_qty or current_qty[0] < amount:
                        raise ValueError("库存不足或不存在")
                    
                    # 扣减源库存
                    cur.execute(
                        """UPDATE inventory SET quantity = quantity - %s 
                        WHERE warehouse_id = %s AND product_id = %s 
                        AND date = CURRENT_DATE""",
                        (amount, from_warehouse, product_id))
                    
                    # 增加目标库存
                    cur.execute("""
                        INSERT INTO inventory (warehouse_id, product_id, date, quantity)
                        VALUES (%s, %s, CURRENT_DATE, %s)
                        ON CONFLICT (warehouse_id, product_id, date) 
                        DO UPDATE SET quantity = inventory.quantity + EXCLUDED.quantity
                    """, (to_warehouse, product_id, amount))
                    
                    conn.commit()
                    return True
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                conn.autocommit = True

class Sales:
    @staticmethod
    def get_sales_trend(product_id: str, months: int = 12) -> List[Dict]:
        with DBPool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT s.month, s.monthly_sales, 
                           s.monthly_sales * p.unit_price AS revenue,
                           st.store_name
                    FROM sales s
                    JOIN product p ON s.product_id = p.product_id
                    JOIN store st ON s.store_id = st.store_id
                    WHERE s.product_id = %s
                    ORDER BY s.month DESC
                    LIMIT %s
                """, (product_id, months))
                columns = [desc[0] for desc in cur.description]
                return [dict(zip(columns, row)) for row in cur.fetchall()]
    
    @staticmethod
    def get_store_sales(store_id: str, months: int = 12) -> List[Dict]:
        with DBPool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT p.product_id, p.product_name,
                           SUM(s.monthly_sales) AS total_sales,
                           SUM(s.monthly_sales * p.unit_price) AS total_revenue
                    FROM sales s
                    JOIN product p ON s.product_id = p.product_id
                    WHERE s.store_id = %s
                    AND s.month >= CURRENT_DATE - INTERVAL '%s months'
                    GROUP BY p.product_id, p.product_name
                    ORDER BY total_sales DESC
                """, (store_id, months))
                columns = [desc[0] for desc in cur.description]
                return [dict(zip(columns, row)) for row in cur.fetchall()]

class Supply:
    @staticmethod
    def get_supply_records(warehouse_id: str, months: int = 6) -> List[Dict]:
        with DBPool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT s.product_id, p.product_name,
                           st.store_id, st.store_name,
                           SUM(sp.monthly_supply) AS total_supply,
                           sp.month
                    FROM supply sp,sales s,product p, store st
                    JOIN product p ON sp.product_id = p.product_id
                    JOIN store st ON sp.store_id = st.store_id
                    WHERE sp.warehouse_id = %s
                    AND sp.month >= CURRENT_DATE - INTERVAL '%s months'
                    GROUP BY s.product_id, p.product_name, st.store_id, st.store_name, sp.month
                    ORDER BY sp.month DESC
                """, (warehouse_id, months))
                columns = [desc[0] for desc in cur.description]
                return [dict(zip(columns, row)) for row in cur.fetchall()]