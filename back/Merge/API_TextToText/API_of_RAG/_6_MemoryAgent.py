'''
    记忆Agent - 负责上下文学习和对话历史管理
'''

import os
from config import Config
from collections import deque
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate

class MemoryAgent:
    def __init__(self, max_memory_size=10):
        self.conversation_history = deque(maxlen=max_memory_size)
        self.context_summary = ""
        self.llm = ChatOpenAI(
            model_name=Config.RAG_MODEL_NAME,
            openai_api_key=Config.RAG_OPENAI_API_KEY,
            openai_api_base=Config.RAG_OPENAI_API_URL,
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