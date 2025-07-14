'''
    TopAgent - 作为中枢大脑，负责理解、分析和Agent协调
'''

import os
import re
import json
import numpy as np
from config import Config
from typing import List, Dict
from langchain.schema import Document
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings

from API_TextToText.API_of_RAG._6_MemoryAgent import MemoryAgent

class TopAgent:
    def __init__(self, memory_agent: MemoryAgent, db_agent, pdf_agent, kb):
        self.memory_agent = memory_agent
        self.db_agent = db_agent
        self.pdf_agent = pdf_agent
        self.kb = kb
        self.llm = ChatOpenAI(
            model_name=Config.RAG_MODEL_NAME,
            openai_api_key=Config.RAG_OPENAI_API_KEY,
            openai_api_base=Config.RAG_OPENAI_API_URL,
            temperature=0.3
        )
        # 初始化语义检索组件
        self.embeddings = HuggingFaceEmbeddings(model_name = Config.RAG_EMBEDDING_MODEL)
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
        
        # 3. 优先执行数据库查询
        results = {}
        db_result = ""
        
        # 数据库查询（优先执行）
        if intent.get("requires_database", True):
            try:
                print("🔍 优先执行数据库查询...")
                # 直接执行数据库查询
                db_result = self.db_agent.query(question, context)
                
                # 检查数据库查询是否成功返回具体数据
                if db_result and "未找到相关数据" not in db_result and "无法理解查询需求" not in db_result:
                    results["db_result"] = db_result
                    print("✅ 数据库查询成功，返回具体数据")
                else:
                    print("⚠️ 数据库查询未返回具体数据")
                    results["db_result"] = "数据库查询未返回具体数据"
                    
                # 获取数据库摘要信息
                try:
                    db_summary = self.db_agent.get_database_summary()
                    results["db_summary"] = db_summary
                except Exception:
                    pass
                    
            except Exception as e:
                print(f"❌ 数据库查询失败: {e}")
                results["db_result"] = f"数据库查询失败: {e}"
        
        # 4. 如果数据库查询成功返回具体数据，直接基于数据生成回答
        if results.get("db_result") and "未找到相关数据" not in results["db_result"] and "无法理解查询需求" not in results["db_result"]:
            print("🎯 基于数据库具体数据生成回答...")
            
            # 知识库查询（作为补充）
            if intent.get("requires_knowledge_base", True):
                try:
                    if hasattr(self.kb, 'query_with_database_context'):
                        results["knowledge_context"] = self.kb.query_with_database_context(question)
                    else:
                        docs = self.kb.vectorstore.similarity_search(question, k=3)
                        results["knowledge_context"] = self._format_knowledge_context(docs)
                except Exception as e:
                    results["knowledge_context"] = f"知识库检索失败: {e}"
            
            # PDF查询（作为补充）
            if intent.get("requires_pdf", True):
                try:
                    results["pdf_result"] = self.pdf_agent.query(question)
                except Exception as e:
                    results["pdf_result"] = f"PDF检索失败: {e}"
            
            # 基于数据库具体数据生成智能回答
            final_answer = self._generate_data_driven_answer(question, results, intent, semantic_results)
            
            return {
                "answer": final_answer,
                "knowledge_context": results.get("knowledge_context", ""),
                "db_result": results.get("db_result", ""),
                "pdf_result": results.get("pdf_result", ""),
                "db_summary": results.get("db_summary", ""),
                "source_type": "database_driven",
                "confidence": min(0.95, 0.8 + max_similarity * 0.15),
                "agent_decision": intent,
                "semantic_results": semantic_results
            }
        
        # 5. 如果数据库查询失败，使用传统多Agent模式
        print("🔄 使用传统多Agent协调模式...")
        
        # 知识库查询
        if intent.get("requires_knowledge_base", True):
            try:
                if hasattr(self.kb, 'query_with_database_context'):
                    results["knowledge_context"] = self.kb.query_with_database_context(question)
                else:
                    docs = self.kb.vectorstore.similarity_search(question, k=5)
                    results["knowledge_context"] = self._format_knowledge_context(docs)
            except Exception as e:
                results["knowledge_context"] = f"知识库检索失败: {e}"
        
        # PDF查询
        if intent.get("requires_pdf", True):
            try:
                results["pdf_result"] = self.pdf_agent.query(question)
            except Exception as e:
                results["pdf_result"] = f"PDF检索失败: {e}"
        
        # 智能结果整合
        final_answer = self._generate_intelligent_answer(question, results, intent, semantic_results)
        
        return {
            "answer": final_answer,
            "knowledge_context": results.get("knowledge_context", ""),
            "db_result": results.get("db_result", ""),
            "pdf_result": results.get("pdf_result", ""),
            "db_summary": results.get("db_summary", ""),
            "source_type": "top_agent_coordinated",
            "confidence": min(0.9, 0.7 + max_similarity * 0.2),
            "agent_decision": intent,
            "semantic_results": semantic_results
        }
    
    def _generate_data_driven_answer(self, question: str, results: Dict, intent: Dict, semantic_results: List) -> str:
        """基于数据库具体数据生成回答"""
        try:
            # 构建数据驱动的回答
            data_prompt = PromptTemplate.from_template("""
作为智能仓储系统的数据分析专家，请基于以下数据库具体数据，为用户问题提供直接、准确、数据驱动的回答：

用户问题：{question}

【数据库具体数据】
{db_result}

【知识库补充信息】
{knowledge_context}

【PDF补充信息】
{pdf_result}

请提供：
1. 直接回答用户问题，基于数据库具体数据
2. 数据分析和业务洞察
3. 具体的数值和统计信息
4. 基于数据的建议

要求：
- 回答要基于数据库的具体数据，不要给出SQL建议
- 突出关键数据和统计信息
- 提供数据驱动的业务洞察
- 回答要简洁、专业、准确

基于数据的回答：
""")
            
            response = self.llm.invoke(data_prompt.format(
                question=question,
                db_result=results.get("db_result", "无数据库数据"),
                knowledge_context=results.get("knowledge_context", "无知识库信息"),
                pdf_result=results.get("pdf_result", "无PDF信息")
            ))
            
            return response.content.strip()
            
        except Exception as e:
            return f"数据驱动回答生成失败: {str(e)}"
    
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