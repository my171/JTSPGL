'''
    通用数据库Agent - 支持任何PostgreSQL数据库结构
'''

import os
import json
import psycopg2
from typing import List, Dict, Tuple, Optional
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
import textwrap

from config import Config
from API_TextToText.API_of_RAG._8_DatabaseSchemaAnalyzer import DatabaseSchemaAnalyzer

class UniversalDatabaseAgent:
    """通用数据库Agent - 支持任何PostgreSQL数据库结构"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model_name=Config.RAG_MODEL_NAME,
            openai_api_key=Config.RAG_OPENAI_API_KEY,
            openai_api_base=Config.RAG_OPENAI_API_URL,
            temperature=0.3
        )
        self.conn = psycopg2.connect(
            host=Config.DB_HOST, port=Config.DB_PORT, database=Config.DB_NAME, user=Config.DB_USER, password=Config.DB_PASSWORD
        )
        self.schema_analyzer = DatabaseSchemaAnalyzer(self.conn)
    
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
            summary.append(f"数据库连接：{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_NAME}")
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