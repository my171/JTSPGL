'''
    知识库
'''
from typing import List
from langchain.schema import Document
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from config import Config
import psycopg2
import fitz
import re
import os

from API_TextToText.API_of_RAG._8_DatabaseSchemaAnalyzer import DatabaseSchemaAnalyzer

class InMemoryKnowledgeBase:
    def __init__(self):
        self.documents: List[Document] = []
        self.embeddings = HuggingFaceEmbeddings(model_name=Config.RAG_EMBEDDING_MODEL)
        self.vectorstore = None
        self.db_agent = None  # 添加数据库Agent引用

    def set_db_agent(self, db_agent):
        """设置数据库Agent引用"""
        self.db_agent = db_agent

    def load_from_postgres(self):
        """动态加载PostgreSQL数据到知识库"""
        try:
            conn = psycopg2.connect(
                host=Config.DB_HOST, port=Config.DB_PORT, database=Config.DB_NAME, user=Config.DB_USER, password=Config.DB_PASSWORD
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

    def load_from_pdfs(self, pdf_dir=Config.RAG_PDF_DIR):
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