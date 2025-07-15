# -*- coding: utf-8 -*-
class Config:

    DB_HOST = 'yd.frp-era.com'
    DB_PORT = '11103'
    DB_NAME = 'postgres'
    DB_USER = 'postgres'
    DB_PASSWORD = 'ab12AB!@'
    client_encoding='utf8'
    
    SQLALCHEMY_DATABASE_URI = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?client_encoding=utf8'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'your-secret-key-here' 

    '''
        RAG_OPENAI_API_KEY = "sk-ubjkrzodjlihepttrgdmmqsxaulmoktrzvmvzzwpkaftmtcn"
        RAG_OPENAI_API_URL = "https://api.siliconflow.cn/v1"
        RAG_MODEL_NAME = "Qwen/Qwen2.5-72B-Instruct"
        RAG_EMBEDDING_MODEL = "Qwen/Qwen3-Embedding-4B"
    '''
    RAG_OPENAI_API_KEY = "sk-FxhjDpv1D62n33JGICef3aVagezAr73GFnoXmSQ4ikMpf9Hb"
    RAG_OPENAI_API_URL = "https://api.openai-proxy.org/v1"
    RAG_MODEL_NAME = "gpt-4.1"
    RAG_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    RAG_PDF_DIR = "./API_TextToText/knowledge_pdfs"
