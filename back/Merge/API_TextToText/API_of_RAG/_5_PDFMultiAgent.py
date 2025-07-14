'''
    PDF Agent，支持多文档检索
'''

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS

from API_TextToText.API_of_RAG._3_InMemoryKnowledgeBase import InMemoryKnowledgeBase

class PDFMultiAgent:
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