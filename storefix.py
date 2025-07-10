import os
# 如果没有设置环境变量不要设置HF_ENDPOINT（删除下面三行），从官网下载模型或者使用本地模型文件
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ["HF_HUB_OFFLINE"] = "0"
os.environ["TRANSFORMERS_OFFLINE"] = "0"

os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "sk-FxhjDpv1D62n33JGICef3aVagezAr73GFnoXmSQ4ikMpf9Hb")#其他api密钥直接改这里，如果closeai的欠费了用这个密钥：sk-tgq6Xw43DMpw510JMGFofD8UPoBZTRUSrtoywgnbIdx8Z88X
os.environ["OPENAI_API_URL"] = os.getenv("OPENAI_API_URL", "https://api.openai-proxy.org/v1")
os.environ["MODEL_NAME"] = os.getenv("MODEL_NAME", "deepseek-chat")#使用的是closeai 的deeepseek-chat模型
EMBEDDING_MODEL = "./models/paraphrase-multilingual-mpnet-base-v2"  # 下载到本地的嵌入模型路径
os.environ["TRANSFORMERS_OFFLINE"] = "0"
rag = None  # FastAPI全局变量
import psycopg2
import fitz
import json
from typing import List, Dict, Tuple
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
# PostgreSQL配置
PG_HOST = os.getenv('PG_HOST', '192.168.28.135')
PG_PORT = os.getenv('PG_PORT', '5432')
PG_NAME = os.getenv('PG_NAME', 'companylink')
PG_USER = os.getenv('PG_USER', 'myuser')
PG_PASSWORD = os.getenv('PG_PASSWORD', '123456abc.')

PDF_DIR = './knowledge_pdfs'#本地知识库所需要pdf文件路径

class InMemoryKnowledgeBase:
    def __init__(self):
        self.documents: List[Document] = []
        self.embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        self.vectorstore = None

    def load_from_postgres(self):
        conn = psycopg2.connect(
            host=PG_HOST, port=PG_PORT, database=PG_NAME, user=PG_USER, password=PG_PASSWORD
        )
        cursor = conn.cursor()
        # 产品
        try:
            cursor.execute("SELECT product_id, product_name FROM product")
            for pid, pname in cursor.fetchall():
                self.documents.append(Document(
                    page_content=f"产品信息：{pname}",
                    metadata={"type": "product", "product_id": pid}
                ))
        except Exception: pass
        # 库存
        try:
            cursor.execute("""
                SELECT p.product_name, i.quantity, w.warehouse_name, i.date
                FROM inventory i
                JOIN product p ON i.product_id = p.product_id
                JOIN warehouse w ON i.warehouse_id = w.warehouse_id
                LIMIT 100
            """)
            for pname, qty, wname, date in cursor.fetchall():
                self.documents.append(Document(
                    page_content=f"{date}，仓库{wname}库存：{pname} {qty}件",
                    metadata={"type": "inventory", "warehouse": wname}
                ))
        except Exception: pass
        # 销售
        try:
            cursor.execute("""
                SELECT st.store_name, p.product_name, s.monthly_sales, s.month
                FROM sales s
                JOIN product p ON s.product_id = p.product_id
                JOIN store st ON s.store_id = st.store_id
                LIMIT 100
            """)
            for sname, pname, sales, month in cursor.fetchall():
                self.documents.append(Document(
                    page_content=f"{month}，门店{sname}销售：{pname} {sales}件",
                    metadata={"type": "sales", "store": sname}
                ))
        except Exception: pass
        # 门店
        try:
            cursor.execute("SELECT store_id, store_name FROM store")
            for sid, sname in cursor.fetchall():
                self.documents.append(Document(
                    page_content=f"门店信息：{sname}",
                    metadata={"type": "store", "store_id": sid}
                ))
        except Exception: pass
        cursor.close()
        conn.close()

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

class DatabaseAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            model_name=os.getenv("MODEL_NAME", "deepseek-chat"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_api_base=os.getenv("OPENAI_API_URL"),
            temperature=0.3
        )
        self.conn = psycopg2.connect(
            host=PG_HOST, port=PG_PORT, database=PG_NAME, user=PG_USER, password=PG_PASSWORD
        )

    def query(self, question: str, context: str = "") -> str:
        """复杂数据库智能问答：自动分析意图并生成SQL，结合LLM分析结果"""
        try:
            # 1. 结构化意图识别
            q_lower = question.lower()
            cursor = self.conn.cursor()
            if any(word in q_lower for word in ["销售", "销量", "营业额", "收入"]):
                cursor.execute("""
                    SELECT st.store_name, p.product_name, s.monthly_sales, s.month
                    FROM sales s
                    JOIN product p ON s.product_id = p.product_id
                    JOIN store st ON s.store_id = st.store_id
                    ORDER BY s.monthly_sales DESC
                    LIMIT 10
                """)
                rows = cursor.fetchall()
                cursor.close()
                if rows:
                    result = "\n".join([f"{r[3]} {r[0]}销售{r[1]}: {r[2]}件" for r in rows])
                    # 2. 结合LLM分析
                    prompt = PromptTemplate.from_template("""
数据库原始结果：
{result}

用户问题：{question}

请用专业术语对数据库结果进行业务分析和总结，若有上下文请结合上下文简要说明。
""")
                    return self.llm.invoke(prompt.format(result=result, question=question)).content
                else:
                    return "未找到相关销售数据"
            elif any(word in q_lower for word in ["库存", "存货", "余量"]):
                cursor.execute("""
                    SELECT p.product_name, i.quantity, w.warehouse_name, i.date
                    FROM inventory i
                    JOIN product p ON i.product_id = p.product_id
                    JOIN warehouse w ON i.warehouse_id = w.warehouse_id
                    ORDER BY i.quantity DESC
                    LIMIT 10
                """)
                rows = cursor.fetchall()
                cursor.close()
                if rows:
                    result = "\n".join([f"{r[3]} {r[2]}库存{r[0]}: {r[1]}件" for r in rows])
                    prompt = PromptTemplate.from_template("""
数据库原始结果：
{result}

用户问题：{question}

请用专业术语对数据库结果进行业务分析和总结，若有上下文请结合上下文简要说明。
""")
                    return self.llm.invoke(prompt.format(result=result, question=question)).content
                else:
                    return "未找到相关库存数据"
            # 其它类型可扩展
            return "请提供更具体的查询需求"
        except Exception as e:
            return f"数据库查询失败: {str(e)}"

    def close(self):
        self.conn.close()

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

class AgenticRAGSystem:
    def __init__(self):
        self.kb = InMemoryKnowledgeBase()
        self.kb.load_from_postgres()
        self.kb.load_from_pdfs()
        self.kb.build_vectorstore()
        self.db_agent = DatabaseAgent()
        self.pdf_agent = PDFMultiAgent(self.kb)
        self.llm = ChatOpenAI(
            model_name=os.getenv("MODEL_NAME"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_api_base=os.getenv("OPENAI_API_URL"),
            temperature=0.3
        )


    def process_query(self, query: str) -> Dict:
        # 1. 检索知识库
        docs = self.kb.vectorstore.similarity_search(query, k=5)
        context = "\n\n".join([d.page_content[:200] for d in docs]) if docs else ""
        # 2. 数据库Agent
        db_result = self.db_agent.query(query, context)
        # 3. PDF Agent
        pdf_result = self.pdf_agent.query(query)
        # 4. LLM融合
        prompt = PromptTemplate.from_template("""
【知识库片段】
{context}

【数据库分析】
{db_result}

【PDF检索】
{pdf_result}

【用户问题】
{question}

请综合所有信息，给出专业、结构化、简明的智能回答。
""")
        answer = self.llm.invoke(prompt.format(
            context=context, db_result=db_result, pdf_result=pdf_result, question=query
        )).content
        return {
            "answer": answer,
            "knowledge_context": context,
            "db_result": db_result,
            "pdf_result": pdf_result
        }

    def close(self):
        self.kb.cleanup()
        self.db_agent.close()

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

# 命令行交互
if __name__ == "__main__":
    rag = AgenticRAGSystem()
    try:
        while True:
            q = input("\n请输入您的查询（quit退出）：").strip()
            if q.lower() in ("quit", "exit", "退出"):
                break
            result = rag.process_query(q)
            print("\n【智能回答】\n", result["answer"])
    finally:
        rag.close()
