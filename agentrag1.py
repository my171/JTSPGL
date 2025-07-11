import os# 如果下载出问题或者没有设置环境变量不要设置HF_ENDPOINT（删除下面三行），从官网下载模型或者使用本地模型文件
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ["HF_HUB_OFFLINE"] = "0"
os.environ["TRANSFORMERS_OFFLINE"] = "0"

os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "sk-FxhjDpv1D62n33JGICef3aVagezAr73GFnoXmSQ4ikMpf9Hb")#其他api密钥直接改这里，如果closeai的欠费了用这个密钥：sk-tgq6Xw43DMpw510JMGFofD8UPoBZTRUSrtoywgnbIdx8Z88X
os.environ["OPENAI_API_URL"] = os.getenv("OPENAI_API_URL", "https://api.openai-proxy.org/v1")
os.environ["MODEL_NAME"] = os.getenv("MODEL_NAME", "gpt-4.1")#使用的是closeai 的(    )模型
#EMBEDDING_MODEL = "./models/paraphrase-multilingual-mpnet-base-v2"  # 下载到本地的嵌入模型路径
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
os.environ["TRANSFORMERS_OFFLINE"] = "0"
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
# PostgreSQL配置（测试数据库）
PG_HOST = os.getenv('PG_HOST', 'yd.frp-era.com')
PG_PORT = os.getenv('PG_PORT', '11103')
PG_NAME = os.getenv('PG_NAME', 'postgres')
PG_USER = os.getenv('PG_USER', 'u3')
PG_PASSWORD = os.getenv('PG_PASSWORD', 'abcd1234')

#PG_HOST = os.getenv('PG_HOST', '192.168.28.135')
#PG_PORT = os.getenv('PG_PORT', '5432')
#PG_NAME = os.getenv('PG_NAME', 'companylink')
#PG_USER = os.getenv('PG_USER', 'myuser')
#PG_PASSWORD = os.getenv('PG_PASSWORD', '123456abc.')

#本地知识库所需要pdf文件路径
PDF_DIR = './knowledge_pdfs'

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
            
            print(f"✅ 数据库模式分析完成：发现 {len(tables)} 个表")
            for table in tables:
                print(f"   📋 {table}: {len(self.schema_info[table])} 个字段")
                
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
    
    def generate_sql(self, question: str) -> Optional[str]:
        """使用LLM生成SQL查询"""
        try:
            schema_summary = self.schema_analyzer.get_schema_summary()
            
            prompt = PromptTemplate.from_template("""
你是一个SQL专家。根据以下数据库模式，为用户问题生成PostgreSQL查询语句。
数据库模式：
{schema_summary}
用户问题：{question}
要求：
1. 只返回SQL语句，不要其他解释
2. 使用LIMIT 10限制结果数量
3. 如果涉及多表，使用适当的JOIN
4. 确保SQL语法正确
5. 如果问题不明确，返回NULL
6. 优先使用聚合函数进行统计分析
SQL查询：
""")
            
            response = self.llm.invoke(prompt.format(
                schema_summary=schema_summary,
                question=question
            ))
            
            sql = response.content.strip()
            if sql.upper().startswith('SELECT') and 'NULL' not in sql.upper():
                return sql
            return None
            
        except Exception as e:
            print(f"❌ SQL生成失败: {e}")
            return None
    
    def execute_query(self, sql: str) -> List[Tuple]:
        """执行SQL查询"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            cursor.close()
            return rows
        except Exception as e:
            print(f"❌ SQL执行失败: {e}")
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
    
    def analyze_results(self, question: str, rows: List[Tuple], sql: str) -> str:
        """深度分析查询结果"""
        if not rows:
            return "未找到相关数据"
        
        try:
            # 获取列名
            column_names = self.get_column_names(sql)
            if not column_names:
                column_names = [f"column_{i}" for i in range(len(rows[0]) if rows else 0)]
            
            # 进行多维度分析
            statistics = self.analyze_data_statistics(rows, column_names)
            trends = self.analyze_data_trends(rows, column_names)
            relationships = self.analyze_data_relationships(rows, column_names)
            
            # 格式化分析结果
            analysis_text = f"数据概览：共找到 {len(rows)} 条记录\n\n"
            
            # 统计信息
            if statistics.get('numeric_columns'):
                analysis_text += "📊 数值统计：\n"
                for col, stats in statistics['numeric_columns'].items():
                    analysis_text += f"  {col}: 平均{stats['avg']:.2f}, 范围{stats['min']}-{stats['max']}, 总计{stats['sum']:.2f}\n"
            
            if statistics.get('categorical_columns'):
                analysis_text += "\n📋 分类统计：\n"
                for col, stats in statistics['categorical_columns'].items():
                    analysis_text += f"  {col}: {stats['unique_count']}个不同值\n"
                    if stats['top_values']:
                        top_val = stats['top_values'][0]
                        analysis_text += f"    最常见: {top_val[0]} ({top_val[1]}次)\n"
            
            # 趋势信息
            if trends:
                analysis_text += "\n📈 趋势分析：\n"
                for trend_name, trend_info in trends.items():
                    if 'trend' in trend_name:
                        analysis_text += f"  {trend_name}: {trend_info['direction']}趋势, 变化范围{trend_info['range']}\n"
            
            # 关联信息
            if relationships:
                analysis_text += "\n🔗 关联关系：\n"
                for rel_name, rel_info in relationships.items():
                    if rel_info['type'] == 'foreign_key':
                        analysis_text += f"  {rel_name} → {rel_info['references']}\n"
            
            # 使用LLM进行业务洞察
            insight_prompt = PromptTemplate.from_template("""
基于以下数据分析结果，为用户问题提供专业的业务洞察和建议：

用户问题：{question}
执行的SQL：{sql}
数据概览：{analysis_text}

请提供：
1. 关键业务指标解读
2. 数据异常或趋势分析
3. 业务建议和优化方向
4. 风险提示（如果适用）

回答要简洁专业，不超过300字。
""")
            
            response = self.llm.invoke(insight_prompt.format(
                question=question,
                sql=sql,
                analysis_text=analysis_text
            ))
            
            return f"{analysis_text}\n\n💡 业务洞察：\n{response.content.strip()}"
            
        except Exception as e:
            return f"数据分析失败: {str(e)}"
    
    def query(self, question: str, context: str = "") -> str:
        """通用数据库查询接口"""
        try:
            # 1. 生成SQL
            sql = self.generate_sql(question)
            if not sql:
                return "无法理解查询需求，请提供更具体的问题"
            
            # 2. 执行查询
            rows = self.execute_query(sql)
            
            # 3. 深度分析结果
            analysis = self.analyze_results(question, rows, sql)
            
            return analysis
            
        except Exception as e:
            return f"数据库查询失败: {str(e)}"
    
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

class TopAgent:
    """TopAgent - 作为中枢大脑，负责理解、分析和Agent协调"""
    def __init__(self, memory_agent: MemoryAgent, db_agent, pdf_agent, kb):
        self.memory_agent = memory_agent
        self.db_agent = db_agent
        self.pdf_agent = pdf_agent
        self.kb = kb
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
    "requires_database": true/false,  // 是否需要数据库查询
    "requires_pdf": true/false,       // 是否需要PDF检索
    "requires_knowledge_base": true/false,  // 是否需要知识库检索
    "primary_agent": "database/pdf/knowledge_base/multi",  // 主要Agent
    "reasoning": "分析理由"
}}

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
            #(f"⚠️ 意图分析失败: {e}")
            # 默认返回多Agent模式
            return {
                "requires_database": True,
                "requires_pdf": True,
                "requires_knowledge_base": True,
                "primary_agent": "multi",
                "reasoning": "默认多Agent模式"
            }
    
    def coordinate_agents(self, question: str, context: str = "") -> Dict:
        """协调各个Agent，获取综合回答"""
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
                "primary_agent": "multi",
                "reasoning": "默认多Agent协调模式"
            }
        
        # 3. 根据意图和相关性决定策略
        if max_similarity < 0.2:
            # 相关性很低，直接由大模型回答
            llm_prompt = PromptTemplate.from_template("""
你是智能仓储系统的专家，请直接、专业地回答下列用户问题：

用户问题：{question}

请用结构化、简明的方式作答。
""")
            answer = self.llm.invoke(llm_prompt.format(question=question)).content.strip()
            return {
                "answer": answer,
                "knowledge_context": "",
                "db_result": "",
                "pdf_result": "",
                "source_type": "llm_fallback",
                "confidence": 0.6,
                "agent_decision": {
                    "primary_agent": "llm_fallback",
                    "reasoning": "语义相关性低，直接由大模型回答",
                    "requires_database": False,
                    "requires_pdf": False,
                    "requires_knowledge_base": False
                },
                "semantic_results": semantic_results
            }
        
        # 4. 根据意图调用相应Agent
        results = {}
        
        # 知识库查询（增强版）
        if intent.get("requires_knowledge_base", True):
            try:
                # 使用增强的知识库查询，包含数据库上下文
                if hasattr(self.kb, 'query_with_database_context'):
                    results["knowledge_context"] = self.kb.query_with_database_context(question)
                else:
                    # 回退到传统知识库查询
                    docs = self.kb.vectorstore.similarity_search(question, k=5)
                    results["knowledge_context"] = self._format_knowledge_context(docs)
            except Exception as e:
                results["knowledge_context"] = f"知识库检索失败: {e}"
        
        # 数据库查询（增强版）
        if intent.get("requires_database", True):
            try:
                # 使用增强的数据库Agent进行深度分析
                results["db_result"] = self.db_agent.query(question, context)
                
                # 如果数据库查询成功，获取数据库摘要信息
                if "未找到相关数据" not in results["db_result"]:
                    try:
                        db_summary = self.db_agent.get_database_summary()
                        results["db_summary"] = db_summary
                    except Exception:
                        pass
            except Exception as e:
                results["db_result"] = f"数据库查询失败: {e}"
        
        # PDF查询
        if intent.get("requires_pdf", True):
            try:
                results["pdf_result"] = self.pdf_agent.query(question)
            except Exception as e:
                results["pdf_result"] = f"PDF检索失败: {e}"
        
        # 5. 智能结果整合
        final_answer = self._generate_intelligent_answer(question, results, intent, semantic_results)
        
        return {
            "answer": final_answer,
            "knowledge_context": results.get("knowledge_context", ""),
            "db_result": results.get("db_result", ""),
            "pdf_result": results.get("pdf_result", ""),
            "db_summary": results.get("db_summary", ""),
            "source_type": "top_agent_coordinated",
            "confidence": min(0.9, 0.7 + max_similarity * 0.2),  # 基于相似度调整置信度
            "agent_decision": intent,
            "semantic_results": semantic_results
        }
    
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
        self.top_agent = TopAgent(self.memory_agent, self.db_agent, self.pdf_agent, self.kb)
        
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
    """格式化显示结果"""
    print("\n" + "="*50)
    print("📝 智能结构化回答")
    print("="*50)
    print(result.get('answer', '无回答'))
    
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
    
    # Agent决策信息
    if 'agent_decision' in result:
        print("\n🤖 Agent决策分析")
        print("-" * 20)
        decision = result['agent_decision']
        print(f"主要Agent: {decision.get('primary_agent', 'unknown')}")
        print(f"分析理由: {decision.get('reasoning', '无')}")
        print(f"数据库查询: {'✅' if decision.get('requires_database') else '❌'}")
        print(f"PDF检索: {'✅' if decision.get('requires_pdf') else '❌'}")
        print(f"知识库检索: {'✅' if decision.get('requires_knowledge_base') else '❌'}")
    
    # 信息来源
    print("\n📋 信息来源")
    print("-" * 20)
    source_type = result.get('source_type', 'unknown')
    if source_type == "top_agent_coordinated":
        print("🧠 TopAgent协调系统")
    elif source_type == "knowledge_base":
        print("✅ 知识库直接匹配")
    elif source_type == "agent_system":
        print("🤖 多Agent协调系统")
    elif source_type == "llm_fallback":
        print("⚠️ LLM直接生成")
    elif source_type == "duplicate":
        print("🔄 重复查询检测")
    else:
        print("❓ 未知来源")
    
    # 数据库摘要信息
    if 'db_summary' in result and result['db_summary']:
        print("\n💾 数据库状态:")
        print(result['db_summary'])
    
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
    print("🚀 === 智能多Agent RAG仓库管理系统（通用PostgreSQL版） ===")
    print("💡 请输入您的查询：")
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
            result = rag.process_query(query)
            display_result(result)
    finally:
        rag.close()
        print("\n👋 系统已关闭")

# 命令行交互
if __name__ == "__main__":
    main()
