from dotenv import load_dotenv
load_dotenv()
import os
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
import fitz
import numpy as np
import faiss
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from sentence_transformers import SentenceTransformer
from langchain_openai import ChatOpenAI
import re

class Config:
    """系统配置类"""
    def __init__(self):
        self.embedding_model = "paraphrase-multilingual-mpnet-base-v2"
        self.llm_model = os.getenv("MODEL_NAME")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_base_url = os.getenv("OPENAI_API_URL")
        self.pdf_knowledge_dir = "./knowledge_pdfs"
        self.index_dim = 768
        self.top_k = 20
        self.rag_threshold = 0.5
        self.chunk_size = 500
        self.chunk_overlap = 50
        self.cache_expiry = 86400

class TextProcessor:
    @staticmethod
    def chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunks.append(text[start:end])
            if end == len(text):
                break
            start = end - overlap
        return chunks
    
    @staticmethod
    def clean_text(text: str) -> str:
        text = ' '.join(text.split())
        return text.strip()

class PDFKnowledgeExtractor:
    def __init__(self, config: Config):
        self.config = config
        self.embedder = SentenceTransformer(config.embedding_model)
        self.text_processor = TextProcessor()
    
    def extract_text(self, pdf_path: str) -> List[Dict]:
        doc = fitz.open(pdf_path)
        chunks = []
        
        for page in doc:
            text = page.get_text()
            if not text.strip():
                continue
                
            text = self.text_processor.clean_text(text)
            text_chunks = self.text_processor.chunk_text(
                text, 
                self.config.chunk_size, 
                self.config.chunk_overlap
            )
            
            for chunk in text_chunks:
                chunks.append({
                    "content": chunk,
                    "metadata": {
                        "source": os.path.basename(pdf_path),
                        "page": page.number + 1,
                        "chunk_id": hashlib.md5(chunk.encode()).hexdigest()[:8]
                    }
                })
        return chunks
    
    def process_pdf_directory(self) -> List[Dict]:
        if not os.path.exists(self.config.pdf_knowledge_dir):
            os.makedirs(self.config.pdf_knowledge_dir)
            return []
        
        all_chunks = []
        processed_files = set()
        
        if os.path.exists("pdf_processing.log"):
            with open("pdf_processing.log", "r") as f:
                processed_files = set(line.strip() for line in f)
        
        new_files = False
        
        for filename in os.listdir(self.config.pdf_knowledge_dir):
            if filename.endswith(".pdf") and filename not in processed_files:
                pdf_path = os.path.join(self.config.pdf_knowledge_dir, filename)
                try:
                    chunks = self.extract_text(pdf_path)
                    all_chunks.extend(chunks)
                    with open("pdf_processing.log", "a") as f:
                        f.write(f"{filename}\n")
                    new_files = True
                except Exception as e:
                    print(f"处理PDF文件失败: {filename}, 错误: {str(e)}")
        
        if new_files:
            print(f"已处理 {len(all_chunks)} 个新文本块")
        
        return all_chunks

class KnowledgeBase:
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
        try:
            index = faiss.read_index("vector_db.index")
            print("加载已有向量索引")
            return index  # 已经是IDMap2类型，直接返回
        except:
            index = faiss.IndexFlatIP(self.config.index_dim)
            print("创建新向量索引")
            return faiss.IndexIDMap2(index)
    
    def _init_local_db(self):
        """初始化SQLite知识库，处理数据库迁移"""
        conn = sqlite3.connect("knowledge.db")
        cursor = conn.cursor()
        
        # 检查knowledge表是否存在并处理迁移
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='knowledge';")
        if cursor.fetchone():
            # 检查knowledge表列
            cursor.execute("PRAGMA table_info(knowledge);")
            columns = [column[1] for column in cursor.fetchall()]
            if 'vector_id' not in columns:
                try:
                    cursor.execute("ALTER TABLE knowledge ADD COLUMN vector_id INTEGER;")
                    conn.commit()
                except sqlite3.OperationalError as e:
                    print(f"添加vector_id列失败: {e}")
        
        # 检查search_cache表是否存在并处理迁移
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='search_cache';")
        if cursor.fetchone():
            cursor.execute("PRAGMA table_info(search_cache);")
            columns = [column[1] for column in cursor.fetchall()]
            if 'query_text' not in columns:
                try:
                    cursor.execute("ALTER TABLE search_cache ADD COLUMN query_text TEXT;")
                    conn.commit()
                except sqlite3.OperationalError as e:
                    print(f"添加query_text列失败: {e}")
        
        # 创建或更新表结构
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            metadata TEXT,
            embedding BLOB,
            source TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            hash TEXT UNIQUE,
            vector_id INTEGER UNIQUE
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS search_cache (
            query_hash TEXT PRIMARY KEY,
            results TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            query_text TEXT
        )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_knowledge_hash ON knowledge(hash)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_knowledge_vector_id ON knowledge(vector_id)')
        
        conn.commit()
        return conn
    
    def _init_pdf_knowledge(self):
        pdf_chunks = self.pdf_extractor.process_pdf_directory()
        for chunk in pdf_chunks:
            self.add_knowledge(
                content=chunk["content"],
                metadata=chunk["metadata"],
                source="pdf"
            )
    
    def _initialize_base_knowledge(self):
        base_knowledge = [
            {
                "content": "仓库管理最佳实践包括定期盘点库存、优化存储布局和建立安全协议。",
                "metadata": {"source": "仓库管理手册", "type": "best_practice"},
                "source": "manual"
            },
            {
                "content": "库存周转率是衡量仓库效率的重要指标，计算公式为:销售成本/平均库存。",
                "metadata": {"source": "供应链管理指南", "type": "metric"},
                "source": "guide"
            },
            {
                "content": "ABC分类法将库存分为三类:A类(高价值低数量)、B类(中等价值中等数量)、C类(低价值高数量)。",
                "metadata": {"source": "库存管理原理", "type": "methodology"},
                "source": "textbook"
            }
        ]
        
        for knowledge in base_knowledge:
            self.add_knowledge(**knowledge)
    
    def add_knowledge(self, content: str, metadata: dict = None, source: str = "local") -> bool:
        content_hash = hashlib.md5(content.encode()).hexdigest()
        cursor = self.local_db.cursor()
        
        try:
            cursor.execute("SELECT id, vector_id FROM knowledge WHERE hash=?", (content_hash,))
            existing = cursor.fetchone()
            
            if existing:
                return False
            
            embedding = self.embedder.encode(content)
            embedding_bytes = embedding.tobytes()
            
            cursor.execute("SELECT MAX(vector_id) FROM knowledge")
            max_id = cursor.fetchone()[0] or 0
            new_vector_id = max_id + 1
            
            cursor.execute('''
            INSERT INTO knowledge (content, metadata, embedding, source, hash, vector_id)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                content, 
                json.dumps(metadata) if metadata else None, 
                embedding_bytes, 
                source, 
                content_hash,
                new_vector_id
            ))
            
            embedding = embedding.reshape(1, -1).astype('float32')
            faiss.normalize_L2(embedding)
            self.vector_index.add_with_ids(embedding, np.array([new_vector_id]))
            
            self.local_db.commit()
            return True
        except Exception as e:
            self.local_db.rollback()
            print(f"添加知识失败: {e}")
            return False
    
    def search_local(self, query: str, use_cache: bool = True) -> List[Dict]:
        query_hash = hashlib.md5(query.encode()).hexdigest()
        
        if use_cache:
            cache_result = self._check_cache(query_hash)
            if cache_result:
                return cache_result
        
        query_embedding = self.embedder.encode(query)
        query_embedding = query_embedding.reshape(1, -1).astype('float32')
        faiss.normalize_L2(query_embedding)
        
        distances, indices = self.vector_index.search(query_embedding, self.config.top_k)
        
        cursor = self.local_db.cursor()
        results = []
        
        for idx, distance in zip(indices[0], distances[0]):
            if idx == -1:
                continue
            
            cursor.execute("""
                SELECT id, content, metadata, source 
                FROM knowledge 
                WHERE vector_id=?
            """, (int(idx),))
            
            row = cursor.fetchone()
            if row:
                results.append({
                    "id": row[0],
                    "content": row[1],
                    "metadata": json.loads(row[2]) if row[2] else {},
                    "source": row[3],
                    "score": float(distance)
                })
        
        results.sort(key=lambda x: x["score"], reverse=True)
        
        if use_cache and results:
            self._cache_results(query_hash, query, results)
        
        return results
    
    def _check_cache(self, query_hash: str) -> Optional[List[Dict]]:
        cursor = self.local_db.cursor()
        cursor.execute("""
            SELECT results, timestamp 
            FROM search_cache 
            WHERE query_hash=?
        """, (query_hash,))
        
        row = cursor.fetchone()
        if row:
            results_json, timestamp = row
            cache_time = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
            if (datetime.now() - cache_time).total_seconds() < self.config.cache_expiry:
                return json.loads(results_json)
        return None
    
    def _cache_results(self, query_hash: str, query_text: str, results: List[Dict]):
        try:
            cursor = self.local_db.cursor()
            # 检查表是否有query_text列
            cursor.execute("PRAGMA table_info(search_cache);")
            columns = [column[1] for column in cursor.fetchall()]
            has_query_text = 'query_text' in columns
            
            if has_query_text:
                cursor.execute("""
                    INSERT OR REPLACE INTO search_cache (query_hash, results, query_text, timestamp)
                    VALUES (?, ?, ?, datetime('now'))
                """, (query_hash, json.dumps(results), query_text))
            else:
                cursor.execute("""
                    INSERT OR REPLACE INTO search_cache (query_hash, results, timestamp)
                    VALUES (?, ?, datetime('now'))
                """, (query_hash, json.dumps(results)))
            
            self.local_db.commit()
        except Exception as e:
            print(f"缓存失败: {e}")
    
    def hybrid_search(self, query: str) -> Tuple[List[Dict], bool]:
        local_results = self.search_local(query)
        has_high_match = any(res.get("score", 0) >= self.config.rag_threshold for res in local_results)
        return local_results, has_high_match
    
    def generate_response(self, query: str, context: List[Dict] = None) -> str:
        # 多轮迭代RAG召回
        filtered_context = iterative_rag_search(self, query)
        # 构建更明确的提示模板
        context_str = "\n\n".join([
            f"来源: {res['metadata'].get('source', res['source'])}\n内容: {res['content']}\n相关度: {res['score']:.2f}"
            for res in filtered_context
        ])
        messages = [{
            "role": "system",
            "content": f"""你是一个专业的仓库知识助手。请根据以下上下文信息回答问题。注意：
1. 必须严格基于提供的上下文信息回答
2. 如果上下文中有直接相关的内容，必须优先使用
3. 保持回答专业、准确、简洁
4. 如有相关明细请直接列举，没有则说明无数据

上下文信息:
{context_str}

问题: {query}

请直接回答问题，不要添加无关信息。"""
        }, {
            "role": "user",
            "content": query
        }]
        response = self.llm.invoke(messages)
        return response.content
    
    def save_vector_index(self):
        faiss.write_index(self.vector_index, "vector_db.index")
        print("向量索引已保存")

def filter_context_by_keywords(context, query, min_count=3):
    # 简单分词，提取长度大于1的词
    keywords = [w for w in query.replace('，', ' ').replace('。', ' ').split() if len(w) > 1]
    filtered = [c for c in context if any(k in c['content'] for k in keywords)]
    if len(filtered) < min_count:
        filtered += [c for c in context if c not in filtered][:min_count - len(filtered)]
    return filtered

def extract_keywords(query):
    # 优先提取门店、产品等实体（可根据实际业务扩展）
    # 这里简单用正则匹配“店”、“中心”、“产品”等关键词
    keywords = set()
    # 匹配“XX店”
    keywords.update(re.findall(r"[\u4e00-\u9fa5]{2,}店", query))
    # 匹配“XX中心”
    keywords.update(re.findall(r"[\u4e00-\u9fa5]{2,}中心", query))
    # 匹配“产品XX”
    keywords.update(re.findall(r"产品[\u4e00-\u9fa5A-Za-z0-9]+", query))
    # 也可加入其它业务关键词
    # 若无匹配，退回分词法
    if not keywords:
        keywords = set([w for w in query.replace('，', ' ').replace('。', ' ').split() if len(w) > 1])
    return list(keywords)

def iterative_rag_search(self, query):
    # 首轮：原始query向量检索
    context = self.search_local(query)
    print("\n[RAG首轮召回片段]:")
    for res in context:
        print(res['content'])
    # 提取关键词
    keywords = extract_keywords(query)
    # 二轮：用关键词分别检索补充
    extra_context = []
    for kw in keywords:
        kw_context = self.search_local(kw, use_cache=False)
        print(f"\n[RAG关键词召回片段 - 关键词:{kw}]:")
        for res in kw_context:
            print(res['content'])
        extra_context.extend(kw_context)
    # 合并去重
    all_context = {res['content']: res for res in context + extra_context}
    merged_context = list(all_context.values())
    # 关键词过滤
    filtered_context = filter_context_by_keywords(merged_context, query, min_count=3)
    print("\n[最终用于大模型的上下文片段]:")
    for res in filtered_context:
        print(res['content'])
    return filtered_context

class WarehouseRAGSystem:
    def __init__(self):
        self.config = Config()
        self.knowledge_base = KnowledgeBase(self.config)
    
    def process_query(self, query: str) -> Dict:
        try:
            results, has_high_match = self.knowledge_base.hybrid_search(query)
            
            if results:  # 只要有结果就使用，不一定要达到阈值
                answer = self.knowledge_base.generate_response(query, results[:3])
                
                return {
                    "question": query,
                    "answer": answer,
                    "sources": [res["metadata"].get("source", res["source"]) for res in results],
                    "context": results,
                    "source_type": "local",
                    "confidence": min(1.0, max(0.0, results[0]["score"]))
                }
            else:
                response = self.knowledge_base.llm.invoke([{
                    "role": "user",
                    "content": query
                }])
                
                return {
                    "question": query,
                    "answer": response.content,
                    "sources": [],
                    "source_type": "llm",
                    "confidence": 0.7
                }
        except Exception as e:
            return {
                "question": query,
                "answer": f"查询失败: {str(e)}",
                "sources": [],
                "source_type": "error"
            }
    
    def close(self):
        self.knowledge_base.save_vector_index()
        self.knowledge_base.local_db.close()

def display_result(result: Dict):
    print("\n=== 回答 ===")
    print(result['answer'])
    
    if result.get('source_type') == "local":
        print(f"\n=== 置信度: {result.get('confidence', 0):.1%} ===")
        print("\n=== 信息来源 ===")
        
        sources = {}
        for item in result.get('context', []):
            source = item.get('metadata', {}).get('source', item.get('source', '未知'))
            if source not in sources:
                sources[source] = 1
        
        for source in sources:
            print(f"- {source}")
    elif result.get('source_type') == "llm":
        print("\n=== 信息来自大模型生成 ===")
    elif result.get('source_type') == "error":
        print("\n=== 查询出错 ===")

def main():
    print("=== RAG仓库知识管理系统 ===")
    print("请输入您的查询：")
    print("输入'退出'或'quit'结束会话\n")
    
    system = WarehouseRAGSystem()
    
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
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        print("请先安装依赖: pip install langchain-openai pymupdf sentence-transformers faiss-cpu python-dotenv")
        exit(1)
    
    main()
