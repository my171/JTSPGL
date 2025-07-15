from langchain_openai import ChatOpenAI
from typing import Dict
from config import Config

from API_TextToText.API_of_RAG._3_InMemoryKnowledgeBase import InMemoryKnowledgeBase
from API_TextToText.API_of_RAG._4_UniversalDatabaseAgent import UniversalDatabaseAgent
from API_TextToText.API_of_RAG._5_PDFMultiAgent import PDFMultiAgent
from API_TextToText.API_of_RAG._6_MemoryAgent import MemoryAgent
from API_TextToText.API_of_RAG._7_TopAgent import TopAgent

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
            model_name = Config.RAG_MODEL_NAME,
            openai_api_key = Config.RAG_OPENAI_API_KEY,
            openai_api_base = Config.RAG_OPENAI_API_URL,
            temperature=0.3
        )
        
        print("✅ 智能多Agent RAG系统初始化完成")
        print(f"📊 数据库连接: {Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_NAME}")
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