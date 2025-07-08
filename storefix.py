from dotenv import load_dotenv
load_dotenv()  # 这行需要放在所有代码之前
import os
# 配置环境变量
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ["HF_HUB_OFFLINE"] = "0"
os.environ["TRANSFORMERS_OFFLINE"] = "0"
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "sk-FxhjDpv1D62n33JGICef3aVagezAr73GFnoXmSQ4ikMpf9Hb")
os.environ["OPENAI_API_URL"] = os.getenv("OPENAI_API_URL", "https://api.openai-proxy.org/v1")
os.environ["MODEL_NAME"] = os.getenv("MODEL_NAME", "deepseek-chat")
os.environ["DB_PATH"] = os.getenv("DB_PATH", "store.db")
import sqlite3
import json
import hashlib
import fitz  # PyMuPDF
import numpy as np
import faiss
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from sentence_transformers import SentenceTransformer
from langchain_openai import ChatOpenAI

class Config:
    """系统配置类"""
    def __init__(self, db_path: Optional[str] = None):
        # 嵌入模型配置
        self.embedding_model = "paraphrase-multilingual-MiniLM-L12-v2"
        # LLM配置
        self.llm_model = os.getenv("MODEL_NAME")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_base_url = os.getenv("OPENAI_API_URL")
        
        # 数据库配置 (新增)
        self.warehouse_db_path = db_path or os.getenv("DB_PATH")
        
        # 知识库配置
        self.pdf_knowledge_dir = "./knowledge_pdfs"
        self.index_dim = 384  # 嵌入模型维度
        
        # 检索配置
        self.top_k = 3
        self.rag_threshold = 0.8  # 提高到80%匹配度
        self.cache_expiry = 86400  # 24小时

class DatabaseImporter:
    """数据库导入器，用于查询导入的数据库"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._verify_database()
    
    def _verify_database(self):
        """验证数据库文件是否有效"""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"数据库文件不存在: {self.db_path}")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            if not tables:
                raise ValueError("数据库中没有表")
            conn.close()
        except sqlite3.Error as e:
            raise ValueError(f"无效的数据库文件: {str(e)}")
    
    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """执行查询并返回格式化结果"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"数据库查询错误: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def get_table_info(self) -> Dict:
        """获取数据库表结构信息"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取所有表名
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            
            # 获取每个表的结构
            table_info = {}
            for table in tables:
                cursor.execute(f"PRAGMA table_info({table});")
                columns = [{"name": row[1], "type": row[2]} for row in cursor.fetchall()]
                table_info[table] = columns
            
            return table_info
        except sqlite3.Error as e:
            print(f"获取表结构失败: {e}")
            return {}
        finally:
            if conn:
                conn.close()

class PDFKnowledgeExtractor:
    """PDF知识提取器"""
    def __init__(self, config: Config):
        self.config = config
        self.embedder = SentenceTransformer(config.embedding_model)
    
    def extract_text(self, pdf_path: str) -> List[Dict]:
        """提取PDF文本内容"""
        doc = fitz.open(pdf_path)
        chunks = []
        for page in doc:
            text = page.get_text()
            if text.strip():
                chunks.append({
                    "content": text,
                    "metadata": {
                        "source": os.path.basename(pdf_path),
                        "page": page.number + 1
                    }
                })
        return chunks
    
    def process_pdf_directory(self) -> List[Dict]:
        """处理PDF目录中的所有文件"""
        if not os.path.exists(self.config.pdf_knowledge_dir):
            os.makedirs(self.config.pdf_knowledge_dir)
            return []
        
        all_chunks = []
        for filename in os.listdir(self.config.pdf_knowledge_dir):
            if filename.endswith(".pdf"):
                pdf_path = os.path.join(self.config.pdf_knowledge_dir, filename)
                chunks = self.extract_text(pdf_path)
                all_chunks.extend(chunks)
        return all_chunks

class KnowledgeBase:
    """知识库管理类"""
    def __init__(self, config: Config):
        self.config = config
        self.embedder = SentenceTransformer(config.embedding_model)
        self.vector_index = self._init_vector_index()
        self.local_db = self._init_local_db()
        self.llm = ChatOpenAI(
            model_name=self.config.llm_model,
            openai_api_key=self.config.openai_api_key,
            openai_api_base=self.config.openai_base_url,
            temperature=0.3
        )
        self.pdf_extractor = PDFKnowledgeExtractor(config)
        self._init_pdf_knowledge()
        self._initialize_base_knowledge()
    
    def _init_vector_index(self):
        """初始化FAISS向量索引"""
        try:
            index = faiss.read_index("vector_db.index")
            print("加载已有向量索引")
        except:
            index = faiss.IndexFlatIP(self.config.index_dim)
            print("创建新向量索引")
        return index
    
    def _init_local_db(self):
        """初始化SQLite知识库"""
        conn = sqlite3.connect("knowledge.db")
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            metadata TEXT,
            embedding BLOB,
            source TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            hash TEXT UNIQUE
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS search_cache (
            query_hash TEXT PRIMARY KEY,
            results TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        conn.commit()
        return conn
    
    def _init_pdf_knowledge(self):
        """初始化PDF知识"""
        pdf_chunks = self.pdf_extractor.process_pdf_directory()
        for chunk in pdf_chunks:
            self.add_knowledge(
                content=chunk["content"],
                metadata=chunk["metadata"],
                source="pdf"
            )
    
    def _initialize_base_knowledge(self):
        """初始化基础仓库知识"""
        base_knowledge = [
            {
                "content": "仓库管理最佳实践包括定期盘点库存、优化存储布局和建立安全协议。",
                "metadata": {"source": "仓库管理手册"},
                "source": "manual"
            },
            {
                "content": "库存周转率是衡量仓库效率的重要指标，计算公式为:销售成本/平均库存。",
                "metadata": {"source": "供应链管理指南"},
                "source": "guide"
            }
        ]
        
        for knowledge in base_knowledge:
            self.add_knowledge(**knowledge)
    
    def add_knowledge(self, content: str, metadata: dict = None, source: str = "local") -> bool:
        """添加知识条目"""
        content_hash = hashlib.md5(content.encode()).hexdigest()
        cursor = self.local_db.cursor()
        
        try:
            cursor.execute("SELECT 1 FROM knowledge WHERE hash=?", (content_hash,))
            if cursor.fetchone():
                return False
            
            embedding = self.embedder.encode(content)
            embedding_bytes = embedding.tobytes()
            
            cursor.execute('''
            INSERT INTO knowledge (content, metadata, embedding, source, hash)
            VALUES (?, ?, ?, ?, ?)
            ''', (content, json.dumps(metadata) if metadata else None, 
                 embedding_bytes, source, content_hash))
            
            embedding = embedding.reshape(1, -1).astype('float32')
            faiss.normalize_L2(embedding)
            self.vector_index.add(embedding)
            
            self.local_db.commit()
            return True
        except Exception as e:
            self.local_db.rollback()
            print(f"添加知识失败: {e}")
            return False
    
    def search_local(self, query: str) -> List[Dict]:
        """本地知识检索"""
        query_embedding = self.embedder.encode(query)
        query_embedding = query_embedding.reshape(1, -1).astype('float32')
        faiss.normalize_L2(query_embedding)
        
        distances, indices = self.vector_index.search(query_embedding, self.config.top_k)
        
        cursor = self.local_db.cursor()
        results = []
        for idx, distance in zip(indices[0], distances[0]):
            if idx < 0:
                continue
            
            cursor.execute("SELECT content, metadata, source FROM knowledge WHERE id=?", (idx+1,))
            row = cursor.fetchone()
            if row:
                results.append({
                    "content": row[0],
                    "metadata": json.loads(row[1]) if row[1] else {},
                    "source": row[2],
                    "score": float(distance)
                })
        
        # 按匹配度排序
        results.sort(key=lambda x: x["score"], reverse=True)
        return results
    
    def hybrid_search(self, query: str) -> Tuple[List[Dict], bool]:
        """增强版混合检索策略"""
        # 本地检索
        local_results = self.search_local(query)
        
        # 检查是否有高匹配度结果
        has_high_match = any(res.get("score", 0) >= self.config.rag_threshold for res in local_results)
        
        return local_results, has_high_match
    
    def save_vector_index(self):
        """保存向量索引"""
        faiss.write_index(self.vector_index, "vector_db.index")
        print("向量索引已保存")

class IntentClassifier:
    """增强版意图分类器"""
    def __init__(self, llm):
        self.llm = llm
        self.default_response = {
            "is_db_query": False,
            "query_type": None,
            "target_id": None,
            "operation": "query"  # query/insert/update/delete
        }
    
    def classify(self, query: str) -> Dict:
        """识别查询意图"""
        try:
            # 简化意图识别，只判断是否需要数据库查询
            return {
                "is_db_query": False,
                "query_type": None,
                "target_id": None,
                "operation": "query"
            }
        except Exception as e:
            print(f"意图分类失败: {e}")
            return self.default_response

class WarehouseRAGSystem:
    """完整的智能仓库管理系统"""
    def __init__(self, db_path: Optional[str] = None):
        self.config = Config(db_path)
        self.knowledge_base = KnowledgeBase(self.config)
        self.intent_classifier = IntentClassifier(self.knowledge_base.llm)
        
        # 初始化数据库导入器
        self.db_importer = None
        if db_path and os.path.exists(db_path):
            try:
                self.db_importer = DatabaseImporter(db_path)
                print(f"已加载数据库: {db_path}")
            except Exception as e:
                print(f"加载数据库失败: {str(e)}")
    
    def process_query(self, query: str) -> Dict:
        """处理用户查询"""
        intent = self.intent_classifier.classify(query)
        
        # 如果有数据库且查询需要数据库信息
        if self.db_importer and self._should_use_database(query):
            return self._handle_db_aware_query(query)
        
        # 否则使用知识库查询
        return self._handle_knowledge_query(query)
    
    def _should_use_database(self, query: str) -> bool:
        """判断是否需要使用数据库信息"""
        db_keywords = ["库存", "销售", "供应", "产品", "仓库", "门店", "员工"]
        return any(keyword in query for keyword in db_keywords)
    
    def _handle_knowledge_query(self, query: str) -> Dict:
        """处理知识库查询"""
        try:
            # 使用混合检索策略
            results, has_high_match = self.knowledge_base.hybrid_search(query)
            
            if has_high_match:
                # 使用本地高匹配度结果生成回答
                context = "\n".join([result["content"] for result in results[:3]])
                response = self.knowledge_base.llm.invoke([{
                    "role": "system",
                    "content": f"基于以下本地知识库信息回答用户问题:\n{context}"
                }, {
                    "role": "user",
                    "content": query
                }])
                
                return {
                    "question": query,
                    "answer": response.content,
                    "sources": [result["source"] for result in results],
                    "context": results,
                    "source_type": "local"
                }
            else:
                # 没有高匹配度结果，直接使用LLM回答
                response = self.knowledge_base.llm.invoke([{
                    "role": "user",
                    "content": query
                }])
                
                return {
                    "question": query,
                    "answer": response.content,
                    "sources": [],
                    "source_type": "llm"
                }
        except Exception as e:
            return {
                "question": query,
                "answer": f"查询失败: {str(e)}",
                "sources": []
            }
    
    def _handle_db_aware_query(self, query: str) -> Dict:
        """处理需要结合数据库知识的查询"""
        try:
            # 1. 获取数据库结构
            db_structure = self.db_importer.get_table_info()
            
            # 2. 使用LLM生成SQL查询
            prompt = f"""你是一个SQL专家。根据以下数据库结构和问题，生成可直接执行的SQL查询:

数据库结构:
{json.dumps(db_structure, indent=2, ensure_ascii=False)}

问题: {query}

请返回可直接执行的SQL语句，不要包含任何解释或注释。"""
            
            sql_response = self.knowledge_base.llm.invoke([{
                "role": "system", 
                "content": prompt
            }])
            
            # 3. 执行SQL查询
            sql_query = sql_response.content
            query_results = self.db_importer.execute_query(sql_query)
            
            # 4. 使用LLM解释结果
            explanation_prompt = f"""根据以下SQL查询结果，用自然语言解释:

查询: {sql_query}

结果:
{json.dumps(query_results, indent=2, ensure_ascii=False)}

问题: {query}

请提供清晰、专业的解释:"""
            
            explanation = self.knowledge_base.llm.invoke([{
                "role": "system",
                "content": explanation_prompt
            }])
            
            return {
                "question": query,
                "answer": explanation.content,
                "sources": ["database"],
                "data": query_results,
                "sql_query": sql_query,
                "source_type": "database"
            }
            
        except Exception as e:
            print(f"数据库查询失败: {str(e)}")
            # 失败时回退到知识库查询
            return self._handle_knowledge_query(query)
    
    def close(self):
        """关闭系统"""
        self.knowledge_base.save_vector_index()
        self.knowledge_base.local_db.close()

def display_result(result: Dict):
    """格式化显示结果"""
    print("\n=== 回答 ===")
    print(result['answer'])
    
    if result.get('source_type') == "local":
        print("\n=== 信息来源 ===")
        pdf_names = [item["metadata"]["source"] for item in result.get('context', []) if "metadata" in item and "source" in item["metadata"]]
        for name in set(pdf_names):
            print(f"- PDF文档: {name}")
    elif result.get('source_type') == "database":
        print("\n=== 数据库查询结果 ===")
        if result.get('data'):
            print("\n=== 数据详情 ===")
            if isinstance(result['data'], list) and len(result['data']) > 0:
                sample = result['data'][0]
                if isinstance(sample, dict):
                    # 显示表格形式的字段和值
                    print("\n".join(f"{k}: {v}" for k, v in sample.items()))
            else:
                print(json.dumps(result['data'], indent=2, ensure_ascii=False))
    elif result.get('source_type') == "llm":
        print("\n=== 信息来自大模型生成 ===")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='仓库智能管理系统')
    parser.add_argument('--db', help='数据库文件路径(可选)')
    args = parser.parse_args()
    
    print("=== 仓库智能管理系统 ===")
    print("请输入您的查询：")
    print("输入'退出'或'quit'结束会话\n")
    system = WarehouseRAGSystem(args.db)
    
    try:
        while True:
            query = input("\n请输入您的查询> ").strip()
            if not query:
                continue
            if query.lower() in ['quit', 'exit', '退出']:
                break
            
            result = system.process_query(query)
            display_result(result)
          
    finally:
        system.close()
        print("\n系统已关闭")

if __name__ == "__main__":
    # 检查依赖
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        print("请先安装依赖: pip install langchain-openai pymupdf sentence-transformers faiss-cpu")
        exit(1)
    
    main()
    # 检查依赖
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        print("请先安装依赖: pip install langchain-openai pymupdf sentence-transformers faiss-cpu")
        exit(1)
    
    main()