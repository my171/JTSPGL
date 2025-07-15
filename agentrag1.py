import os#运行需要1分钟左右，回答15-30秒左右
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ["HF_HUB_OFFLINE"] = "0"
os.environ["TRANSFORMERS_OFFLINE"] = "0"
#sk-FxhjDpv1D62n33JGICef3aVagezAr73GFnoXmSQ4ikMpf9Hb ；sk-tgq6Xw43DMpw510JMGFofD8UPoBZTRUSrtoywgnbIdx8Z88X
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "sk-tgq6Xw43DMpw510JMGFofD8UPoBZTRUSrtoywgnbIdx8Z88X")#其他api密钥直接改这里，如果closeai的欠费了用这个密钥：sk-tgq6Xw43DMpw510JMGFofD8UPoBZTRUSrtoywgnbIdx8Z88X
os.environ["OPENAI_API_URL"] = os.getenv("OPENAI_API_URL", "https://api.openai-proxy.org/v1")
os.environ["MODEL_NAME"] = os.getenv("MODEL_NAME", "gpt-4.1")#使用的是closeai 的(  gpt-4.1-nano/deepseek-chat  )模型
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"

rag = None  # FastAPI全局变量
import psycopg2
import fitz
import json
import numpy as np
from typing import List, Dict, Tuple, Optional
from fastapi import FastAPI, Request
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.prompts import PromptTemplate
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from collections import deque
import re
import textwrap
import subprocess  # 添加绘图功能
import sys  # 添加绘图功能
import time  # 添加绘图功能
# PostgreSQL配置
PG_HOST = os.getenv('PG_HOST', '192.168.28.135')
PG_PORT = os.getenv('PG_PORT', '5432')
PG_NAME = os.getenv('PG_NAME', 'companylink')
PG_USER = os.getenv('PG_USER', 'myuser')
PG_PASSWORD = os.getenv('PG_PASSWORD', '123456abc.')

#本地知识库所需要pdf文件路径
PDF_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'knowledge_pdfs')

class DatabaseSchemaAnalyzer:
    """动态数据库模式分析器 - 支持任何PostgreSQL数据库"""    
    def __init__(self, conn):
        self.conn = conn
        self.schema_info = {}
        self.table_relationships = {}
        self.analyze_schema()
    
    def analyze_schema(self):
        """分析数据库模式，获取所有表、字段、关系"""
        cursor = self.conn.cursor()
        try:
            # 1. 获取所有表
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            # 2. 获取每个表的字段信息
            for table in tables:
                cursor.execute("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns 
                    WHERE table_name = %s 
                    AND table_schema = 'public'
                    ORDER BY ordinal_position
                """, (table,))
                
                columns = []
                for row in cursor.fetchall():
                    columns.append({
                        'name': row[0],
                        'type': row[1],
                        'nullable': row[2] == 'YES',
                        'default': row[3]
                    })
                
                self.schema_info[table] = columns
            
            # 3. 分析外键关系
            cursor.execute("""
                SELECT 
                    tc.table_name, 
                    kcu.column_name, 
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name 
                FROM information_schema.table_constraints AS tc 
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY' 
                AND tc.table_schema = 'public'
            """)
            
            for row in cursor.fetchall():
                table, column, foreign_table, foreign_column = row
                if table not in self.table_relationships:
                    self.table_relationships[table] = []
                self.table_relationships[table].append({
                    'column': column,
                    'foreign_table': foreign_table,
                    'foreign_column': foreign_column
                })
            
        #    print(f"✅ 数据库模式分析完成：发现 {len(tables)} 个表")
        #   for table in tables:
        #       print(f"   📋 {table}: {len(self.schema_info[table])} 个字段")
                
        except Exception as e:
            print(f"❌ 数据库模式分析失败: {e}")
        finally:
            cursor.close()
    
    def get_schema_summary(self) -> str:
        """获取数据库模式摘要"""
        summary = []
        for table, columns in self.schema_info.items():
            col_names = [col['name'] for col in columns]
            summary.append(f"表 {table}: {', '.join(col_names)}")
        return "\n".join(summary)
    
    def find_related_tables(self, table_name: str) -> List[str]:
        """查找与指定表相关的表"""
        related = set()
        if table_name in self.table_relationships:
            for rel in self.table_relationships[table_name]:
                related.add(rel['foreign_table'])
        
        # 反向查找
        for table, rels in self.table_relationships.items():
            for rel in rels:
                if rel['foreign_table'] == table_name:
                    related.add(table)
        
        return list(related)

class UniversalDatabaseAgent:
    """通用数据库Agent - 支持任何PostgreSQL数据库结构"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model_name=os.getenv("MODEL_NAME", "gpt-4.1"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_api_base=os.getenv("OPENAI_API_URL"),
            temperature=0.3
        )
        self.conn = psycopg2.connect(
            host=PG_HOST, port=PG_PORT, database=PG_NAME, user=PG_USER, password=PG_PASSWORD
        )
        self.schema_analyzer = DatabaseSchemaAnalyzer(self.conn)
    
    def get_data_for_plotting(self, sql: str) -> Optional[List[Dict]]:
        """执行SQL查询并返回字典列表，用于绘图"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql)
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            cursor.close()
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            print(f"❌ SQL执行以获取绘图数据时失败: {e}")
            return None
    
    def analyze_query_intent(self, question: str) -> Dict:
        """智能分析用户查询意图，将自然语言转换为数据库查询需求"""
        try:
            print(f"🧠 开始分析查询意图: {question}")
            
            # 获取数据库模式信息
            schema_summary = self.schema_analyzer.get_schema_summary()
            
                                      # 构建意图分析提示
            intent_prompt = PromptTemplate.from_template("""
你是一个专业的数据库查询意图分析专家。请分析用户的问题，将其转换为具体的数据库查询需求。

数据库模式信息：
{schema_summary}

用户问题：{question}

请分析用户意图并返回JSON格式的查询需求：
{{
    "query_type": "销售分析/库存分析/产品分析/仓库分析/门店分析/补货分析/趋势分析/综合查询",
    "target_tables": ["表名1", "表名2"],
    "target_columns": ["字段1", "字段2"],
    "filter_conditions": {{
        "category": "产品类别（如：ELECTRONICS, BEVERAGE, SNACK等）",
        "location": "位置信息（如：仓库ID、门店ID）",
        "time_range": "时间范围",
        "product_name": "产品名称关键词",
        "warehouse_name": "仓库名称关键词",
        "store_name": "门店名称关键词"
    }},
    "aggregation": {{
        "functions": ["SUM", "COUNT", "AVG", "MAX", "MIN"],
        "group_by": ["分组字段"],
        "order_by": ["排序字段"]
    }},
    "business_insight": "业务洞察需求",
    "confidence": 0.0-1.0
}}

智能识别规则：

1. 产品类别映射（必须准确识别，且category值必须与数据库字段完全一致，区分大小写。例如：ELECTRONICS、BEVERAGE、SNACK、DAILY、FROZEN、APPLIANCE等）：
   - "电子产品"、"电子"、"数码"、"手机"、"电脑"、"耳机"、"充电宝"、"iPhone"、"华为"、"小米" → category: "ELECTRONICS"
   - "饮料"、"矿泉水"、"可乐"、"牛奶"、"茶"、"咖啡"、"红牛"、"伊利" → category: "BEVERAGE" 
   - "零食"、"薯片"、"巧克力"、"饼干"、"坚果"、"糖果"、"乐事"、"德芙"、"奥利奥" → category: "SNACK"
   - "日用品"、"洗发水"、"牙膏"、"香皂"、"纸巾"、"洗衣液"、"海飞丝"、"佳洁士"、"舒肤佳" → category: "DAILY"
   - "冷冻食品"、"冰淇淋"、"水饺"、"牛排"、"汤圆"、"速冻"、"湾仔码头"、"哈根达斯" → category: "FROZEN"
   - "家电"、"空调"、"冰箱"、"吸尘器"、"电视"、"洗衣机"、"戴森"、"美的"、"格力"、"索尼" → category: "APPLIANCE"
   
   ⚠️ 注意：category字段的值必须与数据库实际字段值完全一致，区分大小写（如ELECTRONICS、BEVERAGE等），不要输出小写或其他变体。

2. 查询类型识别：
   - 包含"销售"、"销量"、"销售额"、"卖"、"售出" → query_type: "销售分析"
   - 包含"库存"、"存货"、"库存量"、"库存情况"、"库存状态" → query_type: "库存分析"
   - 包含"产品"、"商品"、"SKU"、"产品信息"、"产品详情"、"查询"、"查看" → query_type: "产品分析"
   - 包含"仓库"、"仓"、"中心仓"、"仓库信息" → query_type: "仓库分析"
   - 包含"门店"、"店铺"、"店"、"门店信息"、"门店情况" → query_type: "门店分析"
   - 包含"补货"、"进货"、"采购"、"补货情况" → query_type: "补货分析"
   - 包含"趋势"、"变化"、"增长"、"趋势分析" → query_type: "趋势分析"

3. 排序和聚合识别：
   - 包含"价格最高"、"最贵"、"最高价" → order_by: ["unit_price DESC"]
   - 包含"价格最低"、"最便宜"、"最低价" → order_by: ["unit_price ASC"]
   - 包含"销量最高"、"最畅销"、"卖得最好" → order_by: ["total_sales_quantity DESC"]
   - 包含"销售额最高"、"收入最高"、"营业额最高" → order_by: ["total_sales_amount DESC"]
   - 包含"库存最多"、"库存量最大" → order_by: ["total_warehouse_stock DESC"]
   - 包含"库存最少"、"库存不足" → order_by: ["total_warehouse_stock ASC"]

4. 位置识别：
   - 包含"北京"、"上海"、"广州"、"深圳"等城市名 → 查找对应的门店或仓库
   - 包含"王府井"、"徐家汇"、"天河城"等具体地点 → 查找对应的门店
   - 包含"华北"、"华东"、"华南"、"西南"等区域 → 查找对应的仓库

5. 时间识别：
   - 包含"今天"、"昨天"、"本周"、"本月"、"最近" → 设置相应的时间范围
   - 包含"7天"、"30天"、"一周"、"一个月" → 设置具体的时间间隔

6. 表关联规则：
   - 销售分析：sales + product + store + warehouse
   - 库存分析：warehouse_inventory + store_inventory + product + warehouse
   - 产品分析：product + sales + warehouse_inventory + store_inventory
   - 仓库分析：warehouse + warehouse_inventory + replenishment + store
   - 门店分析：store + sales + store_inventory + warehouse
   - 补货分析：replenishment + warehouse + store + product

7. 字段映射：
   - 销售相关：quantity(数量), total_amount(金额), sale_date(销售日期)
   - 库存相关：quantity(仓库库存), stock_quantity(门店库存), safety_stock(安全库存)
   - 产品相关：product_name(产品名), category(类别), unit_price(单价), cost_price(成本价)
   - 位置相关：warehouse_name(仓库名), store_name(门店名), address(地址)

8. 业务洞察识别：
   - "价格最高" → business_insight: "查找价格最高的产品，便于了解高端商品定价"
   - "销量最好" → business_insight: "分析最畅销产品，了解市场需求"
   - "库存不足" → business_insight: "识别库存不足的产品，需要补货"
   - "销售趋势" → business_insight: "分析产品销售趋势，预测未来需求"

请仔细分析用户问题，准确识别查询意图，确保返回的JSON格式正确。
只返回JSON格式，不要其他解释。
""")
            
            response = self.llm.invoke(intent_prompt.format(
                schema_summary=schema_summary,
                question=question
            ))
            
            # 解析JSON响应
            intent_data = json.loads(response.content.strip())
            print(f"✅ 查询意图分析完成: {intent_data}")
            
            return intent_data
            
        except Exception as e:
            print(f"❌ 查询意图分析失败: {e}")
            # 返回默认意图
            return {
                "query_type": "综合查询",
                "target_tables": [],
                "target_columns": [],
                "filter_conditions": {},
                "aggregation": {
                    "functions": [],
                    "group_by": [],
                    "order_by": []
                },
                "business_insight": "通用查询",
                "confidence": 0.5
            }
    
    def generate_sql_from_intent(self, intent: Dict) -> Optional[str]:
        """基于查询意图生成SQL"""
        try:
            print(f"🔧 基于意图生成SQL: {intent}")
            
            # 增强意图分析，添加位置信息
            enhanced_intent = self._enhance_intent_with_location(intent)
            print(f"🔧 增强后的意图: {enhanced_intent}")
            
            query_type = enhanced_intent.get("query_type", "综合查询")
            target_tables = enhanced_intent.get("target_tables", [])
            filter_conditions = enhanced_intent.get("filter_conditions", {})
            aggregation = enhanced_intent.get("aggregation", {})
            
            # 根据查询类型生成不同的SQL
            if query_type == "销售分析":
                sql = self._generate_sales_sql(enhanced_intent)
            elif query_type == "库存分析":
                sql = self._generate_inventory_sql(enhanced_intent)
            elif query_type == "产品分析":
                sql = self._generate_product_sql(enhanced_intent)
            elif query_type == "仓库分析":
                sql = self._generate_warehouse_sql(enhanced_intent)
            elif query_type == "门店分析":
                sql = self._generate_store_sql(enhanced_intent)
            elif query_type == "补货分析":
                sql = self._generate_replenishment_sql(enhanced_intent)
            elif query_type == "趋势分析":
                sql = self._generate_trend_sql(enhanced_intent)
            else:
                sql = self._generate_general_sql(enhanced_intent)
            
            print(f"✅ 生成的SQL: {sql}")
            return sql
            
        except Exception as e:
            print(f"❌ SQL生成失败: {e}")
            return None
    
    def _generate_sales_sql(self, intent: Dict) -> str:
        """生成销售分析SQL"""
        filter_conditions = intent.get("filter_conditions", {})
        
        sql = """
        SELECT 
            p.product_name,
            p.category,
            st.store_name,
            w.warehouse_name,
            s.sale_date,
            s.quantity,
            s.unit_price,
            s.total_amount
        FROM sales s
        JOIN product p ON s.product_id = p.product_id
        JOIN store st ON s.store_id = st.store_id
        LEFT JOIN warehouse w ON st.warehouse_id = w.warehouse_id
        WHERE 1=1
        """
        
        # 添加过滤条件
        if filter_conditions.get("category"):
            sql += f" AND p.category = '{filter_conditions['category']}'"
        
        if filter_conditions.get("location"):
            sql += f" AND (st.store_id = '{filter_conditions['location']}' OR w.warehouse_id = '{filter_conditions['location']}')"
        
        if filter_conditions.get("product_name"):
            sql += f" AND p.product_name LIKE '%{filter_conditions['product_name']}%'"
        
        if filter_conditions.get("store_name"):
            sql += f" AND st.store_name LIKE '%{filter_conditions['store_name']}%'"
        
        sql += " ORDER BY s.sale_date DESC LIMIT 20"
        
        return sql
    
    def _generate_inventory_sql(self, intent: Dict) -> str:
        """生成库存分析SQL"""
        filter_conditions = intent.get("filter_conditions", {})
        
        sql = """
        SELECT 
            p.product_name,
            p.category,
            w.warehouse_name,
            wi.quantity as warehouse_quantity,
            si.stock_quantity as store_quantity,
            si.safety_stock,
            wi.record_date
        FROM warehouse_inventory wi
        JOIN product p ON wi.product_id = p.product_id
        JOIN warehouse w ON wi.warehouse_id = w.warehouse_id
        LEFT JOIN store_inventory si ON wi.product_id = si.product_id
        WHERE 1=1
        """
        
        # 添加过滤条件
        if filter_conditions.get("category"):
            sql += f" AND p.category = '{filter_conditions['category']}'"
        
        if filter_conditions.get("location"):
            sql += f" AND (w.warehouse_id = '{filter_conditions['location']}' OR si.store_id = '{filter_conditions['location']}')"
        
        if filter_conditions.get("product_name"):
            sql += f" AND p.product_name LIKE '%{filter_conditions['product_name']}%'"
        
        if filter_conditions.get("warehouse_name"):
            sql += f" AND w.warehouse_name LIKE '%{filter_conditions['warehouse_name']}%'"
        
        sql += " ORDER BY wi.record_date DESC LIMIT 20"
        
        return sql
    
    def _generate_product_sql(self, intent: Dict) -> str:
        """生成产品分析SQL"""
        filter_conditions = intent.get("filter_conditions", {})
        
        # 检查是否需要按价格排序
        aggregation = intent.get("aggregation", {})
        order_by = aggregation.get("order_by", [])
        
        # 基础SQL
        sql = """
        SELECT 
            p.product_id,
            p.product_name,
            p.category,
            p.unit_price,
            p.cost_price,
            p.barcode,
            COALESCE(SUM(s.quantity), 0) as total_sales_quantity,
            COALESCE(SUM(s.total_amount), 0) as total_sales_amount,
            COALESCE(SUM(wi.quantity), 0) as total_warehouse_stock,
            COALESCE(SUM(si.stock_quantity), 0) as total_store_stock
        FROM product p
        LEFT JOIN sales s ON p.product_id = s.product_id
        LEFT JOIN warehouse_inventory wi ON p.product_id = wi.product_id
        LEFT JOIN store_inventory si ON p.product_id = si.product_id
        WHERE 1=1
        """
        
        # 添加过滤条件
        if filter_conditions.get("category"):
            sql += f" AND p.category = '{filter_conditions['category']}'"
        
        if filter_conditions.get("product_name"):
            sql += f" AND p.product_name LIKE '%{filter_conditions['product_name']}%'"
        
        sql += " GROUP BY p.product_id, p.product_name, p.category, p.unit_price, p.cost_price, p.barcode"
        
        # 根据意图选择排序方式
        if "价格最高" in intent.get("business_insight", "") or "unit_price DESC" in order_by:
            sql += " ORDER BY p.unit_price DESC"
        elif "价格最低" in intent.get("business_insight", "") or "unit_price ASC" in order_by:
            sql += " ORDER BY p.unit_price ASC"
        elif "销量最高" in intent.get("business_insight", "") or "total_sales_quantity DESC" in order_by:
            sql += " ORDER BY total_sales_quantity DESC"
        elif "销售额最高" in intent.get("business_insight", "") or "total_sales_amount DESC" in order_by:
            sql += " ORDER BY total_sales_amount DESC"
        else:
            sql += " ORDER BY p.product_name"
        
        sql += " LIMIT 20"
        
        return textwrap.dedent(sql)
    
    def _generate_warehouse_sql(self, intent: Dict) -> str:
        """生成仓库分析SQL"""
        filter_conditions = intent.get("filter_conditions", {})
        
        sql = """
        SELECT 
            w.warehouse_id,
            w.warehouse_name,
            w.address,
            w.created_at,
            COUNT(DISTINCT wi.product_id) as product_count,
            SUM(wi.quantity) as total_inventory,
            COUNT(DISTINCT r.replenishment_id) as replenishment_count,
            COUNT(DISTINCT st.store_id) as store_count
        FROM warehouse w
        LEFT JOIN warehouse_inventory wi ON w.warehouse_id = wi.warehouse_id
        LEFT JOIN replenishment r ON w.warehouse_id = r.warehouse_id
        LEFT JOIN store st ON w.warehouse_id = st.warehouse_id
        WHERE 1=1
        """
        
        # 添加过滤条件
        if filter_conditions.get("location"):
            sql += f" AND w.warehouse_id = '{filter_conditions['location']}'"
        
        if filter_conditions.get("warehouse_name"):
            sql += f" AND w.warehouse_name LIKE '%{filter_conditions['warehouse_name']}%'"
        
        sql += " GROUP BY w.warehouse_id, w.warehouse_name, w.address, w.created_at"
        sql += " ORDER BY total_inventory DESC LIMIT 20"
        
        return textwrap.dedent(sql)
    
    def _generate_store_sql(self, intent: Dict) -> str:
        """生成门店分析SQL"""
        filter_conditions = intent.get("filter_conditions", {})
        
        sql = """
        SELECT 
            st.store_id,
            st.store_name,
            st.address,
            st.opened_date,
            w.warehouse_name,
            COUNT(DISTINCT s.sales_id) as sales_count,
            SUM(s.quantity) as total_sales_quantity,
            SUM(s.total_amount) as total_sales_amount,
            COUNT(DISTINCT si.product_id) as product_count,
            SUM(si.stock_quantity) as total_stock
        FROM store st
        LEFT JOIN warehouse w ON st.warehouse_id = w.warehouse_id
        LEFT JOIN sales s ON st.store_id = s.store_id
        LEFT JOIN store_inventory si ON st.store_id = si.store_id
        WHERE 1=1
        """
        
        # 添加过滤条件
        if filter_conditions.get("location"):
            sql += f" AND st.store_id = '{filter_conditions['location']}'"
        
        if filter_conditions.get("store_name"):
            sql += f" AND st.store_name LIKE '%{filter_conditions['store_name']}%'"
        
        sql += " GROUP BY st.store_id, st.store_name, st.address, st.opened_date, w.warehouse_name"
        sql += " ORDER BY total_sales_amount DESC LIMIT 20"
        
        return textwrap.dedent(sql)
    
    def _generate_replenishment_sql(self, intent: Dict) -> str:
        """生成补货分析SQL"""
        filter_conditions = intent.get("filter_conditions", {})
        
        sql = """
        SELECT 
            r.replenishment_id,
            w.warehouse_name,
            st.store_name,
            p.product_name,
            p.category,
            r.shipment_date,
            r.shipped_quantity,
            r.received_quantity,
            r.status,
            (r.shipped_quantity - COALESCE(r.received_quantity, 0)) as pending_quantity
        FROM replenishment r
        JOIN warehouse w ON r.warehouse_id = w.warehouse_id
        JOIN store st ON r.store_id = st.store_id
        JOIN product p ON r.product_id = p.product_id
        WHERE 1=1
        """
        
        # 添加过滤条件
        if filter_conditions.get("location"):
            sql += f" AND (r.warehouse_id = '{filter_conditions['location']}' OR r.store_id = '{filter_conditions['location']}')"
        
        if filter_conditions.get("category"):
            sql += f" AND p.category = '{filter_conditions['category']}'"
        
        sql += " ORDER BY r.shipment_date DESC LIMIT 20"
        
        return textwrap.dedent(sql)
    
    def _generate_trend_sql(self, intent: Dict) -> str:
        """生成趋势分析SQL"""
        filter_conditions = intent.get("filter_conditions", {})
        
        sql = """
        SELECT 
            DATE_TRUNC('day', s.sale_date) as sale_day,
            p.category,
            SUM(s.quantity) as daily_sales_quantity,
            SUM(s.total_amount) as daily_sales_amount,
            COUNT(DISTINCT s.sales_id) as daily_order_count
        FROM sales s
        JOIN product p ON s.product_id = p.product_id
        WHERE 1=1
        """
        
        # 添加过滤条件
        if filter_conditions.get("category"):
            sql += f" AND p.category = '{filter_conditions['category']}'"
        
        if filter_conditions.get("time_range"):
            sql += f" AND s.sale_date >= CURRENT_DATE - INTERVAL '{filter_conditions['time_range']}'"
        
        sql += " GROUP BY DATE_TRUNC('day', s.sale_date), p.category"
        sql += " ORDER BY sale_day DESC, daily_sales_amount DESC LIMIT 20"
        
        return textwrap.dedent(sql)
    
    def _generate_general_sql(self, intent: Dict) -> str:
        """生成通用查询SQL"""
        # 默认查询所有表的基本信息
        sql = """
        SELECT 
            'product' as table_name,
            COUNT(*) as record_count,
            '产品信息表' as description
        FROM product
        UNION ALL
        SELECT 
            'sales' as table_name,
            COUNT(*) as record_count,
            '销售记录表' as description
        FROM sales
        UNION ALL
        SELECT 
            'warehouse' as table_name,
            COUNT(*) as record_count,
            '仓库信息表' as description
        FROM warehouse
        UNION ALL
        SELECT 
            'store' as table_name,
            COUNT(*) as record_count,
            '门店信息表' as description
        FROM store
        ORDER BY record_count DESC
        """
        
        return sql
    
    def _map_location_name(self, location_name: str) -> Dict:
        """智能映射位置名称到数据库ID"""
        try:
            # 城市到门店/仓库的映射
            city_mapping = {
                "北京": {"stores": ["ST101"], "warehouses": ["WH001"]},
                "上海": {"stores": ["ST102"], "warehouses": ["WH002"]},
                "广州": {"stores": ["ST103"], "warehouses": ["WH003"]},
                "深圳": {"stores": ["ST104"], "warehouses": ["WH003"]},
                "成都": {"stores": ["ST105"], "warehouses": ["WH004"]},
                "重庆": {"stores": ["ST106"], "warehouses": ["WH004"]},
                "武汉": {"stores": ["ST107"], "warehouses": ["WH004"]},
                "南京": {"stores": ["ST108"], "warehouses": ["WH002"]},
                "杭州": {"stores": ["ST109"], "warehouses": ["WH002"]},
                "西安": {"stores": ["ST110"], "warehouses": ["WH001"]}
            }
            
            # 具体地点到门店的映射
            place_mapping = {
                "王府井": "ST101",
                "徐家汇": "ST102", 
                "天河城": "ST103",
                "万象城": "ST104",
                "春熙路": "ST105",
                "解放碑": "ST106",
                "武商广场": "ST107",
                "新街口": "ST108",
                "西湖": "ST109",
                "钟楼": "ST110"
            }
            
            # 区域到仓库的映射
            region_mapping = {
                "华北": "WH001",
                "华东": "WH002",
                "华南": "WH003", 
                "西南": "WH004",
                "东北": "WH005"
            }
            
            # 检查城市映射
            for city, mapping in city_mapping.items():
                if city in location_name:
                    return mapping
            
            # 检查具体地点映射
            for place, store_id in place_mapping.items():
                if place in location_name:
                    return {"stores": [store_id], "warehouses": []}
            
            # 检查区域映射
            for region, warehouse_id in region_mapping.items():
                if region in location_name:
                    return {"stores": [], "warehouses": [warehouse_id]}
            
            return {"stores": [], "warehouses": []}
            
        except Exception as e:
            print(f"⚠️ 位置映射失败: {e}")
            return {"stores": [], "warehouses": []}
    
    def _enhance_intent_with_location(self, intent: Dict) -> Dict:
        """增强意图分析，添加位置信息"""
        try:
            filter_conditions = intent.get("filter_conditions", {})
            
            # 检查是否有位置相关的过滤条件
            if filter_conditions.get("location"):
                location_name = filter_conditions["location"]
                location_mapping = self._map_location_name(location_name)
                
                # 根据查询类型选择合适的ID
                query_type = intent.get("query_type", "")
                
                if query_type in ["门店分析", "销售分析"] and location_mapping["stores"]:
                    filter_conditions["location"] = location_mapping["stores"][0]
                elif query_type in ["仓库分析", "库存分析"] and location_mapping["warehouses"]:
                    filter_conditions["location"] = location_mapping["warehouses"][0]
                elif location_mapping["stores"]:
                    filter_conditions["location"] = location_mapping["stores"][0]
                elif location_mapping["warehouses"]:
                    filter_conditions["location"] = location_mapping["warehouses"][0]
            
            intent["filter_conditions"] = filter_conditions
            return intent
            
        except Exception as e:
            print(f"⚠️ 意图位置增强失败: {e}")
            return intent

    def generate_sql(self, question: str) -> Optional[str]:
        """使用LLM生成SQL查询"""
        try:
            # 1. 首先进行查询意图分析
            intent = self.analyze_query_intent(question)
            
            # 2. 基于意图生成SQL
            sql = self.generate_sql_from_intent(intent)
            
            if sql and sql.upper().startswith('SELECT'):
                return sql
            return None
            
        except Exception as e:
            print(f"❌ SQL生成失败: {e}")
            return None
    
    def execute_query(self, sql: str) -> List[Tuple]:
        try:
            print(f"🚀 执行SQL查询: {repr(sql)}")
            print(f"SQL类型: {type(sql)}")
            assert self.conn and self.conn.closed == 0, "数据库连接已关闭"
            cursor = self.conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            cursor.close()
            print(f"✅ 查询执行成功，返回 {len(rows)} 行数据")
            return rows
        except Exception as e:
            print(f"❌ SQL执行失败: {e}")
            import traceback
            traceback.print_exc()
            # 写入日志
            with open("sql_error.log", "a", encoding="utf-8") as f:
                f.write(f"SQL执行失败: {repr(sql)}\n错误: {e}\n")
            return []
    
    def get_column_names(self, sql: str) -> List[str]:
        """获取查询结果的列名"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql)
            column_names = [desc[0] for desc in cursor.description]
            cursor.close()
            return column_names
        except Exception as e:
            print(f"❌ 获取列名失败: {e}")
            return []
    
    def analyze_data_statistics(self, rows: List[Tuple], column_names: List[str]) -> Dict:
        """分析数据统计信息"""
        if not rows or not column_names:
            return {}
        
        stats = {}
        try:
            # 转换为DataFrame格式进行分析
            data_dict = {}
            for i, col_name in enumerate(column_names):
                data_dict[col_name] = [row[i] for row in rows]
            
            # 数值型列统计
            numeric_stats = {}
            for col_name, values in data_dict.items():
                try:
                    # 尝试转换为数值
                    numeric_values = []
                    for val in values:
                        if val is not None:
                            try:
                                numeric_values.append(float(val))
                            except (ValueError, TypeError):
                                continue
                    
                    if numeric_values:
                        numeric_stats[col_name] = {
                            'count': len(numeric_values),
                            'min': min(numeric_values),
                            'max': max(numeric_values),
                            'avg': sum(numeric_values) / len(numeric_values),
                            'sum': sum(numeric_values)
                        }
                except Exception:
                    continue
            
            # 分类列统计
            categorical_stats = {}
            for col_name, values in data_dict.items():
                if col_name not in numeric_stats:
                    try:
                        value_counts = {}
                        for val in values:
                            if val is not None:
                                val_str = str(val)
                                value_counts[val_str] = value_counts.get(val_str, 0) + 1
                        
                        if value_counts:
                            categorical_stats[col_name] = {
                                'unique_count': len(value_counts),
                                'top_values': sorted(value_counts.items(), key=lambda x: x[1], reverse=True)[:5]
                            }
                    except Exception:
                        continue
            
            stats = {
                'total_rows': len(rows),
                'numeric_columns': numeric_stats,
                'categorical_columns': categorical_stats
            }
            
        except Exception as e:
            print(f"⚠️ 数据统计分析失败: {e}")
        
        return stats
    
    def analyze_data_trends(self, rows: List[Tuple], column_names: List[str]) -> Dict:
        """分析数据趋势"""
        if not rows or not column_names:
            return {}
        
        trends = {}
        try:
            # 查找时间相关列
            time_columns = []
            for col_name in column_names:
                if any(keyword in col_name.lower() for keyword in ['time', 'date', 'created', 'updated', 'timestamp']):
                    time_columns.append(col_name)
            
            if time_columns:
                # 分析时间趋势
                for time_col in time_columns:
                    try:
                        time_idx = column_names.index(time_col)
                        time_values = [row[time_idx] for row in rows if row[time_idx] is not None]
                        
                        if time_values:
                            # 简单的时间趋势分析
                            trends[time_col] = {
                                'earliest': min(time_values),
                                'latest': max(time_values),
                                'total_periods': len(time_values)
                            }
                    except Exception:
                        continue
            
            # 分析数值趋势
            data_dict = {}
            for i, col_name in enumerate(column_names):
                data_dict[col_name] = [row[i] for row in rows]
            
            for col_name, values in data_dict.items():
                try:
                    numeric_values = []
                    for val in values:
                        if val is not None:
                            try:
                                numeric_values.append(float(val))
                            except (ValueError, TypeError):
                                continue
                    
                    if len(numeric_values) > 1:
                        # 计算趋势（简单线性趋势）
                        sorted_values = sorted(numeric_values)
                        if sorted_values[0] != sorted_values[-1]:
                            trend_direction = "上升" if sorted_values[-1] > sorted_values[0] else "下降"
                            trends[f"{col_name}_trend"] = {
                                'direction': trend_direction,
                                'range': f"{sorted_values[0]} - {sorted_values[-1]}",
                                'variation': sorted_values[-1] - sorted_values[0]
                            }
                except Exception:
                    continue
                    
        except Exception as e:
            print(f"⚠️ 趋势分析失败: {e}")
        
        return trends
    
    def analyze_data_relationships(self, rows: List[Tuple], column_names: List[str]) -> Dict:
        """分析数据关联关系"""
        if not rows or not column_names:
            return {}
        
        relationships = {}
        try:
            # 分析外键关系
            for table_name, rels in self.schema_analyzer.table_relationships.items():
                for rel in rels:
                    relationships[f"{table_name}.{rel['column']}"] = {
                        'references': f"{rel['foreign_table']}.{rel['foreign_column']}",
                        'type': 'foreign_key'
                    }
            
            # 分析数据中的关联模式
            data_dict = {}
            for i, col_name in enumerate(column_names):
                data_dict[col_name] = [row[i] for row in rows]
            
            # 查找可能的关联列（相同值的列）
            for col1 in column_names:
                for col2 in column_names:
                    if col1 != col2:
                        try:
                            values1 = set(str(data_dict[col1][i]) for i in range(len(rows)) if data_dict[col1][i] is not None)
                            values2 = set(str(data_dict[col2][i]) for i in range(len(rows)) if data_dict[col2][i] is not None)
                            
                            # 计算重叠度
                            overlap = len(values1.intersection(values2))
                            if overlap > 0 and len(values1) > 0 and len(values2) > 0:
                                overlap_ratio = overlap / min(len(values1), len(values2))
                                if overlap_ratio > 0.3:  # 30%以上重叠认为有关联
                                    relationships[f"{col1}_vs_{col2}"] = {
                                        'overlap_count': overlap,
                                        'overlap_ratio': overlap_ratio,
                                        'type': 'data_overlap'
                                    }
                        except Exception:
                            continue
        
        except Exception as e:
            print(f"⚠️ 关联关系分析失败: {e}")
        
        return relationships
    

    
    def query(self, question: str, context: str = "") -> str:
        """通用数据库查询接口 - 直接执行查询并返回具体数据"""
        try:
            print(f"🔍 开始处理查询: {question}")
            
            # 1. 智能生成SQL查询
            sql = self._generate_intelligent_sql(question)
            
            if not sql:
                print("❌ SQL生成失败")
                return "无法理解查询需求，请提供更具体的问题"
            
            print(f"✅ 生成的SQL: {sql}")
            
            # 2. 执行查询
            rows = self.execute_query(sql)
            
            if not rows:
                print("❌ 查询返回空结果")
                return "未找到相关数据，请检查查询条件"
            
            print(f"✅ 查询成功，返回 {len(rows)} 条记录")
            
            # 3. 获取列名
            column_names = self.get_column_names(sql)
            if not column_names:
                column_names = [f"column_{i}" for i in range(len(rows[0]) if rows else 0)]
            
            print(f"✅ 列名: {column_names}")
            
            # 4. 直接返回具体数据和分析
            result = self._format_comprehensive_results(question, rows, column_names, sql)
            print(f"✅ 结果格式化完成，长度: {len(result)} 字符")
            
            return result
            
        except Exception as e:
            print(f"❌ 查询处理失败: {e}")
            import traceback
            traceback.print_exc()
            return f"数据库查询失败: {str(e)}"
    
    def _generate_intelligent_sql(self, question: str) -> Optional[str]:
        """智能生成SQL查询 - 使用意图分析"""
        try:
            print(f"🧠 开始智能SQL生成，问题: {question}")
            
            # 使用新的意图分析功能
            return self.generate_sql(question)
            
        except Exception as e:
            print(f"❌ 智能SQL生成失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def execute_query_with_columns(self, sql: str):
        """执行SQL并返回 (rows, column_names)"""
        try:
            print(f"🚀 执行SQL查询: {repr(sql)}")
            print(f"SQL类型: {type(sql)}")
            assert self.conn and self.conn.closed == 0, "数据库连接已关闭"
            cursor = self.conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            cursor.close()
            print(f"✅ 查询执行成功，返回 {len(rows)} 行数据")
            return rows, column_names
        except Exception as e:
            print(f"❌ SQL执行失败: {e}")
            import traceback
            traceback.print_exc()
            with open("sql_error.log", "a", encoding="utf-8") as f:
                f.write(f"SQL执行失败: {repr(sql)}\\n错误: {e}\\n")
            return [], []
    
    def get_column_names(self, sql: str) -> List[str]:
        """获取查询结果的列名"""
        try:
            print(f"📋 获取列名，SQL: {sql}")
            cursor = self.conn.cursor()
            cursor.execute(sql)
            column_names = [desc[0] for desc in cursor.description]
            cursor.close()
            print(f"✅ 获取列名成功: {column_names}")
            return column_names
        except Exception as e:
            print(f"❌ 获取列名失败: {e}")
            return []
    
    def analyze_data_statistics(self, rows: List[Tuple], column_names: List[str]) -> Dict:
        """分析数据统计信息"""
        if not rows or not column_names:
            return {}
        
        stats = {}
        try:
            # 转换为DataFrame格式进行分析
            data_dict = {}
            for i, col_name in enumerate(column_names):
                data_dict[col_name] = [row[i] for row in rows]
            
            # 数值型列统计
            numeric_stats = {}
            for col_name, values in data_dict.items():
                try:
                    # 尝试转换为数值
                    numeric_values = []
                    for val in values:
                        if val is not None:
                            try:
                                numeric_values.append(float(val))
                            except (ValueError, TypeError):
                                continue
                    
                    if numeric_values:
                        numeric_stats[col_name] = {
                            'count': len(numeric_values),
                            'sum': sum(values),
                            'avg': sum(values) / len(values),
                            'min': min(values),
                            'max': max(values)
                        }
                except Exception:
                    continue
            
            # 分类列统计
            categorical_stats = {}
            for col_name, values in data_dict.items():
                if col_name not in numeric_stats:
                    try:
                        value_counts = {}
                        for val in values:
                            if val is not None:
                                val_str = str(val)
                                value_counts[val_str] = value_counts.get(val_str, 0) + 1
                        
                        if value_counts:
                            categorical_stats[col_name] = {
                                'unique_count': len(value_counts),
                                'top_values': sorted(value_counts.items(), key=lambda x: x[1], reverse=True)[:5]
                            }
                    except Exception:
                        continue
            
            stats = {
                'total_rows': len(rows),
                'numeric_columns': numeric_stats,
                'categorical_columns': categorical_stats
            }
            
        except Exception as e:
            print(f"⚠️ 数据统计分析失败: {e}")
        
        return stats
    
    def analyze_data_trends(self, rows: List[Tuple], column_names: List[str]) -> Dict:
        """分析数据趋势"""
        if not rows or not column_names:
            return {}
        
        trends = {}
        try:
            # 查找时间相关列
            time_columns = []
            for col_name in column_names:
                if any(keyword in col_name.lower() for keyword in ['time', 'date', 'created', 'updated', 'timestamp']):
                    time_columns.append(col_name)
            
            if time_columns:
                # 分析时间趋势
                for time_col in time_columns:
                    try:
                        time_idx = column_names.index(time_col)
                        time_values = [row[time_idx] for row in rows if row[time_idx] is not None]
                        
                        if time_values:
                            # 简单的时间趋势分析
                            trends[time_col] = {
                                'earliest': min(time_values),
                                'latest': max(time_values),
                                'total_periods': len(time_values)
                            }
                    except Exception:
                        continue
            
            # 分析数值趋势
            data_dict = {}
            for i, col_name in enumerate(column_names):
                data_dict[col_name] = [row[i] for row in rows]
            
            for col_name, values in data_dict.items():
                try:
                    numeric_values = []
                    for val in values:
                        if val is not None:
                            try:
                                numeric_values.append(float(val))
                            except (ValueError, TypeError):
                                continue
                    
                    if len(numeric_values) > 1:
                        # 计算趋势（简单线性趋势）
                        sorted_values = sorted(numeric_values)
                        if sorted_values[0] != sorted_values[-1]:
                            trend_direction = "上升" if sorted_values[-1] > sorted_values[0] else "下降"
                            trends[f"{col_name}_trend"] = {
                                'direction': trend_direction,
                                'range': f"{sorted_values[0]} - {sorted_values[-1]}",
                                'variation': sorted_values[-1] - sorted_values[0]
                            }
                except Exception:
                    continue
                    
        except Exception as e:
            print(f"⚠️ 趋势分析失败: {e}")
        
        return trends
    
    def analyze_data_relationships(self, rows: List[Tuple], column_names: List[str]) -> Dict:
        """分析数据关联关系"""
        if not rows or not column_names:
            return {}
        
        relationships = {}
        try:
            # 分析外键关系
            for table_name, rels in self.schema_analyzer.table_relationships.items():
                for rel in rels:
                    relationships[f"{table_name}.{rel['column']}"] = {
                        'references': f"{rel['foreign_table']}.{rel['foreign_column']}",
                        'type': 'foreign_key'
                    }
            
            # 分析数据中的关联模式
            data_dict = {}
            for i, col_name in enumerate(column_names):
                data_dict[col_name] = [row[i] for row in rows]
            
            # 查找可能的关联列（相同值的列）
            for col1 in column_names:
                for col2 in column_names:
                    if col1 != col2:
                        try:
                            values1 = set(str(data_dict[col1][i]) for i in range(len(rows)) if data_dict[col1][i] is not None)
                            values2 = set(str(data_dict[col2][i]) for i in range(len(rows)) if data_dict[col2][i] is not None)
                            
                            # 计算重叠度
                            overlap = len(values1.intersection(values2))
                            if overlap > 0 and len(values1) > 0 and len(values2) > 0:
                                overlap_ratio = overlap / min(len(values1), len(values2))
                                if overlap_ratio > 0.3:  # 30%以上重叠认为有关联
                                    relationships[f"{col1}_vs_{col2}"] = {
                                        'overlap_count': overlap,
                                        'overlap_ratio': overlap_ratio,
                                        'type': 'data_overlap'
                                    }
                        except Exception:
                            continue
        
        except Exception as e:
            print(f"⚠️ 关联关系分析失败: {e}")
        
        return relationships
    

    
    def _format_comprehensive_results(self, question: str, rows: List[Tuple], column_names: List[str], sql: str) -> str:
        """综合格式化查询结果，返回具体数据"""
        try:
            result = f"📊 查询结果：共找到 {len(rows)} 条记录\n\n"
            
            # 1. 显示表头
            result += "📋 数据明细：\n"
            result += " | ".join(f"{name:<15}" for name in column_names) + "\n"
            result += "-" * (len(column_names) * 18) + "\n"
            
            # 2. 显示数据（最多显示15行）
            for i, row in enumerate(rows[:15]):
                formatted_row = []
                for value in row:
                    if value is None:
                        formatted_row.append("NULL".ljust(15))
                    else:
                        str_value = str(value)
                        if len(str_value) > 15:
                            str_value = str_value[:12] + "..."
                        formatted_row.append(str_value.ljust(15))
                result += " | ".join(formatted_row) + "\n"
            
            if len(rows) > 15:
                result += f"... 还有 {len(rows) - 15} 条记录\n"
            
            # 3. 添加统计分析
            result += "\n📈 统计分析：\n"
            
            # 数值列统计
            numeric_stats = self._calculate_numeric_stats(rows, column_names)
            if numeric_stats:
                result += "数值统计：\n"
                for col, stats in numeric_stats.items():
                    result += f"  {col}: 总计{stats['sum']:,.2f}, 平均{stats['avg']:.2f}, 范围{stats['min']}-{stats['max']}\n"
            
            # 分类统计
            categorical_stats = self._calculate_categorical_stats(rows, column_names)
            if categorical_stats:
                result += "\n分类统计：\n"
                for col, stats in categorical_stats.items():
                    result += f"  {col}: {stats['unique_count']}个不同值\n"
                    if stats['top_values']:
                        top_val = stats['top_values'][0]
                        result += f"    最常见: {top_val[0]} ({top_val[1]}次)\n"
            
            # 4. 业务洞察
            result += "\n💡 业务洞察：\n"
            insight = self._generate_comprehensive_insight(question, rows, column_names, sql)
            result += insight
            
            # 5. 数据摘要
            result += "\n📋 数据摘要：\n"
            result += f"• 查询字段：{', '.join(column_names)}\n"
            result += f"• 数据时间：最新记录包含{len(rows)}条数据\n"
            result += f"• 查询类型：{self._identify_query_type(question)}\n"
            
            return result
            
        except Exception as e:
            return f"结果格式化失败: {str(e)}"
    
    def _calculate_numeric_stats(self, rows: List[Tuple], column_names: List[str]) -> Dict:
        """计算数值列统计"""
        stats = {}
        for i, col_name in enumerate(column_names):
            try:
                values = []
                for row in rows:
                    if row[i] is not None:
                        try:
                            values.append(float(row[i]))
                        except (ValueError, TypeError):
                            continue
                
                if values:
                    stats[col_name] = {
                        'count': len(values),
                        'sum': sum(values),
                        'avg': sum(values) / len(values),
                        'min': min(values),
                        'max': max(values)
                    }
            except Exception:
                continue
        return stats
    
    def _calculate_categorical_stats(self, rows: List[Tuple], column_names: List[str]) -> Dict:
        """计算分类列统计"""
        stats = {}
        for i, col_name in enumerate(column_names):
            try:
                value_counts = {}
                for row in rows:
                    if row[i] is not None:
                        val_str = str(row[i])
                        value_counts[val_str] = value_counts.get(val_str, 0) + 1
                
                if value_counts:
                    stats[col_name] = {
                        'unique_count': len(value_counts),
                        'top_values': sorted(value_counts.items(), key=lambda x: x[1], reverse=True)[:3]
                    }
            except Exception:
                continue
        return stats
    
    def _identify_query_type(self, question: str) -> str:
        """识别查询类型"""
        if any(keyword in question for keyword in ["销售", "销售额", "销售情况"]):
            return "销售分析"
        elif any(keyword in question for keyword in ["库存", "存货", "库存情况"]):
            return "库存分析"
        elif any(keyword in question for keyword in ["产品", "商品", "SKU"]):
            return "产品分析"
        elif any(keyword in question for keyword in ["仓库", "仓", "中心仓"]):
            return "仓库分析"
        elif any(keyword in question for keyword in ["趋势", "变化", "增长"]):
            return "趋势分析"
        else:
            return "通用查询"
    
    def _generate_comprehensive_insight(self, question: str, rows: List[Tuple], column_names: List[str], sql: str) -> str:
        """生成综合业务洞察（只输出一次，按query_type分流）"""
        try:
            insight = ""
            query_type = self._identify_query_type(question)
            if query_type == "销售分析":
                insight += self._generate_sales_insight(rows, column_names)
            elif query_type == "库存分析":
                insight += self._generate_inventory_insight(rows, column_names)
            elif query_type == "产品分析":
                insight += self._generate_product_insight(rows, column_names)
            elif query_type == "仓库分析":
                insight += self._generate_warehouse_insight(rows, column_names)
            elif query_type == "趋势分析":
                insight += self._generate_trend_insight(rows, column_names)
            else:
                insight += self._generate_general_insight(rows, column_names, f"查询返回{len(rows)}条记录")
            return insight
        except Exception as e:
            return f"业务洞察生成失败: {str(e)}"
    
    def _generate_product_insight(self, rows: List[Tuple], column_names: List[str]) -> str:
        """生成产品洞察"""
        try:
            insight = ""
            
            # 查找产品相关字段
            product_name_idx = -1
            category_idx = -1
            price_idx = -1
            sales_idx = -1
            
            for i, col in enumerate(column_names):
                if 'product_name' in col.lower() or 'name' in col.lower():
                    product_name_idx = i
                elif 'category' in col.lower():
                    category_idx = i
                elif 'price' in col.lower():
                    price_idx = i
                elif 'sales' in col.lower() or 'amount' in col.lower():
                    sales_idx = i
            
            if product_name_idx >= 0:
                products = set()
                for row in rows:
                    if row[product_name_idx] is not None:
                        products.add(str(row[product_name_idx]))
                insight += f"• 涉及产品：{len(products)}种\n"
                
                if len(products) <= 5:
                    insight += f"• 产品列表：{', '.join(list(products)[:5])}\n"
            
            if category_idx >= 0:
                categories = {}
                for row in rows:
                    if row[category_idx] is not None:
                        cat = str(row[category_idx])
                        categories[cat] = categories.get(cat, 0) + 1
                
                if categories:
                    top_category = max(categories.items(), key=lambda x: x[1])
                    insight += f"• 主要类别：{top_category[0]} ({top_category[1]}条记录)\n"
            
            if sales_idx >= 0:
                total_sales = sum(float(row[sales_idx]) for row in rows if row[sales_idx] is not None)
                insight += f"• 总销售额：¥{total_sales:,.2f}\n"
            
            return insight
            
        except Exception as e:
            return f"产品洞察生成失败: {str(e)}"
    
    def _generate_warehouse_insight(self, rows: List[Tuple], column_names: List[str]) -> str:
        """生成仓库洞察"""
        try:
            insight = ""
            
            # 查找仓库相关字段
            warehouse_name_idx = -1
            inventory_idx = -1
            
            for i, col in enumerate(column_names):
                if 'warehouse' in col.lower():
                    warehouse_name_idx = i
                elif 'inventory' in col.lower() or 'stock' in col.lower():
                    inventory_idx = i
            
            if warehouse_name_idx >= 0:
                warehouses = set()
                for row in rows:
                    if row[warehouse_name_idx] is not None:
                        warehouses.add(str(row[warehouse_name_idx]))
                insight += f"• 涉及仓库：{len(warehouses)}个\n"
                
                if len(warehouses) <= 5:
                    insight += f"• 仓库列表：{', '.join(list(warehouses)[:5])}\n"
            
            if inventory_idx >= 0:
                total_inventory = sum(float(row[inventory_idx]) for row in rows if row[inventory_idx] is not None)
                insight += f"• 总库存量：{total_inventory:,.0f}\n"
            
            return insight
            
        except Exception as e:
            return f"仓库洞察生成失败: {str(e)}"
    
    def _generate_sales_insight(self, rows: List[Tuple], column_names: List[str]) -> str:
        """生成销售洞察"""
        try:
            insight = ""
            
            # 计算总销售额
            total_sales = 0
            total_quantity = 0
            product_sales = {}
            warehouse_sales = {}
            
            for row in rows:
                amount_idx = column_names.index('total_amount') if 'total_amount' in column_names else -1
                quantity_idx = column_names.index('total_quantity') if 'total_quantity' in column_names else -1
                product_idx = column_names.index('product_name') if 'product_name' in column_names else -1
                warehouse_idx = column_names.index('warehouse_name') if 'warehouse_name' in column_names else -1
                
                if amount_idx >= 0 and row[amount_idx] is not None:
                    total_sales += float(row[amount_idx])
                
                if quantity_idx >= 0 and row[quantity_idx] is not None:
                    total_quantity += float(row[quantity_idx])
                
                if product_idx >= 0 and amount_idx >= 0:
                    product = str(row[product_idx])
                    amount = float(row[amount_idx]) if row[amount_idx] is not None else 0
                    product_sales[product] = product_sales.get(product, 0) + amount
                
                if warehouse_idx >= 0 and amount_idx >= 0:
                    warehouse = str(row[warehouse_idx])
                    amount = float(row[amount_idx]) if row[amount_idx] is not None else 0
                    warehouse_sales[warehouse] = warehouse_sales.get(warehouse, 0) + amount
            
            insight += f"• 总销售额：¥{total_sales:,.2f}\n"
            insight += f"• 总销售数量：{total_quantity:,.0f}\n"
            
            if product_sales:
                top_product = max(product_sales.items(), key=lambda x: x[1])
                insight += f"• 热销产品：{top_product[0]} (¥{top_product[1]:,.2f})\n"
            
            if warehouse_sales:
                top_warehouse = max(warehouse_sales.items(), key=lambda x: x[1])
                insight += f"• 销售最佳仓库：{top_warehouse[0]} (¥{top_warehouse[1]:,.2f})\n"
            
            return insight
            
        except Exception as e:
            return f"销售洞察生成失败: {str(e)}"
    
    def _generate_inventory_insight(self, rows: List[Tuple], column_names: List[str]) -> str:
        """生成库存洞察"""
        try:
            insight = ""
            
            total_value = 0
            low_stock_count = 0
            normal_stock_count = 0
            high_stock_count = 0
            
            for row in rows:
                value_idx = column_names.index('inventory_value') if 'inventory_value' in column_names else -1
                status_idx = column_names.index('stock_status') if 'stock_status' in column_names else -1
                
                if value_idx >= 0 and row[value_idx] is not None:
                    total_value += float(row[value_idx])
                
                if status_idx >= 0:
                    status = str(row[status_idx])
                    if '需要补货' in status:
                        low_stock_count += 1
                    elif '库存充足' in status:
                        high_stock_count += 1
                    else:
                        normal_stock_count += 1
            
            insight += f"• 总库存价值：¥{total_value:,.2f}\n"
            insight += f"• 需要补货：{low_stock_count}种产品\n"
            insight += f"• 库存正常：{normal_stock_count}种产品\n"
            insight += f"• 库存充足：{high_stock_count}种产品\n"
            
            return insight
            
        except Exception as e:
            return f"库存洞察生成失败: {str(e)}"
    
    def _generate_trend_insight(self, rows: List[Tuple], column_names: List[str]) -> str:
        """生成趋势洞察"""
        try:
            insight = ""
            
            if len(rows) >= 2:
                amount_idx = column_names.index('monthly_sales_amount') if 'monthly_sales_amount' in column_names else -1
                if amount_idx >= 0:
                    current = float(rows[0][amount_idx]) if rows[0][amount_idx] is not None else 0
                    previous = float(rows[1][amount_idx]) if rows[1][amount_idx] is not None else 0
                    
                    if previous > 0:
                        growth = ((current - previous) / previous) * 100
                        insight += f"• 环比增长率：{growth:+.1f}%\n"
                    
                    insight += f"• 当前月销售额：¥{current:,.2f}\n"
                    insight += f"• 上月销售额：¥{previous:,.2f}\n"
            
            return insight
            
        except Exception as e:
            return f"趋势洞察生成失败: {str(e)}"
    
    def _generate_general_insight(self, rows: List[Tuple], column_names: List[str], data_summary: str) -> str:
        """生成通用洞察"""
        try:
            insight = f"• {data_summary}\n"
            
            # 计算基本统计
            if rows:
                insight += f"• 数据时间范围：最新记录包含{len(rows)}条数据\n"
                
                # 查找可能的数值列进行统计
                numeric_cols = []
                for i, col in enumerate(column_names):
                    try:
                        values = [float(row[i]) for row in rows if row[i] is not None]
                        if values:
                            numeric_cols.append((col, sum(values)))
                    except:
                        continue
                
                if numeric_cols:
                    top_col = max(numeric_cols, key=lambda x: x[1])
                    insight += f"• 主要数值字段：{top_col[0]} (总计{top_col[1]:,.2f})\n"
            
            return insight
            
        except Exception as e:
            return f"通用洞察生成失败: {str(e)}"
    
    def get_database_summary(self) -> str:
        """获取数据库整体摘要"""
        try:
            summary = []
            summary.append(f"数据库连接：{PG_HOST}:{PG_PORT}/{PG_NAME}")
            summary.append(f"表数量：{len(self.schema_analyzer.schema_info)}")
            
            # 统计每个表的数据量
            for table_name in self.schema_analyzer.schema_info.keys():
                try:
                    cursor = self.conn.cursor()
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                    cursor.close()
                    summary.append(f"  {table_name}: {count} 条记录")
                except Exception:
                    summary.append(f"  {table_name}: 无法获取记录数")
            
            return "\n".join(summary)
        except Exception as e:
            return f"数据库摘要获取失败: {str(e)}"
    
    def close(self):
        self.conn.close()

    def build_sql_from_intent(self, intent: Dict) -> str:
        """根据意图结构自动生成SQL，合并所有SQL生成逻辑"""
        query_type = intent.get("query_type", "综合查询")
        filter_conditions = intent.get("filter_conditions", {})
        aggregation = intent.get("aggregation", {})
        order_by = aggregation.get("order_by", [])
        columns = intent.get("target_columns") or []
        # 只查product表的简单查询
        if query_type == "产品分析" and (not columns or set(columns) <= {"product_id","product_name","category","unit_price","cost_price","barcode"}):
            sql = """
            SELECT p.product_id, p.product_name, p.category, p.unit_price, p.cost_price, p.barcode
            FROM product p
            WHERE 1=1
            """
            if filter_conditions.get("category"):
                sql += f" AND p.category = '{filter_conditions['category']}'"
            if filter_conditions.get("product_name"):
                sql += f" AND p.product_name LIKE '%{filter_conditions['product_name']}%'"
            sql += " ORDER BY p.unit_price ASC LIMIT 20"
            return textwrap.dedent(sql)
        # 复杂产品分析（带聚合）
        if query_type == "产品分析":
            sql = """
            SELECT 
                p.product_id,
                p.product_name,
                p.category,
                p.unit_price,
                p.cost_price,
                p.barcode,
                COALESCE(SUM(s.quantity), 0) as total_sales_quantity,
                COALESCE(SUM(s.total_amount), 0) as total_sales_amount,
                COALESCE(SUM(wi.quantity), 0) as total_warehouse_stock,
                COALESCE(SUM(si.stock_quantity), 0) as total_store_stock
            FROM product p
            LEFT JOIN sales s ON p.product_id = s.product_id
            LEFT JOIN warehouse_inventory wi ON p.product_id = wi.product_id
            LEFT JOIN store_inventory si ON p.product_id = si.product_id
            WHERE 1=1
            """
            if filter_conditions.get("category"):
                sql += f" AND p.category = '{filter_conditions['category']}'"
            if filter_conditions.get("product_name"):
                sql += f" AND p.product_name LIKE '%{filter_conditions['product_name']}%'"
            sql += " GROUP BY p.product_id, p.product_name, p.category, p.unit_price, p.cost_price, p.barcode"
            if "unit_price DESC" in order_by:
                sql += " ORDER BY p.unit_price DESC"
            elif "unit_price ASC" in order_by:
                sql += " ORDER BY p.unit_price ASC"
            elif "total_sales_quantity DESC" in order_by:
                sql += " ORDER BY total_sales_quantity DESC"
            elif "total_sales_amount DESC" in order_by:
                sql += " ORDER BY total_sales_amount DESC"
            else:
                sql += " ORDER BY p.product_name"
            sql += " LIMIT 20"
            return textwrap.dedent(sql)
        # 其它类型，调用原有生成方法
        return self.generate_sql_from_intent(intent)

    def execute_query(self, sql: str) -> List[Tuple]:
        try:
            print(f"🚀 执行SQL查询: {repr(sql)}")
            print(f"SQL类型: {type(sql)}")
            assert self.conn and self.conn.closed == 0, "数据库连接已关闭"
            cursor = self.conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            cursor.close()
            print(f"✅ 查询执行成功，返回 {len(rows)} 行数据")
            return rows
        except Exception as e:
            print(f"❌ SQL执行失败: {e}")
            import traceback
            traceback.print_exc()
            with open("sql_error.log", "a", encoding="utf-8") as f:
                f.write(f"SQL执行失败: {repr(sql)}\\n错误: {e}\\n")
            return []

    def query(self, question: str, context: str = "") -> str:
        """主入口：接收用户问题，返回直观化业务数据和分析，不显示SQL"""
        # 1. 意图识别
        intent = self.analyze_query_intent(question)
        print(f"✅ 查询意图分析完成: {intent}")

        # 2. SQL生成
        sql = self.build_sql_from_intent(intent)
        print(f"🔧 基于意图生成SQL: {intent}")  # 仅日志，不输出SQL内容

        # 3. SQL执行
        rows, column_names = self.execute_query_with_columns(sql)
        if rows:
            # 4. 业务洞察与直观化输出
            answer = self._format_query_result(rows, column_names)
            insight = self._generate_comprehensive_insight(question, rows, column_names, sql)
            return f"{answer}\n{insight}"
        else:
            # 5. 数据为空时才考虑知识库/LLM补充
            kb_result = self.query_knowledge_base(question)
            return f"未查询到相关数据库数据。\n{kb_result}"

    def _format_query_result(self, rows, column_names):
        """将数据库查询结果格式化为结构化表格或直观文本"""
        if not rows or not column_names:
            return "未查询到相关数据。"
        # 简单表格输出
        from tabulate import tabulate
        table = tabulate(rows, headers=column_names, tablefmt="fancy_grid", floatfmt=".2f")
        return f"\n📊 查询结果\n{table}\n"

class InMemoryKnowledgeBase:
    def __init__(self):
        self.documents: List[Document] = []
        self.embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        self.vectorstore = None
        self.db_agent = None  # 添加数据库Agent引用

    def set_db_agent(self, db_agent):
        """设置数据库Agent引用"""
        self.db_agent = db_agent

    def load_from_postgres(self):
        """动态加载PostgreSQL数据到知识库"""
        try:
            conn = psycopg2.connect(
                host=PG_HOST, port=PG_PORT, database=PG_NAME, user=PG_USER, password=PG_PASSWORD
            )
            schema_analyzer = DatabaseSchemaAnalyzer(conn)
            
            # 为每个表生成知识片段
            for table_name, columns in schema_analyzer.schema_info.items():
                try:
                    # 获取表的前100行数据作为示例（增加数据量）
                    cursor = conn.cursor()
                    cursor.execute(f"SELECT * FROM {table_name} LIMIT 100")
                    rows = cursor.fetchall()
                    cursor.close()
                    
                    if rows:
                        # 生成表结构描述
                        col_names = [col['name'] for col in columns]
                        table_desc = f"表 {table_name} 包含字段：{', '.join(col_names)}"
                        self.documents.append(Document(
                            page_content=table_desc,
                            metadata={"type": "table_schema", "table": table_name}
                        ))
                        
                        # 生成数据示例（增加更多行）
                        for i, row in enumerate(rows[:10]):  # 增加到10行
                            data_desc = f"{table_name}表数据示例{i+1}：{dict(zip(col_names, row))}"
                            self.documents.append(Document(
                                page_content=data_desc,
                                metadata={"type": "table_data", "table": table_name, "row": i+1}
                            ))
                        
                        # 生成表统计信息
                        try:
                            cursor = conn.cursor()
                            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                            total_count = cursor.fetchone()[0]
                            cursor.close()
                            
                            # 为数值列生成统计信息
                            numeric_cols = [col['name'] for col in columns if 'int' in col['type'] or 'decimal' in col['type'] or 'float' in col['type']]
                            if numeric_cols:
                                for col in numeric_cols[:3]:  # 限制统计列数
                                    try:
                                        cursor = conn.cursor()
                                        cursor.execute(f"SELECT AVG({col}), MIN({col}), MAX({col}) FROM {table_name} WHERE {col} IS NOT NULL")
                                        stats = cursor.fetchone()
                                        cursor.close()
                                        if stats and stats[0] is not None:
                                            stats_desc = f"{table_name}表{col}字段统计：平均{stats[0]:.2f}, 最小{stats[1]}, 最大{stats[2]}, 总记录{total_count}"
                                            self.documents.append(Document(
                                                page_content=stats_desc,
                                                metadata={"type": "table_stats", "table": table_name, "column": col}
                                            ))
                                    except Exception:
                                        continue
                        except Exception:
                            pass
                
                except Exception as e:
                    print(f"⚠️ 处理表 {table_name} 时出错: {e}")
                    continue
            
            conn.close()
            print(f"✅ 成功加载 {len(self.documents)} 个数据库知识片段")
        except Exception as e:
            print(f"❌ 数据库知识加载失败: {e}")

    def get_realtime_data_context(self, question: str) -> str:
        """获取实时数据库数据上下文"""
        if not self.db_agent:
            return ""
        
        try:
            # 使用数据库Agent进行实时查询
            db_result = self.db_agent.query(question)
            if db_result and "未找到相关数据" not in db_result:
                return f"实时数据库查询结果：\n{db_result}"
        except Exception as e:
            print(f"⚠️ 实时数据查询失败: {e}")
        
        return ""

    def query_with_database_context(self, question: str) -> str:
        """结合数据库上下文的知识库查询"""
        try:
            # 1. 获取知识库检索结果
            if not self.vectorstore:
                return "知识库未初始化"
            
            docs = self.vectorstore.similarity_search(question, k=5)
            knowledge_context = self._format_knowledge_context(docs)
            
            # 2. 获取实时数据库上下文
            realtime_context = self.get_realtime_data_context(question)
            
            # 3. 结合分析
            if realtime_context:
                combined_context = f"{knowledge_context}\n\n{realtime_context}"
            else:
                combined_context = knowledge_context
            
            return combined_context
            
        except Exception as e:
            return f"知识库查询失败: {str(e)}"

    def _format_knowledge_context(self, docs: List[Document]) -> str:
        """格式化知识库上下文"""
        if not docs:
            return ""
        
        formatted_contexts = []
        for i, doc in enumerate(docs[:3]):
            content = doc.page_content.strip()
            # 清理和格式化文本
            content = re.sub(r'\n+', ' ', content)
            content = re.sub(r'\s+', ' ', content)
            content = content[:400] + "..." if len(content) > 400 else content
            
            # 添加元数据信息
            metadata_info = ""
            if doc.metadata.get("type") == "table_schema":
                metadata_info = f" [表结构]"
            elif doc.metadata.get("type") == "table_data":
                metadata_info = f" [数据示例]"
            elif doc.metadata.get("type") == "table_stats":
                metadata_info = f" [统计信息]"
            elif doc.metadata.get("type") == "pdf":
                metadata_info = f" [PDF: {doc.metadata.get('source', 'unknown')}]"
            
            formatted_contexts.append(f"知识片段{i+1}{metadata_info}: {content}")
        
        return "\n".join(formatted_contexts)

    def load_from_pdfs(self, pdf_dir=PDF_DIR):
        if not os.path.exists(pdf_dir):
            print(f"⚠️ PDF目录不存在: {pdf_dir}")
            return
        for fname in os.listdir(pdf_dir):
            if not fname.lower().endswith('.pdf'):
                continue
            path = os.path.join(pdf_dir, fname)
            try:
                doc = fitz.open(path)
                for page_num in range(len(doc)):
                    text = doc.load_page(page_num).get_text()
                    if text.strip():
                        self.documents.append(Document(
                            page_content=text,
                            metadata={"type": "pdf", "source": fname, "page": page_num + 1}
                        ))
                doc.close()
            except Exception as e:
                print(f"❌ 解析PDF失败: {fname} {e}")

    def build_vectorstore(self):
        if not self.documents:
            raise RuntimeError("没有知识片段可用于向量化")
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        docs = splitter.split_documents(self.documents)
        self.vectorstore = FAISS.from_documents(docs, self.embeddings)

    def cleanup(self):
        self.documents.clear()
        self.vectorstore = None
class PDFMultiAgent:
    """PDF Agent，支持多文档检索"""
    def __init__(self, kb: InMemoryKnowledgeBase):
        self.kb = kb
    def query(self, question: str) -> str:
        docs = [d for d in self.kb.documents if d.metadata.get("type") == "pdf"]
        if not docs:
            return "无PDF知识库"
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        pdf_chunks = splitter.split_documents(docs)
        embeddings = self.kb.embeddings
        vectorstore = FAISS.from_documents(pdf_chunks, embeddings)
        results = vectorstore.similarity_search(question, k=3)
        if results:
            return "\n\n".join([r.page_content[:200] for r in results])
        return "未找到相关PDF内容"
class MemoryAgent:
    """记忆Agent - 负责上下文学习和对话历史管理"""
    def __init__(self, max_memory_size=10):
        self.conversation_history = deque(maxlen=max_memory_size)
        self.context_summary = ""
        self.llm = ChatOpenAI(
            model_name=os.getenv("MODEL_NAME", "gpt-4.1"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_api_base=os.getenv("OPENAI_API_URL"),
            temperature=0.3
        )
    def add_interaction(self, question: str, answer: str, context: str = ""):
        """添加对话交互到记忆"""
        interaction = {
            "question": question,
            "answer": answer,
            "context": context,
            "timestamp": len(self.conversation_history) + 1
        }
        self.conversation_history.append(interaction)
        self._update_context_summary()
    def _update_context_summary(self):
        """更新上下文摘要"""
        if not self.conversation_history:
            self.context_summary = ""
            return
        
        try:
            recent_interactions = list(self.conversation_history)[-3:]  # 最近3次交互
            summary_prompt = PromptTemplate.from_template("""
基于以下最近的对话历史，生成一个简洁的上下文摘要，用于理解用户的连续问题：
对话历史：
{history}
请生成一个简洁的上下文摘要，突出关键信息和用户关注点：
""")
            
            history_text = "\n".join([
                f"Q{i+1}: {interaction['question']}\nA{i+1}: {interaction['answer'][:100]}..."
                for i, interaction in enumerate(recent_interactions)
            ])
            
            response = self.llm.invoke(summary_prompt.format(history=history_text))
            self.context_summary = response.content.strip()
            
        except Exception as e:
            print(f"⚠️ 上下文摘要更新失败: {e}")
            self.context_summary = ""
    
    def get_context_for_query(self, current_question: str) -> str:
        """为当前查询获取相关上下文"""
        if not self.conversation_history:
            return ""
        # 检查当前问题是否涉及之前的上下文
        context_keywords = ["结合", "基于", "根据", "之前", "上述", "前面", "第一个问题"]
        has_context_reference = any(keyword in current_question for keyword in context_keywords)
        
        if has_context_reference and self.context_summary:
            return f"对话上下文：{self.context_summary}\n"
        
        return ""
    def clear_memory(self):
        """清空记忆"""
        self.conversation_history.clear()
        self.context_summary = ""

class DrawingAgent:
    """绘图Agent - 负责生成并执行绘图代码"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model_name=os.getenv("MODEL_NAME", "gpt-4.1"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_api_base=os.getenv("OPENAI_API_URL"),
            temperature=0.4
        )
    
    def _extract_code(self, text: str) -> str:
        """从文本中提取Python代码块"""
        if '```python' in text:
            start = text.find('```python') + len('```python')
            end = text.find('```', start)
            return text[start:end].strip()
        elif '```' in text:
            start = text.find('```') + 3
            end = text.find('```', start)
            return text[start:end].strip()
        return text
    
    def draw(self, question: str, data_context: str = "") -> str:
        """根据问题和数据上下文生成并执行绘图代码"""
        timestamp = int(time.time())
        plot_filename = f"plot_{timestamp}.png"
        plot_context = ""
        if data_context:
            plot_context = f"""
Please use the following JSON data for plotting, do not fabricate data:
--- DATA START ---
{data_context}
--- DATA END ---
"""
        plot_prompt_template = PromptTemplate.from_template("""
You are a data visualization expert. Please generate complete Python code to create charts based on the user's question and provided data.

{plot_context}

User Question: {question}

Code Requirements:
1. Use `matplotlib.pyplot` library and alias it as `plt`.
2. **Before calling `plt.show()`, you must save the chart to a file named '{plot_filename}'.**
3. **Finally, you must call `plt.show()` to display the image.**
4. The code must be complete and directly runnable.
5. Use English for chart labels and titles to avoid encoding issues.
6. If JSON data is provided, parse it and use the actual data. If no data provided, create reasonable sample data.
7. Add appropriate title and axis labels to the chart.
8. Add a note at the bottom center: 'Note: Data is for reference only.'
9. For database data, focus on meaningful visualizations like bar charts, pie charts, or line charts.
10. Only return Python code block wrapped in ```python ... ```, no additional explanations.

Data Processing Tips:
- If JSON data is provided, use `json.loads()` to parse it
- Handle potential encoding issues with Chinese characters
- Choose appropriate chart types based on data structure
- For numerical data, consider bar charts or line charts
- For categorical data, consider pie charts or bar charts
""")
        final_prompt = plot_prompt_template.format(question=question, plot_context=plot_context,
                                                   plot_filename=plot_filename)
        attempt = 0
        max_attempts = 5
        conversation = [{"role": "system",
                         "content": "You are a helpful AI assistant that generates Python code for plotting graphs using matplotlib."}]
        conversation.append({"role": "user", "content": final_prompt})
        while attempt < max_attempts:
            attempt += 1
            print(f"\n[绘图尝试 {attempt}/{max_attempts}] 正在向LLM请求绘图代码...")
            response = self.llm.invoke(conversation)
            ai_response = response.content.strip()
            code = self._extract_code(ai_response)
            if not code:
                print(f"❌ 绘图失败: LLM未返回有效的代码。")
                conversation.append({"role": "assistant", "content": ai_response})
                conversation.append(
                    {"role": "user", "content": "You did not return any code. Please only return code blocks wrapped in ```python."})
                continue

            # 清理代码，移除可能的问题代码
            code = code.replace("matplotlib.use('Agg')", "")
            code = code.replace("plt.show()", "")
            code = re.sub(r"plt\.savefig\s*\(['\"].*?['\"]\)", "", code, flags=re.DOTALL)
            
            # 添加系统控制的保存和显示命令
            code += f"\n\n# Adding save and show commands by the system #wh_add_draw\n"
            code += f"plt.savefig('{plot_filename}', dpi=300, bbox_inches='tight') #wh_add_draw\n"
            code += f"plt.show() #wh_add_draw\n"

            script_name = f"temp_plot_{timestamp}_{attempt}.py"
            with open(script_name, "w", encoding="utf-8") as f:
                f.write(code)
            try:
                # 修复Windows编码问题
                result = subprocess.run(
                    [sys.executable, script_name],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',  # 明确指定UTF-8编码
                    timeout=30,
                    env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}  # 设置Python IO编码
                )
                if result.returncode == 0 and os.path.exists(plot_filename):
                    print(f"✅ 绘图成功! 图像已保存到: {os.path.abspath(plot_filename)}")
                    os.remove(script_name)
                    return f"绘图成功，文件保存在: {os.path.abspath(plot_filename)}"
                else:
                    error_msg = f"代码执行失败或未生成图像文件。\nReturn Code: {result.returncode}\nStderr: {result.stderr}"
                    print(f"❌ {error_msg}")
                    conversation.append({"role": "assistant", "content": ai_response})
                    feedback = f"Your generated code execution failed, error message: {error_msg}. Please fix it and regenerate complete code."
                    conversation.append({"role": "user", "content": feedback})
            except subprocess.TimeoutExpired:
                error_msg = "Execution timeout: Plotting code ran too long."
                print(f"❌ {error_msg}")
                conversation.append({"role": "assistant", "content": ai_response})
                conversation.append(
                    {"role": "user", "content": f"Your generated code execution timed out. Please optimize the code to run faster."})
            except Exception as e:
                error_msg = f"Execution exception: {str(e)}"
                print(f"❌ {error_msg}")
                os.remove(script_name)
                return f"绘图时发生未知错误: {error_msg}"
            finally:
                if os.path.exists(script_name):
                    os.remove(script_name)
        return f"⚠️ 经过 {max_attempts} 次尝试，仍然无法成功生成图像。"

class TopAgent:
    """TopAgent - 作为中枢大脑，负责理解、分析和Agent协调"""
    def __init__(self, memory_agent: MemoryAgent, db_agent, pdf_agent, kb, drawing_agent):
        self.memory_agent = memory_agent
        self.db_agent = db_agent
        self.pdf_agent = pdf_agent
        self.kb = kb
        self.drawing_agent = drawing_agent
        self.llm = ChatOpenAI(
            model_name=os.getenv("MODEL_NAME", "gpt-4.1"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_api_base=os.getenv("OPENAI_API_URL"),
            temperature=0.3
        )
        # 初始化语义检索组件
        self.embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        self.candidate_examples = self._initialize_candidate_examples()
        self.candidate_vectors = None
        self._build_candidate_vectors()
    
    def _initialize_candidate_examples(self) -> List[Dict]:
        """初始化候选示例库"""
        examples = [
            {
                "task": "库存分析",
                "examples": [
                    "分析库存物品的ABC分类",
                    "计算库存周转率",
                    "识别滞销商品",
                    "分析库存结构",
                    "评估库存成本"
                ]
            },
            {
                "task": "仓储规划",
                "examples": [
                    "优化存储策略",
                    "设计货架布局",
                    "规划仓储空间",
                    "确定存储位置",
                    "分析存储效率"
                ]
            },
            {
                "task": "订单管理",
                "examples": [
                    "分析订单趋势",
                    "处理订单异常",
                    "优化订单流程",
                    "统计订单数据",
                    "预测订单量"
                ]
            },
            {
                "task": "供应链分析",
                "examples": [
                    "分析供应商绩效",
                    "评估供应链风险",
                    "优化采购策略",
                    "监控供应链状态",
                    "分析物流成本"
                ]
            },
            {
                "task": "数据查询",
                "examples": [
                    "查询商品信息",
                    "统计销售数据",
                    "分析客户行为",
                    "查看库存状态",
                    "导出报表数据"
                ]
            }
        ]
        return examples
    def _build_candidate_vectors(self):
        """离线构建候选示例的向量表征"""
        try:
            all_examples = []
            for task_group in self.candidate_examples:
                for example in task_group["examples"]:
                    all_examples.append({
                        "text": example,
                        "task": task_group["task"],
                        "full_text": f"{task_group['task']}: {example}"
                    })
            # 批量生成向量表征
            texts = [item["full_text"] for item in all_examples]
            vectors = self.embeddings.embed_documents(texts)
            # 存储向量和元数据
            self.candidate_vectors = []
            for i, (item, vector) in enumerate(zip(all_examples, vectors)):
                self.candidate_vectors.append({
                    "id": i,
                    "text": item["text"],
                    "task": item["task"],
                    "full_text": item["full_text"],
                    "vector": vector
                })
            
            print(f"✅ 成功构建 {len(self.candidate_vectors)} 个候选示例的向量表征")
        except Exception as e:
            print(f"❌ 候选示例向量构建失败: {e}")
            self.candidate_vectors = []
    
    def _calculate_semantic_similarity(self, query_vector, candidate_vector) -> float:
        """计算语义相似度（余弦相似度）"""
        try:
            query_np = np.array(query_vector)
            candidate_np = np.array(candidate_vector)
            # 计算余弦相似度
            dot_product = np.dot(query_np, candidate_np)
            query_norm = np.linalg.norm(query_np)
            candidate_norm = np.linalg.norm(candidate_np)
            if query_norm == 0 or candidate_norm == 0:
                return 0.0
            
            similarity = dot_product / (query_norm * candidate_norm)
            return float(similarity)
            
        except Exception as e:
            print(f"⚠️ 相似度计算失败: {e}")
            return 0.0
    def _knn_semantic_search(self, query: str, k: int = 5) -> List[Dict]:
        """基于KNN的语义相似度检索"""
        if not self.candidate_vectors:
            return []
        try:
            # 实时表征用户输入
            query_vector = self.embeddings.embed_query(query)
            # 计算与所有候选示例的相似度
            similarities = []
            for candidate in self.candidate_vectors:
                similarity = self._calculate_semantic_similarity(query_vector, candidate["vector"])
                similarities.append({
                    "candidate": candidate,
                    "similarity": similarity
                })
            
            # 按相似度排序，取前k个
            similarities.sort(key=lambda x: x["similarity"], reverse=True)
            top_k_results = similarities[:k]
            
            return top_k_results
        except Exception as e:
            print(f"⚠️ KNN语义检索失败: {e}")
            return []
    def _enhance_query_with_semantic_context(self, query: str) -> str:
        """基于语义检索增强查询上下文"""
        semantic_results = self._knn_semantic_search(query, k=3)
        
        if not semantic_results:
            return query
        # 构建语义上下文
        context_parts = []
        for i, result in enumerate(semantic_results):
            candidate = result["candidate"]
            similarity = result["similarity"]
            if similarity > 0.5:  # 只使用相似度较高的结果
                context_parts.append(f"相关任务{i+1}: {candidate['task']} - {candidate['text']} (相似度: {similarity:.2f})")
        
        if context_parts:
            semantic_context = "\n".join(context_parts)
            enhanced_query = f"用户问题: {query}\n\n语义相关任务:\n{semantic_context}"
            return enhanced_query
        
        return query
    
    def analyze_query_intent(self, question: str, context: str = "") -> Dict:
        """分析查询意图，决定需要哪些Agent参与"""
        try:
            intent_prompt = PromptTemplate.from_template("""
分析用户问题的意图，决定需要哪些专业Agent来回答：

用户问题：{question}
对话上下文：{context}

请分析问题类型，并返回JSON格式的决策：
{{
    "requires_database": true/false,  // 是否需要数据库查询获取数据
    "requires_pdf": true/false,       // 是否需要PDF检索
    "requires_knowledge_base": true/false,  // 是否需要知识库检索
    "requires_drawing": true/false, // 是否需要调用绘图Agent
    "primary_agent": "database/pdf/knowledge_base/drawing/multi",  // 主要Agent
    "reasoning": "分析理由"
}}

- 如果问题是关于"画图"、"绘制图表"、"可视化"、"图表"、"柱状图"、"折线图"、"饼图"等，请设置 "requires_drawing": true 并且 "primary_agent": "drawing"。
- 如果绘图需要查询数据库中的数据（如"画出每个仓库的库存量"），请同时设置 "requires_database": true。
- 其他情况照常分析。

只返回JSON，不要其他内容。
""")
            
            response = self.llm.invoke(intent_prompt.format(
                question=question,
                context=context
            ))
            
            # 解析JSON响应
            intent_data = json.loads(response.content.strip())
            return intent_data
            
        except Exception as e:
            # 检查是否包含画图关键词
            drawing_keywords = ["画图", "绘制", "图表", "可视化", "柱状图", "折线图", "饼图", "plot", "draw", "chart"]
            if any(keyword in question for keyword in drawing_keywords):
                return {
                    "requires_database": True,
                    "requires_pdf": False,
                    "requires_knowledge_base": False,
                    "requires_drawing": True,
                    "primary_agent": "drawing",
                    "reasoning": "关键词触发绘图模式"
                }
            # 默认返回多Agent模式
            return {
                "requires_database": True,
                "requires_pdf": True,
                "requires_knowledge_base": True,
                "requires_drawing": False,
                "primary_agent": "multi",
                "reasoning": "默认多Agent模式"
            }
    
    def coordinate_agents(self, question: str, context: str = "") -> Dict:
        """协调各个Agent，获取综合回答"""
        # 检查是否是画图需求
        drawing_keywords = ["画图", "绘制", "图表", "可视化", "柱状图", "折线图", "饼图", "plot", "draw", "chart"]
        if any(keyword in question for keyword in drawing_keywords):
            print("🎨 检测到画图需求，启动绘图流程...")
            db_data_context = ""
            data_summary = ""
            
            # 智能判断是否需要数据库数据
            # 1. 明确包含数据库相关关键词
            db_related_keywords = ["仓库", "库存", "销售", "产品", "门店", "补货", "warehouse", "inventory", "sales", "product", "store"]
            is_db_related = any(keyword in question for keyword in db_related_keywords)
            
            # 2. 检查是否是通用画图需求（如历史、地理等）
            general_keywords = ["历史", "朝代", "国家", "地理", "人口", "经济", "历史", "dynasty", "country", "geography", "population", "economy"]
            is_general = any(keyword in question for keyword in general_keywords)
            
            if is_db_related and not is_general:
                # 静默获取数据库数据，不显示技术细节
                try:
                    sql = self.db_agent.generate_sql(question)
                    if sql:
                        plot_data = self.db_agent.get_data_for_plotting(sql)
                        if plot_data and len(plot_data) > 0:
                            db_data_context = json.dumps(plot_data, ensure_ascii=False, indent=2)
                            # 生成数据摘要
                            data_summary = self._generate_data_summary_for_plot(plot_data, question)
                            print(f"✅ 成功获取数据库数据用于绘图，共{len(plot_data)}条记录")
                        else:
                            print("📊 数据库无相关数据，将使用示例数据")
                    else:
                        print("📊 无法生成数据库查询，将使用示例数据")
                except Exception as e:
                    print(f"📊 数据库查询异常，将使用示例数据: {str(e)}")
            else:
                print("📊 检测到通用画图需求，将使用示例数据...")
            
            # 调用绘图Agent
            plot_result = self.drawing_agent.draw(question, db_data_context)
            
            # 构建用户友好的回答
            if "成功" in plot_result:
                if data_summary:
                    user_answer = f"🎨 已根据数据库信息生成图表\n\n{data_summary}\n\n{plot_result}"
                else:
                    user_answer = f"🎨 已生成图表\n\n{plot_result}"
            else:
                user_answer = f"❌ 图表生成失败: {plot_result}"
            
            return {
                "answer": user_answer,
                "knowledge_context": "",
                "db_result": data_summary if data_summary else "使用示例数据",
                "pdf_result": "",
                "source_type": "drawing_agent",
                "confidence": 0.95,
                "agent_decision": {
                    "primary_agent": "drawing",
                    "reasoning": "用户输入包含画图关键词，直接触发绘图模式",
                    "requires_database": is_db_related and not is_general,
                    "requires_pdf": False,
                    "requires_knowledge_base": False,
                    "requires_drawing": True
                },
                "semantic_results": [],
                "plot_path": plot_result if "成功" in plot_result else None
            }
        
        # 1. 语义检索增强
        enhanced_question = self._enhance_query_with_semantic_context(question)
        semantic_results = self._knn_semantic_search(question, k=3)
        
        # 检查最高相关性
        max_similarity = max([r['similarity'] for r in semantic_results], default=0)
        
        # 2. 分析查询意图
        try:
            intent = self.analyze_query_intent(enhanced_question, context)
        except Exception as e:
            print(f"⚠️ 意图分析失败: {e}")
            intent = None
        
        # 如果意图分析失败，使用默认策略
        if not intent or not isinstance(intent, dict) or not intent.get('primary_agent'):
            intent = {
                "requires_database": True,
                "requires_pdf": True,
                "requires_knowledge_base": True,
                "requires_drawing": False,
                "primary_agent": "multi",
                "reasoning": "默认多Agent协调模式"
            }
        
        # 3. 优先执行数据库查询
        results = {}
        db_result = ""
        
        # 数据库查询（优先执行）
        if intent.get("requires_database", True):
            try:
                print("🔍 优先执行数据库查询...")
                # 直接执行数据库查询
                db_result = self.db_agent.query(question, context)
                
                # 检查数据库查询是否成功返回具体数据
                if db_result and "未找到相关数据" not in db_result and "无法理解查询需求" not in db_result:
                    results["db_result"] = db_result
                    print("✅ 数据库查询成功，返回具体数据")
                else:
                    print("⚠️ 数据库查询未返回具体数据")
                    results["db_result"] = "数据库查询未返回具体数据"
                    
                # 获取数据库摘要信息
                try:
                    db_summary = self.db_agent.get_database_summary()
                    results["db_summary"] = db_summary
                except Exception:
                    pass
                    
            except Exception as e:
                print(f"❌ 数据库查询失败: {e}")
                results["db_result"] = f"数据库查询失败: {e}"
        
        # 4. 如果数据库查询成功返回具体数据，直接基于数据生成回答
        if results.get("db_result") and "未找到相关数据" not in results["db_result"] and "无法理解查询需求" not in results["db_result"]:
            print("🎯 基于数据库具体数据生成回答...")
            
            # 知识库查询（作为补充）
            if intent.get("requires_knowledge_base", True):
                try:
                    if hasattr(self.kb, 'query_with_database_context'):
                        results["knowledge_context"] = self.kb.query_with_database_context(question)
                    else:
                        docs = self.kb.vectorstore.similarity_search(question, k=3)
                        results["knowledge_context"] = self._format_knowledge_context(docs)
                except Exception as e:
                    results["knowledge_context"] = f"知识库检索失败: {e}"
            
            # PDF查询（作为补充）
            if intent.get("requires_pdf", True):
                try:
                    results["pdf_result"] = self.pdf_agent.query(question)
                except Exception as e:
                    results["pdf_result"] = f"PDF检索失败: {e}"
            
            # 基于数据库具体数据生成智能回答
            final_answer = self._generate_data_driven_answer(question, results, intent, semantic_results)
            
            return {
                "answer": final_answer,
                "knowledge_context": results.get("knowledge_context", ""),
                "db_result": results.get("db_result", ""),
                "pdf_result": results.get("pdf_result", ""),
                "db_summary": results.get("db_summary", ""),
                "source_type": "database_driven",
                "confidence": min(0.95, 0.8 + max_similarity * 0.15),
                "agent_decision": intent,
                "semantic_results": semantic_results
            }
        
        # 5. 如果数据库查询失败，使用传统多Agent模式
        print("🔄 使用传统多Agent协调模式...")
        
        # 知识库查询
        if intent.get("requires_knowledge_base", True):
            try:
                if hasattr(self.kb, 'query_with_database_context'):
                    results["knowledge_context"] = self.kb.query_with_database_context(question)
                else:
                    docs = self.kb.vectorstore.similarity_search(question, k=5)
                    results["knowledge_context"] = self._format_knowledge_context(docs)
            except Exception as e:
                results["knowledge_context"] = f"知识库检索失败: {e}"
        
        # PDF查询
        if intent.get("requires_pdf", True):
            try:
                results["pdf_result"] = self.pdf_agent.query(question)
            except Exception as e:
                results["pdf_result"] = f"PDF检索失败: {e}"
        
        # 智能结果整合
        final_answer = self._generate_intelligent_answer(question, results, intent, semantic_results)
        
        return {
            "answer": final_answer,
            "knowledge_context": results.get("knowledge_context", ""),
            "db_result": results.get("db_result", ""),
            "pdf_result": results.get("pdf_result", ""),
            "db_summary": results.get("db_summary", ""),
            "source_type": "top_agent_coordinated",
            "confidence": min(0.9, 0.7 + max_similarity * 0.2),
            "agent_decision": intent,
            "semantic_results": semantic_results
        }
    
    def _generate_data_driven_answer(self, question: str, results: Dict, intent: Dict, semantic_results: List) -> str:
        """基于数据库具体数据生成回答"""
        try:
            # 构建数据驱动的回答
            data_prompt = PromptTemplate.from_template("""
作为智能仓储系统的数据分析专家，请基于以下数据库具体数据，为用户问题提供直接、准确、数据驱动的回答：

用户问题：{question}

【数据库具体数据】
{db_result}

【知识库补充信息】
{knowledge_context}

【PDF补充信息】
{pdf_result}

请提供：
1. 直接回答用户问题，基于数据库具体数据
2. 数据分析和业务洞察
3. 具体的数值和统计信息
4. 基于数据的建议

要求：
- 回答要基于数据库的具体数据，不要给出SQL建议
- 突出关键数据和统计信息
- 提供数据驱动的业务洞察
- 回答要简洁、专业、准确

基于数据的回答：
""")
            
            response = self.llm.invoke(data_prompt.format(
                question=question,
                db_result=results.get("db_result", "无数据库数据"),
                knowledge_context=results.get("knowledge_context", "无知识库信息"),
                pdf_result=results.get("pdf_result", "无PDF信息")
            ))
            
            return response.content.strip()
            
        except Exception as e:
            return f"数据驱动回答生成失败: {str(e)}"
    
    def _format_knowledge_context(self, docs: List[Document]) -> str:
        """格式化知识库上下文，解决多行隔断问题"""
        if not docs:
            return ""
        
        formatted_contexts = []
        for i, doc in enumerate(docs[:3]):  # 只取前3个最相关的
            content = doc.page_content.strip()
            # 清理和格式化文本
            content = re.sub(r'\n+', ' ', content)  # 将多个换行符替换为空格
            content = re.sub(r'\s+', ' ', content)  # 将多个空格替换为单个空格
            content = content[:300] + "..." if len(content) > 300 else content
            formatted_contexts.append(f"知识片段{i+1}: {content}")
        
        return "\n".join(formatted_contexts)
    
    def _generate_data_summary_for_plot(self, plot_data: List[Dict], question: str) -> str:
        """为绘图生成数据摘要"""
        try:
            if not plot_data:
                return ""
            
            # 分析数据结构
            sample_record = plot_data[0]
            columns = list(sample_record.keys())
            
            # 生成摘要
            summary_parts = []
            summary_parts.append(f"📊 数据概览：基于 {len(plot_data)} 条记录")
            
            # 识别关键字段
            numeric_fields = []
            categorical_fields = []
            
            for field in columns:
                if field in ['quantity', 'total_amount', 'unit_price', 'cost_price', 'stock_quantity', 'safety_stock']:
                    numeric_fields.append(field)
                elif field in ['product_name', 'category', 'warehouse_name', 'store_name']:
                    categorical_fields.append(field)
            
            # 添加数值字段统计
            if numeric_fields:
                for field in numeric_fields[:3]:  # 最多显示3个数值字段
                    try:
                        values = [float(record[field]) for record in plot_data if record[field] is not None]
                        if values:
                            total = sum(values)
                            avg = total / len(values)
                            summary_parts.append(f"• {field}: 总计 {total:,.2f}, 平均 {avg:.2f}")
                    except:
                        continue
            
            # 添加分类字段统计
            if categorical_fields:
                for field in categorical_fields[:2]:  # 最多显示2个分类字段
                    try:
                        unique_values = set(record[field] for record in plot_data if record[field] is not None)
                        if unique_values:
                            summary_parts.append(f"• {field}: {len(unique_values)} 个不同值")
                    except:
                        continue
            
            return "\n".join(summary_parts)
            
        except Exception as e:
            return f"数据摘要生成失败: {str(e)}"

    def _generate_intelligent_answer(self, question: str, results: Dict, intent: Dict, semantic_results: List) -> str:
        """智能生成综合回答"""
        try:
            # 构建上下文信息
            context_parts = []
            
            # 添加语义相关任务信息
            if semantic_results:
                relevant_tasks = []
                for result in semantic_results[:2]:  # 取前2个最相关的
                    if result['similarity'] > 0.4:
                        candidate = result['candidate']
                        relevant_tasks.append(f"{candidate['task']}: {candidate['text']}")
                
                if relevant_tasks:
                    context_parts.append(f"相关任务: {'; '.join(relevant_tasks)}")
            
            # 添加数据库摘要
            if results.get("db_summary"):
                context_parts.append(f"数据库状态: {results['db_summary']}")
            
            # 构建综合提示
            synthesis_prompt = PromptTemplate.from_template("""
作为智能仓储系统的中枢大脑，请基于以下多源信息生成专业、结构化的综合回答：

用户问题：{question}
Agent决策：{intent_reasoning}
上下文信息：{context_info}

【知识库信息】
{knowledge_context}

【数据库分析】
{db_result}

【PDF检索结果】
{pdf_result}

请提供：
1. 直接回答用户问题
2. 基于多源信息的综合分析
3. 数据驱动的业务洞察
4. 具体的建议和优化方向
5. 如果有上下文关联，请体现连续性

要求：
- 回答要简洁、专业、结构化
- 充分利用数据库的具体数据
- 结合知识库的理论指导
- 体现智能分析能力

综合回答：
""")
            
            context_info = "\n".join(context_parts) if context_parts else "无特殊上下文"
            
            response = self.llm.invoke(synthesis_prompt.format(
                question=question,
                intent_reasoning=intent.get("reasoning", ""),
                context_info=context_info,
                knowledge_context=results.get("knowledge_context", "无相关信息"),
                db_result=results.get("db_result", "无数据库结果"),
                pdf_result=results.get("pdf_result", "无PDF结果")
            ))
            
            return response.content.strip()
            
        except Exception as e:
            return f"智能回答生成失败: {str(e)}"

class AgenticRAGSystem:
    def __init__(self):
        # 1. 初始化知识库
        self.kb = InMemoryKnowledgeBase()
        
        # 2. 初始化数据库Agent
        self.db_agent = UniversalDatabaseAgent()
        
        # 3. 设置知识库的数据库Agent引用
        self.kb.set_db_agent(self.db_agent)
        
        # 4. 加载数据到知识库
        self.kb.load_from_postgres()
        self.kb.load_from_pdfs()
        self.kb.build_vectorstore()
        
        # 5. 初始化其他Agent
        self.pdf_agent = PDFMultiAgent(self.kb)
        self.memory_agent = MemoryAgent()
        self.drawing_agent = DrawingAgent()  # 添加绘图Agent
        self.top_agent = TopAgent(self.memory_agent, self.db_agent, self.pdf_agent, self.kb, self.drawing_agent)
        
        # 6. 初始化LLM
        self.llm = ChatOpenAI(
            model_name=os.getenv("MODEL_NAME"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_api_base=os.getenv("OPENAI_API_URL"),
            temperature=0.3
        )
        
        print("✅ 智能多Agent RAG系统初始化完成")
        print(f"📊 数据库连接: {PG_HOST}:{PG_PORT}/{PG_NAME}")
        print(f"📚 知识库文档数: {len(self.kb.documents)}")
        print(f"🧠 语义检索候选数: {len(self.top_agent.candidate_vectors) if self.top_agent.candidate_vectors else 0}")

    def process_query(self, query: str) -> Dict:
        # 1. 获取上下文
        context = self.memory_agent.get_context_for_query(query)
        
        # 2. TopAgent协调各个Agent
        result = self.top_agent.coordinate_agents(query, context)
        
        # 3. 更新记忆
        self.memory_agent.add_interaction(query, result["answer"], context)
        
        return result

    def close(self):
        self.kb.cleanup()
        self.db_agent.close()
        self.memory_agent.clear_memory()
        print("🧹 系统资源已清理")

# FastAPI接口
app = FastAPI(title="智能多Agent RAG API")
class QueryRequest(BaseModel):
    question: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    global rag
    rag = AgenticRAGSystem()
    yield
    rag.close()

app = FastAPI(lifespan=lifespan)

@app.post("/query")
def query_api(req: QueryRequest):
    try:
        result = rag.process_query(req.question)
        return result
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

def display_result(result: Dict):
    """格式化显示结果（不显示数据库状态、Agent决策分析、信息来源和SQL相关内容）"""
    print("\n" + "="*50)
    print("📝 智能结构化回答")
    print("="*50)
    print(result.get('answer', '无回答'))
    
    # 绘图结果特殊处理
    if result.get("source_type") == "drawing_agent":
        if result.get("plot_path"):
            print("✅ 图像已尝试在窗口中显示，并已保存到本地。")
        # 对于画图功能，不显示其他技术细节
        return
    
    # 置信度和相关性
    if 'confidence' in result:
        print(f"\n🎯 置信度: {result['confidence']:.1%}")
    if 'relevance_score' in result:
        print(f"📊 知识库匹配度: {result['relevance_score']:.1%}")
    
    # 语义检索结果
    if 'semantic_results' in result and result['semantic_results']:
        print("\n🔍 语义相似度检索")
        print("-" * 20)
        for i, semantic_result in enumerate(result['semantic_results'][:3]):
            candidate = semantic_result['candidate']
            similarity = semantic_result['similarity']
            if similarity > 0.3:  # 只显示相似度较高的结果
                print(f"相关任务{i+1}: {candidate['task']} - {candidate['text']}")
                print(f"相似度: {similarity:.3f}")
    
    # 详细上下文（可选）
    if 'knowledge_context' in result and result['knowledge_context']:
        print("\n🧠 知识库片段:")
        print(result['knowledge_context'])
    if 'db_result' in result and result['db_result']:
        print("\n💾 数据库分析:")
        print(result['db_result'])
    if 'pdf_result' in result and result['pdf_result']:
        print("\n📄 PDF检索:")
        print(result['pdf_result'])

def main():
    print("🚀 === 智能多Agent RAG仓库管理系统（支持画图功能） ===")
    print("💡 请输入您的查询：")
    print("🎨 支持画图功能：输入包含'画图'、'绘制'、'图表'等关键词的问题")
    print("🔚 输入'退出'、'quit'、'exit'或'q'结束会话")
    print("🧹 输入'clear'清空对话记忆\n")
    
    rag = AgenticRAGSystem()
    try:
        while True:
            query = input("\n🤔 请输入您的查询> ").strip()
            if not query:
                continue
            if query.lower() in ['quit', 'exit', '退出', 'q']:
                print("🧹 正在清空对话记忆...")
                rag.memory_agent.clear_memory()
                print("✅ 对话记忆已清空")
                break
            if query.lower() == 'clear':
                rag.memory_agent.clear_memory()
                print("🧹 对话记忆已清空")
                continue
            
            # 检查是否是画图需求
            drawing_keywords = ["画图", "绘制", "图表", "可视化", "柱状图", "折线图", "饼图", "plot", "draw", "chart"]
            is_drawing_request = any(keyword in query for keyword in drawing_keywords)
            
            if is_drawing_request:
                print("🎨 检测到画图需求，启动绘图流程...")
                # 画图功能静默处理，不显示技术细节
                import sys
                class DummyFile:
                    def write(self, x): 
                        # 只显示画图相关的输出
                        if any(keyword in x for keyword in ["🎨", "📊", "✅", "❌", "绘图", "画图", "图像", "图表"]):
                            sys.__stdout__.write(x)
                old_stdout = sys.stdout
                sys.stdout = DummyFile()
                result = rag.process_query(query)
                sys.stdout = old_stdout
            else:
                # 只在调试模式下显示SQL相关日志
                import os
                if os.getenv('RAG_DEBUG', '0') == '1':
                    result = rag.process_query(query)
                else:
                    # 临时屏蔽SQL相关print
                    import sys
                    class DummyFile:
                        def write(self, x): pass
                    old_stdout = sys.stdout
                    sys.stdout = DummyFile()
                    result = rag.process_query(query)
                    sys.stdout = old_stdout
            
            display_result(result)
    finally:
        rag.close()
        print("\n👋 系统已关闭")

# Flask集成支持
def create_rag_app():
    """创建Flask集成的RAG应用实例"""
    return AgenticRAGSystem()

# 画图功能支持
def is_drawing_request(question: str) -> bool:
    """检查是否是画图请求"""
    drawing_keywords = ["画图", "绘制", "图表", "可视化", "柱状图", "折线图", "饼图", "plot", "draw", "chart"]
    return any(keyword in question for keyword in drawing_keywords)

# 命令行交互
if __name__ == "__main__":
    main()

def process_terminal_input(query: str) -> str:
    """处理一次终端输入，返回终端风格输出（只保留answer部分）"""
    global rag
    if rag is None:
        rag = AgenticRAGSystem()
    if query.lower() in ['quit', 'exit', '退出', 'q']:
        rag.memory_agent.clear_memory()
        return '🧹 正在清空对话记忆...\n✅ 对话记忆已清空\n👋 系统已关闭'
    if query.lower() == 'clear':
        rag.memory_agent.clear_memory()
        return '🧹 对话记忆已清空'
    try:
        result = rag.process_query(query)
        # 只返回终端风格的主回答内容
        return result.get('answer', '无回答')
    except Exception as e:
        return f'❌ 处理失败: {str(e)}'

def process_draw_input(query: str) -> str:
    """专门处理画图请求，结合数据库数据，返回图片路径或错误信息"""
    global rag
    if rag is None:
        rag = AgenticRAGSystem()
    try:
        # 1. 用数据库Agent生成SQL
        sql = rag.db_agent.generate_sql(query)
        plot_data = None
        if sql:
            plot_data = rag.db_agent.get_data_for_plotting(sql)
        db_data_context = ''
        if plot_data and len(plot_data) > 0:
            import json
            db_data_context = json.dumps(plot_data, ensure_ascii=False, indent=2)
        # 2. 只用数据库数据作图
        plot_result = rag.drawing_agent.draw(query, db_data_context)
        if '成功' in plot_result and '文件保存在' in plot_result:
            # 提取图片路径
            import re
            m = re.search(r'文件保存在: (.+)', plot_result)
            if m:
                return m.group(1).strip()
        return plot_result
    except Exception as e:
        return f"❌ 画图失败: {str(e)}"

