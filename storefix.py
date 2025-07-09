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
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import Tool
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

class Config:
    """系统配置类"""
    def __init__(self):
        self.embedding_model = "paraphrase-multilingual-mpnet-base-v2"
        self.llm_model = os.getenv("MODEL_NAME")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_api_base = os.getenv("OPENAI_API_URL")
        self.pdf_knowledge_dir = "./knowledge_pdfs"
        self.index_dim = 768
        self.top_k = 10
        self.rag_threshold = 0.75  # 调整阈值
        self.chunk_size = 500
        self.chunk_overlap = 50
        self.cache_expiry = 86400
        self.max_retrieval_docs = 5
        self.max_agent_iterations = 3  # 限制Agent迭代次数

class KnowledgeMatcher:
    """增强的知识库匹配器"""
    def __init__(self, config: Config):
        self.config = config
        self.embedder = SentenceTransformer(config.embedding_model)
        self.vectorstore = None
        self._init_knowledge_base()
    
    def _init_knowledge_base(self):
        """初始化统一知识库"""
        try:
            # 加载向量索引 - 修复pickle安全问题
            if os.path.exists("vector_db.index"):
                # 使用与storefix.py兼容的加载方式
                import faiss
                self.vector_index = faiss.read_index("vector_db.index")
                print("✅ 加载已有知识库向量索引")
                
                # 创建LangChain兼容的向量存储
                embeddings = HuggingFaceEmbeddings(model_name=self.config.embedding_model)
                # 创建一个临时的向量存储用于LangChain接口
                self.vectorstore = self._create_langchain_compatible_store(embeddings)
            else:
                print("⚠️ 知识库向量索引不存在，请先运行storefix.py同步数据")
                self.vectorstore = None
        except Exception as e:
            print(f"❌ 加载知识库失败: {e}")
            self.vectorstore = None
    
    def _create_langchain_compatible_store(self, embeddings):
        """创建LangChain兼容的向量存储"""
        try:
            # 从SQLite数据库读取知识内容
            import sqlite3
            conn = sqlite3.connect("knowledge.db")
            cursor = conn.cursor()
            
            cursor.execute("SELECT content, metadata, source FROM knowledge ORDER BY id")
            rows = cursor.fetchall()
            conn.close()
            
            if not rows:
                print("⚠️ 知识库中没有数据")
                return None
            
            # 创建文档列表
            documents = []
            for row in rows:
                content, metadata_json, source = row
                metadata = json.loads(metadata_json) if metadata_json else {}
                metadata['source'] = source
                
                documents.append(Document(
                    page_content=content,
                    metadata=metadata
                ))
            
            # 创建向量存储
            vectorstore = FAISS.from_documents(documents, embeddings)
            return vectorstore
            
        except Exception as e:
            print(f"❌ 创建LangChain兼容存储失败: {e}")
            return None
    
    def check_relevance(self, query: str) -> Tuple[bool, float, List[Dict]]:
        """检查问题与知识库的相关性"""
        if not self.vectorstore:
            return False, 0.0, []
        
        try:
            # 检索相关文档
            docs = self.vectorstore.similarity_search_with_score(query, k=self.config.max_retrieval_docs)
            
            if not docs:
                return False, 0.0, []
            
            # 计算平均匹配度
            scores = [1.0 - score for _, score in docs]
            avg_score = sum(scores) / len(scores)
            max_score = max(scores)
            
            # 检查是否达到阈值（使用平均分和最高分的加权）
            relevance_score = (avg_score * 0.7 + max_score * 0.3)
            is_relevant = relevance_score >= self.config.rag_threshold
            
            # 格式化结果
            results = []
            for doc, score in docs:
                results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": 1.0 - score,
                    "source": doc.metadata.get("source", "unknown")
                })
            
            return is_relevant, relevance_score, results
            
        except Exception as e:
            print(f"❌ 相关性检查失败: {e}")
            return False, 0.0, []

class DatabaseAgent:
    """增强的数据库专用Agent"""
    def __init__(self, config: Config):
        self.config = config
        self.db_path = "store.db"
        self.llm = ChatOpenAI(
            model_name=self.config.llm_model,
            openai_api_key=self.config.openai_api_key,
            openai_api_base=self.config.openai_api_base,
            temperature=0.3
        )
        self._init_database_schema()
    
    def _init_database_schema(self):
        """初始化数据库模式信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取表结构信息
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            self.schema_info = {}
            for table in tables:
                table_name = table[0]
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = cursor.fetchall()
                self.schema_info[table_name] = [col[1] for col in columns]
            
            conn.close()
            print(f"✅ 数据库模式加载完成，包含 {len(self.schema_info)} 个表")
        except Exception as e:
            print(f"❌ 数据库模式加载失败: {e}")
            self.schema_info = {}
    
    def query(self, question: str, context: str = "") -> str:
        """智能数据库查询"""
        try:
            # 分析问题类型
            query_type = self._analyze_query_type(question)
            
            # 执行相应的查询
            if query_type == "sales":
                return self._query_sales_data(question, context)
            elif query_type == "inventory":
                return self._query_inventory_data(question, context)
            elif query_type == "supply":
                return self._query_supply_data(question, context)
            elif query_type == "analysis":
                return self._query_analysis_data(question, context)
            else:
                return self._query_general_data(question, context)
                
        except Exception as e:
            return f"❌ 数据库查询失败: {str(e)}"
    
    def _analyze_query_type(self, question: str) -> str:
        """分析查询类型"""
        question_lower = question.lower()
        
        if any(word in question_lower for word in ["销售", "销量", "营业额", "收入"]):
            return "sales"
        elif any(word in question_lower for word in ["库存", "存货", "数量", "余量"]):
            return "inventory"
        elif any(word in question_lower for word in ["供应", "配送", "运输", "物流"]):
            return "supply"
        elif any(word in question_lower for word in ["分析", "统计", "趋势", "对比"]):
            return "analysis"
        else:
            return "general"
    
    def _query_sales_data(self, query: str, context: str = "") -> str:
        """查询销售数据"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 根据查询内容动态生成SQL
            if "北京中关村店" in query:
                cursor.execute("""
                    SELECT p.product_name, s.monthly_sales, s.month, st.store_name
                    FROM sales s
                    JOIN product p ON s.product_id = p.product_id
                    JOIN store st ON s.store_id = st.store_id
                    WHERE st.store_name = '北京中关村店'
                    ORDER BY s.month DESC
                    LIMIT 10
                """)
            else:
                cursor.execute("""
                    SELECT st.store_name, p.product_name, s.monthly_sales, s.month
                    FROM sales s
                    JOIN product p ON s.product_id = p.product_id
                    JOIN store st ON s.store_id = st.store_id
                    ORDER BY s.monthly_sales DESC
                    LIMIT 10
                """)
            
            rows = cursor.fetchall()
            conn.close()
            
            if rows:
                result = "📊 销售数据分析：\n"
                for row in rows:
                    if len(row) == 4:
                        result += f"- {row[0]}: {row[1]}件，日期：{row[2]}\n"
                    else:
                        result += f"- {row[0]}销售{row[1]}: {row[2]}件，日期：{row[3]}\n"
                
                # 结合上下文进行智能分析
                if context:
                    result += f"\n💡 结合知识库分析：{self._enhance_with_context(result, context)}"
                
                return result
            else:
                return "❌ 未找到相关销售数据"
        except Exception as e:
            return f"❌ 查询销售数据失败: {str(e)}"
    
    def _query_inventory_data(self, query: str, context: str = "") -> str:
        """查询库存数据"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT p.product_name, i.quantity, w.warehouse_name, i.date
                FROM inventory i
                JOIN product p ON i.product_id = p.product_id
                JOIN warehouse w ON i.warehouse_id = w.warehouse_id
                ORDER BY i.quantity DESC
                LIMIT 10
            """)
            
            rows = cursor.fetchall()
            conn.close()
            
            if rows:
                result = "📦 库存数据分析：\n"
                for row in rows:
                    result += f"- {row[0]}: {row[1]}件，位于{row[2]}，日期：{row[3]}\n"
                
                # 结合上下文进行智能分析
                if context:
                    result += f"\n💡 结合知识库分析：{self._enhance_with_context(result, context)}"
                
                return result
            else:
                return "❌ 未找到相关库存数据"
        except Exception as e:
            return f"❌ 查询库存数据失败: {str(e)}"
    
    def _query_supply_data(self, query: str, context: str = "") -> str:
        """查询供应链数据"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT w.warehouse_name, st.store_name, p.product_name, s.monthly_supply, s.month
                FROM supply s
                JOIN warehouse w ON s.warehouse_id = w.warehouse_id
                JOIN store st ON s.store_id = st.store_id
                JOIN product p ON s.product_id = p.product_id
                ORDER BY s.monthly_supply DESC
                LIMIT 10
            """)
            
            rows = cursor.fetchall()
            conn.close()
            
            if rows:
                result = "🚚 供应链数据分析：\n"
                for row in rows:
                    result += f"- {row[0]}向{row[1]}供应{row[2]}: {row[3]}件，日期：{row[4]}\n"
                
                # 结合上下文进行智能分析
                if context:
                    result += f"\n💡 结合知识库分析：{self._enhance_with_context(result, context)}"
                
                return result
            else:
                return "❌ 未找到相关供应链数据"
        except Exception as e:
            return f"❌ 查询供应链数据失败: {str(e)}"
    
    def _query_analysis_data(self, query: str, context: str = "") -> str:
        """查询分析数据"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 综合数据分析
            cursor.execute("""
                SELECT 
                    p.product_name,
                    SUM(s.monthly_sales) as total_sales,
                    AVG(i.quantity) as avg_inventory,
                    COUNT(DISTINCT st.store_id) as store_count
                FROM product p
                LEFT JOIN sales s ON p.product_id = s.product_id
                LEFT JOIN inventory i ON p.product_id = i.product_id
                LEFT JOIN store st ON s.store_id = st.store_id
                GROUP BY p.product_id
                ORDER BY total_sales DESC
                LIMIT 5
            """)
            
            rows = cursor.fetchall()
            conn.close()
            
            if rows:
                result = "📈 综合数据分析：\n"
                for row in rows:
                    result += f"- {row[0]}: 总销量{row[1]}件，平均库存{row[2]:.0f}件，覆盖{row[3]}家门店\n"
                
                # 结合上下文进行智能分析
                if context:
                    result += f"\n💡 结合知识库分析：{self._enhance_with_context(result, context)}"
                
                return result
            else:
                return "❌ 未找到相关分析数据"
        except Exception as e:
            return f"❌ 查询分析数据失败: {str(e)}"
    
    def _query_general_data(self, query: str, context: str = "") -> str:
        """通用数据查询"""
        return "请提供更具体的查询需求，如销售、库存、供应链或分析相关信息。"
    
    def _enhance_with_context(self, data_result: str, context: str) -> str:
        """结合上下文增强数据解释"""
        try:
            prompt = PromptTemplate.from_template("""
基于以下数据库查询结果和知识库上下文，提供智能分析和建议：

数据库查询结果：
{data_result}

知识库上下文：
{context}

请结合两者提供：
1. 数据趋势分析
2. 业务洞察
3. 优化建议

回答要简洁明了，不超过100字。
""")
            
            response = self.llm.invoke(prompt.format(data_result=data_result, context=context))
            return response.content
        except Exception as e:
            return f"上下文分析失败: {str(e)}"

class PDFAgent:
    """增强的PDF文档专用Agent"""
    def __init__(self, config: Config, pdf_path: str, agent_name: str):
        self.config = config
        self.pdf_path = pdf_path
        self.agent_name = agent_name
        self.llm = ChatOpenAI(
            model_name=self.config.llm_model,
            openai_api_key=self.config.openai_api_key,
            openai_api_base=self.config.openai_api_base,
            temperature=0.3
        )
        self.vectorstore = None
        self._init_pdf_vectorstore()
    
    def _extract_pdf_content(self) -> List[Document]:
        """提取PDF内容"""
        try:
            doc = fitz.open(self.pdf_path)
            documents = []
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text()
                if text.strip():
                    documents.append(Document(
                        page_content=text,
                        metadata={"source": os.path.basename(self.pdf_path), "page": page_num + 1}
                    ))
            
            doc.close()
            return documents
        except Exception as e:
            print(f"❌ PDF内容提取失败: {e}")
            return []
    
    def _init_pdf_vectorstore(self):
        """初始化PDF向量存储"""
        documents = self._extract_pdf_content()
        if not documents:
            print(f"⚠️ PDF文件 {self.pdf_path} 内容为空")
            return
        
        try:
            # 文本分割
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.config.chunk_size, 
                chunk_overlap=self.config.chunk_overlap
            )
            texts = text_splitter.split_documents(documents)
            
            # 创建向量存储
            embeddings = HuggingFaceEmbeddings(model_name=self.config.embedding_model)
            self.vectorstore = FAISS.from_documents(texts, embeddings)
            
            print(f"✅ {self.agent_name} 向量存储初始化完成")
            
        except Exception as e:
            print(f"❌ PDF向量存储初始化失败: {e}")
    
    def query(self, question: str, context: str = "") -> str:
        """智能PDF内容查询"""
        if not self.vectorstore:
            return f"❌ PDF Agent {self.agent_name} 未正确初始化"
        
        try:
            # 检索相关文档
            docs = self.vectorstore.similarity_search(question, k=3)
            
            if not docs:
                return f"❌ 在{self.agent_name}中未找到相关信息"
            
            # 构建上下文
            pdf_context = "\n\n".join([doc.page_content for doc in docs])
            
            # 使用LLM生成回答
            prompt = PromptTemplate.from_template("""
基于以下PDF文档内容和额外上下文，回答问题：

PDF文档内容：
{pdf_context}

额外上下文：
{context}

问题：{question}

请根据文档内容给出准确、详细的回答。如果文档中没有相关信息，请说明。
如果提供了额外上下文，请结合两者进行分析。
""")
            
            response = self.llm.invoke(prompt.format(
                pdf_context=pdf_context, 
                context=context if context else "无额外上下文", 
                question=question
            ))
            return response.content
            
        except Exception as e:
            return f"❌ PDF查询失败: {str(e)}"

class AgenticRAGSystem:
    """增强的Agentic RAG系统"""
    def __init__(self):
        self.config = Config()
        self.knowledge_matcher = KnowledgeMatcher(self.config)
        self.database_agent = DatabaseAgent(self.config)
        self.pdf_agents = {}
        self._init_pdf_agents()
        self.llm = ChatOpenAI(
            model_name=self.config.llm_model,
            openai_api_key=self.config.openai_api_key,
            openai_api_base=self.config.openai_api_base,
            temperature=0.3
        )
        self.query_history = []  # 查询历史，避免重复处理
    
    def _init_pdf_agents(self):
        """初始化PDF Agents"""
        try:
            pdf_files = [f for f in os.listdir(self.config.pdf_knowledge_dir) if f.endswith('.pdf')]
            for i, pdf_file in enumerate(pdf_files[:2]):  # 只取前两个PDF
                pdf_path = os.path.join(self.config.pdf_knowledge_dir, pdf_file)
                agent_name = f"PDF{i+1}_{os.path.splitext(pdf_file)[0]}"
                self.pdf_agents[agent_name] = PDFAgent(self.config, pdf_path, agent_name)
        except Exception as e:
            print(f"❌ 初始化PDF Agents失败: {e}")
    
    def process_query(self, query: str) -> Dict:
        """增强的查询处理逻辑"""
        try:
            print(f"🔍 正在分析问题: {query}")
            
            # 检查是否重复查询
            if query in self.query_history:
                return {
                    "question": query,
                    "answer": "检测到重复查询，请提供新的问题。",
                    "source_type": "duplicate",
                    "confidence": 1.0
                }
            
            self.query_history.append(query)
            
            # 1. 检查知识库相关性
            is_relevant, relevance_score, knowledge_results = self.knowledge_matcher.check_relevance(query)
            
            print(f"📊 知识库匹配度: {relevance_score:.2%}")
            
            # 2. 收集所有相关信息
            all_context = self._gather_all_context(query, knowledge_results)
            
            # 3. 智能路由和回答生成
            if is_relevant and knowledge_results:
                print("🎯 使用知识库直接回答")
                answer = self._generate_enhanced_answer(query, knowledge_results, all_context)
                return {
                    "question": query,
                    "answer": answer,
                    "source_type": "knowledge_base",
                    "confidence": relevance_score,
                    "relevance_score": relevance_score
                }
            else:
                print("🤖 使用Agent系统回答")
                answer = self._route_to_appropriate_agent(query, all_context)
                
                return {
                    "question": query,
                    "answer": answer,
                    "source_type": "agent_system",
                    "confidence": 0.7,
                    "relevance_score": relevance_score
                }
            
        except Exception as e:
            # 4. 如果所有方法都失败，使用LLM直接回答
            print(f"⚠️ 使用LLM直接回答: {e}")
            answer = self._fallback_to_llm(query)
            return {
                "question": query,
                "answer": answer,
                "source_type": "llm_fallback",
                "confidence": 0.5
            }
    
    def _gather_all_context(self, query: str, knowledge_results: List[Dict]) -> str:
        """收集所有相关上下文"""
        context_parts = []
        
        # 添加知识库结果
        if knowledge_results:
            context_parts.append("知识库信息：")
            for result in knowledge_results[:3]:
                context_parts.append(f"- {result['content'][:200]}...")
        
        # 添加数据库信息（如果问题涉及业务数据）
        if any(keyword in query for keyword in ["销售", "库存", "供应", "门店", "数据"]):
            try:
                db_context = self.database_agent._query_general_data(query, "")
                if db_context and "请提供更具体" not in db_context:
                    context_parts.append(f"数据库信息：{db_context}")
            except:
                pass
        
        # 添加PDF信息
        pdf_contexts = []
        for agent_name, agent in self.pdf_agents.items():
            try:
                pdf_result = agent.query(query, "")
                if pdf_result and "未找到" not in pdf_result:
                    pdf_contexts.append(f"[{agent_name}]: {pdf_result[:300]}...")
            except:
                pass
        
        if pdf_contexts:
            context_parts.append("PDF文档信息：")
            context_parts.extend(pdf_contexts)
        
        return "\n\n".join(context_parts) if context_parts else "无相关上下文"
    
    def _generate_enhanced_answer(self, query: str, knowledge_results: List[Dict], all_context: str) -> str:
        """基于知识库结果生成增强回答"""
        try:
            # 构建上下文
            context = "\n\n".join([result["content"] for result in knowledge_results[:3]])
            
            prompt = PromptTemplate.from_template("""
基于以下知识库内容和其他相关信息，回答问题：

知识库内容：
{context}

其他相关信息：
{all_context}

问题：{question}

请根据知识库内容给出准确、详细的回答。如果其他信息与问题相关，请结合分析。
回答要结构清晰，重点突出。
""")
            
            response = self.llm.invoke(prompt.format(
                context=context, 
                all_context=all_context, 
                question=query
            ))
            return response.content
            
        except Exception as e:
            return f"❌ 基于知识库生成回答失败: {str(e)}"
    
    def _route_to_appropriate_agent(self, query: str, all_context: str) -> str:
        """智能路由到合适的Agent"""
        try:
            # 判断问题类型
            if any(keyword in query for keyword in ["销售", "库存", "供应", "北京中关村店", "门店", "数据"]):
                # 数据库查询 + 结合知识库
                db_answer = self.database_agent.query(query, all_context)
                
                # 如果数据库有结果，进一步结合PDF信息
                if db_answer and "未找到" not in db_answer:
                    enhanced_answer = self._enhance_with_pdf_context(db_answer, query)
                    return enhanced_answer
                else:
                    return db_answer
            else:
                # 使用PDF Agents + 结合数据库信息
                answers = []
                for agent_name, agent in self.pdf_agents.items():
                    try:
                        answer = agent.query(query, all_context)
                        if answer and "未找到" not in answer:
                            answers.append(f"[{agent_name}]: {answer}")
                    except Exception as e:
                        print(f"❌ PDF Agent {agent_name} 查询失败: {e}")
                
                if answers:
                    combined_answer = "\n\n".join(answers)
                    # 进一步结合数据库信息
                    enhanced_answer = self._enhance_with_db_context(combined_answer, query)
                    return enhanced_answer
                else:
                    return "❌ 在现有知识库中未找到相关信息"
                    
        except Exception as e:
            return f"❌ Agent路由失败: {str(e)}"
    
    def _enhance_with_pdf_context(self, db_answer: str, query: str) -> str:
        """用PDF信息增强数据库回答"""
        try:
            pdf_contexts = []
            for agent_name, agent in self.pdf_agents.items():
                try:
                    pdf_result = agent.query(query, db_answer)
                    if pdf_result and "未找到" not in pdf_result:
                        pdf_contexts.append(f"[{agent_name}补充]: {pdf_result}")
                except:
                    pass
            
            if pdf_contexts:
                enhanced_answer = f"{db_answer}\n\n📚 知识库补充信息：\n" + "\n\n".join(pdf_contexts)
                return enhanced_answer
            else:
                return db_answer
                
        except Exception as e:
            return f"{db_answer}\n\n❌ PDF增强失败: {str(e)}"
    
    def _enhance_with_db_context(self, pdf_answer: str, query: str) -> str:
        """用数据库信息增强PDF回答"""
        try:
            # 尝试获取相关数据库信息
            db_context = self.database_agent._query_general_data(query, pdf_answer)
            if db_context and "请提供更具体" not in db_context:
                enhanced_answer = f"{pdf_answer}\n\n💾 数据库补充信息：\n{db_context}"
                return enhanced_answer
            else:
                return pdf_answer
                
        except Exception as e:
            return f"{pdf_answer}\n\n❌ 数据库增强失败: {str(e)}"
    
    def _fallback_to_llm(self, query: str) -> str:
        """回退到LLM直接回答"""
        try:
            response = self.llm.invoke(f"请回答以下问题：{query}")
            return response.content
        except Exception as e:
            return f"❌ LLM回答失败: {str(e)}"
    
    def close(self):
        """关闭系统"""
        print("🔚 Agentic RAG系统已关闭")

def display_result(result: Dict):
    """格式化显示结果"""
    print("\n" + "="*50)
    print("📝 回答")
    print("="*50)
    print(result['answer'])
    
    print(f"\n🎯 置信度: {result.get('confidence', 0):.1%}")
    if result.get('relevance_score'):
        print(f"📊 知识库匹配度: {result.get('relevance_score', 0):.1%}")
    
    print("\n📋 信息来源")
    print("-" * 20)
    source_type = result.get('source_type', 'unknown')
    if source_type == "knowledge_base":
        print("✅ 知识库直接匹配")
    elif source_type == "agent_system":
        print("🤖 多Agent协调系统")
    elif source_type == "llm_fallback":
        print("⚠️ LLM直接生成")
    elif source_type == "duplicate":
        print("🔄 重复查询检测")
    else:
        print("❓ 未知来源")

def main():
    print("🚀 === 智能Agentic RAG仓库管理系统 ===")
    print("💡 请输入您的查询：")
    print("🔚 输入'退出'或'quit'结束会话\n")
    
    system = AgenticRAGSystem()
    
    try:
        while True:
            query = input("\n🤔 请输入您的查询> ").strip()
            if not query:
                continue
            if query.lower() in ['quit', 'exit', '退出']:
                break
            
            result = system.process_query(query)
            display_result(result)
          
    finally:
        system.close()
        print("\n👋 系统已关闭")

if __name__ == "__main__":
    try:
        from langchain_openai import ChatOpenAI
        from langchain_huggingface import HuggingFaceEmbeddings
        from langchain_community.vectorstores import FAISS
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        from langchain.prompts import PromptTemplate
    except ImportError:
        print("❌ 请先安装依赖: pip install langchain-openai langchain-huggingface langchain pymupdf sentence-transformers faiss-cpu python-dotenv")
        exit(1)
    
    main()
