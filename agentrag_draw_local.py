import os

# 如果没设置环境变量不要设置HF_ENDPOINT（删除下面三行），从官网下载模型或者使用本地模型文件?
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ["HF_HUB_OFFLINE"] = "0"
os.environ["TRANSFORMERS_OFFLINE"] = "0"

os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "sk-FxhjDpv1D62n33JGICef3aVagezAr73GFnoXmSQ4ikMpf9Hb")
os.environ["OPENAI_API_URL"] = os.getenv("OPENAI_API_URL", "https://api.openai-proxy.org/v1")
os.environ["MODEL_NAME"] = os.getenv("MODEL_NAME", "gpt-4.1-nano")
# 使用本地SQLite数据库
os.environ["DB_PATH"] = os.getenv("DB_PATH", "store.db")

rag = None  # FastAPI全局变量
import sqlite3  # 使用SQLite数据库
import json
import numpy as np
from typing import List, Dict, Tuple, Optional
from fastapi import FastAPI
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.prompts import PromptTemplate
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from collections import deque
import re
import subprocess  # wh_add_draw
import sys  # wh_add_draw
import time  # wh_add_draw


class DatabaseSchemaAnalyzer:
    """动态数据库模式分析器 - 支持SQLite数据库"""

    def __init__(self, conn):
        self.conn = conn
        self.schema_info = {}
        self.table_relationships = {}
        self.analyze_schema()

    def analyze_schema(self):
        """分析数据库模式，获取所有表、字段、关系"""
        cursor = self.conn.cursor()
        try:
            # 1. 获取所有表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]

            # 2. 获取每个表的字段信息
            for table in tables:
                cursor.execute(f"PRAGMA table_info({table});")
                columns = cursor.fetchall()

                column_info = []
                for col in columns:
                    column_info.append({
                        'name': col[1],
                        'type': col[2],
                        'nullable': not col[3],  # SQLite中0表示NOT NULL
                        'default': col[4]
                    })

                self.schema_info[table] = column_info

            # 3. 分析外键关系 (SQLite外键支持有限)
            for table in tables:
                cursor.execute(f"PRAGMA foreign_key_list({table});")
                fks = cursor.fetchall()

                if table not in self.table_relationships:
                    self.table_relationships[table] = []

                for fk in fks:
                    self.table_relationships[table].append({
                        'column': fk[3],  # from列
                        'foreign_table': fk[2],  # to表
                        'foreign_column': fk[4]  # to列
                    })

            print(f"✅ 数据库模式分析完成：发现 {len(tables)} 个表")
            for table in tables:
                print(f"   📋 {table}: {len(self.schema_info[table])} 个字段")

        except Exception as e:
            print(f"❌ 数据库模式分析失败: {e}")
        finally:
            cursor.close()

    def get_schema_summary(self) -> str:
        """获取数据库模式摘要"""
        summary = []
        for table, columns in self.schema_info.items():
            col_names = [col['name'] for col in columns]
            summary.append(f"表 {table}: {', '.join(col_names)}")
        return "\n".join(summary)

    def find_related_tables(self, table_name: str) -> List[str]:
        """查找与指定表相关的表"""
        related = set()
        if table_name in self.table_relationships:
            for rel in self.table_relationships[table_name]:
                related.add(rel['foreign_table'])

        # 反向查找
        for table, rels in self.table_relationships.items():
            for rel in rels:
                if rel['foreign_table'] == table_name:
                    related.add(table)

        return list(related)


class UniversalDatabaseAgent:
    """通用数据库Agent - 支持SQLite数据库结构"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model_name=os.getenv("MODEL_NAME", "deepseek-chat"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_api_base=os.getenv("OPENAI_API_URL"),
            temperature=0.3
        )
        # 连接SQLite数据库
        db_path = os.getenv("DB_PATH", "store.db")
        self.conn = sqlite3.connect(db_path)
        self.schema_analyzer = DatabaseSchemaAnalyzer(self.conn)

    def generate_sql(self, question: str) -> Optional[str]:
        """使用LLM生成SQL查询"""
        try:
            schema_summary = self.schema_analyzer.get_schema_summary()

            prompt = PromptTemplate.from_template("""
你是一个SQL专家。根据以下数据库模式，为用户问题生成SQLite查询语句。
数据库模式：
{schema_summary}
用户问题：{question}
要求：
1. 只返回SQL语句，不要其他解释
2. 使用LIMIT 10限制结果数量
3. 如果涉及多表，使用适当的JOIN
4. 确保SQL语法正确
5. 如果问题不明确，返回NULL
SQL查询：
""")

            response = self.llm.invoke(prompt.format(
                schema_summary=schema_summary,
                question=question
            ))

            sql = response.content.strip()
            if sql.upper().startswith('SELECT') and 'NULL' not in sql.upper():
                return sql
            return None

        except Exception as e:
            print(f"❌ SQL生成失败: {e}")
            return None

    def execute_query(self, sql: str) -> List[Tuple]:
        """执行SQL查询"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            cursor.close()
            return rows
        except Exception as e:
            print(f"❌ SQL执行失败: {e}")
            return []

    def get_data_for_plotting(self, sql: str) -> Optional[List[Dict]]:  # wh_add_draw
        """执行SQL查询并返回字典列表，用于绘图。"""  # wh_add_draw
        try:  # wh_add_draw
            cursor = self.conn.cursor()  # wh_add_draw
            cursor.execute(sql)  # wh_add_draw
            columns = [description[0] for description in cursor.description]  # wh_add_draw
            rows = cursor.fetchall()  # wh_add_draw
            cursor.close()  # wh_add_draw
            return [dict(zip(columns, row)) for row in rows]  # wh_add_draw
        except Exception as e:  # wh_add_draw
            print(f"❌ SQL执行以获取绘图数据时失败: {e}")  # wh_add_draw
            return None  # wh_add_draw

    def analyze_results(self, question: str, rows: List[Tuple], sql: str) -> str:
        """分析查询结果"""
        if not rows:
            return "未找到相关数据"

        try:
            # 将结果格式化为文本
            result_text = "\n".join([str(row) for row in rows[:5]])  # 只显示前5行

            prompt = PromptTemplate.from_template("""
基于以下查询结果，为用户问题提供专业的业务分析：
用户问题：{question}
执行的SQL：{sql}
查询结果：
{result_text}
请提供：
1. 数据概览和关键指标
2. 业务洞察和建议
3. 数据趋势分析（如果适用）
回答要简洁专业，不超过200字。
""")

            response = self.llm.invoke(prompt.format(
                question=question,
                sql=sql,
                result_text=result_text
            ))

            return response.content

        except Exception as e:
            return f"结果分析失败: {str(e)}"

    def query(self, question: str, context: str = "") -> str:
        """通用数据库查询接口"""
        try:
            # 1. 生成SQL
            sql = self.generate_sql(question)
            if not sql:
                return "无法理解查询需求，请提供更具体的问题"

            # 2. 执行查询
            rows = self.execute_query(sql)

            # 3. 分析结果
            analysis = self.analyze_results(question, rows, sql)

            return analysis

        except Exception as e:
            return f"数据库查询失败: {str(e)}"

    def close(self):
        self.conn.close()


class InMemoryKnowledgeBase:
    def __init__(self):
        self.documents: List[Document] = []
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2")
        self.vectorstore = None

    def load_from_sqlite(self):
        """从SQLite数据库动态加载知识"""
        try:
            db_path = os.getenv("DB_PATH", "store.db")
            conn = sqlite3.connect(db_path)
            schema_analyzer = DatabaseSchemaAnalyzer(conn)

            # 为每个表生成知识片段
            for table_name, columns in schema_analyzer.schema_info.items():
                try:
                    # 获取表的前50行数据作为示例
                    cursor = conn.cursor()
                    cursor.execute(f"SELECT * FROM {table_name} LIMIT 50")
                    rows = cursor.fetchall()

                    if rows:
                        # 生成表结构描述
                        col_names = [col['name'] for col in columns]
                        table_desc = f"表 {table_name} 包含字段：{', '.join(col_names)}"
                        self.documents.append(Document(
                            page_content=table_desc,
                            metadata={"type": "table_schema", "table": table_name}
                        ))

                        # 生成数据示例
                        for i, row in enumerate(rows[:3]):  # 只取前3行
                            data_desc = f"{table_name}表数据示例{i + 1}：{dict(zip(col_names, row))}"
                            self.documents.append(Document(
                                page_content=data_desc,
                                metadata={"type": "table_data", "table": table_name, "row": i + 1}
                            ))

                except Exception as e:
                    print(f"⚠️ 处理表 {table_name} 时出错: {e}")
                    continue

            conn.close()
            print(f"✅ 成功加载 {len(self.documents)} 个数据库知识片段")
        except Exception as e:
            print(f"❌ 数据库知识加载失败: {e}")

    def build_vectorstore(self):
        if not self.documents:
            raise RuntimeError("没有知识片段可用于向量化")
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        docs = splitter.split_documents(self.documents)
        self.vectorstore = FAISS.from_documents(docs, self.embeddings)

    def cleanup(self):
        self.documents.clear()
        self.vectorstore = None


class MemoryAgent:
    """记忆Agent - 负责上下文学习和对话历史管理"""

    def __init__(self, max_memory_size=10):
        self.conversation_history = deque(maxlen=max_memory_size)
        self.context_summary = ""
        self.llm = ChatOpenAI(
            model_name=os.getenv("MODEL_NAME", "deepseek-chat"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_api_base=os.getenv("OPENAI_API_URL"),
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
                f"Q{i + 1}: {interaction['question']}\nA{i + 1}: {interaction['answer'][:100]}..."
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


class DrawingAgent:  # wh_add_draw
    """绘图Agent - 负责生成并执行绘图代码"""  # wh_add_draw

    def __init__(self):  # wh_add_draw
        self.llm = ChatOpenAI(  # wh_add_draw
            model_name=os.getenv("MODEL_NAME", "deepseek-chat"),  # wh_add_draw
            openai_api_key=os.getenv("OPENAI_API_KEY"),  # wh_add_draw
            openai_api_base=os.getenv("OPENAI_API_URL"),  # wh_add_draw
            temperature=0.4  # wh_add_draw
        )  # wh_add_draw

    def _extract_code(self, text: str) -> str:  # wh_add_draw
        """从文本中提取Python代码块"""  # wh_add_draw
        if '```python' in text:  # wh_add_draw
            start = text.find('```python') + len('```python')  # wh_add_draw
            end = text.find('```', start)  # wh_add_draw
            return text[start:end].strip()  # wh_add_draw
        elif '```' in text:  # wh_add_draw
            start = text.find('```') + 3  # wh_add_draw
            end = text.find('```', start)  # wh_add_draw
            return text[start:end].strip()  # wh_add_draw
        return text  # wh_add_draw

    def draw(self, question: str, data_context: str = "") -> str:  # wh_add_draw
        """根据问题和数据上下文生成并执行绘图代码"""  # wh_add_draw
        timestamp = int(time.time())  # wh_add_draw
        plot_filename = f"plot_{timestamp}.png"  # wh_add_draw
        plot_context = ""  # wh_add_draw
        if data_context:  # wh_add_draw
            plot_context = f"""
请使用以下JSON格式的数据进行绘图，不要自己编造数据：
--- DATA START ---
{data_context}
--- DATA END ---
"""  # wh_add_draw
        plot_prompt_template = PromptTemplate.from_template("""
你是一个数据可视化专家。请根据用户的问题和提供的数据，生成一段完整的Python代码来绘制图表。

{plot_context}

用户问题：{question}

代码要求：
1. 使用 `matplotlib.pyplot` 库，并将其别名为 `plt`。
2. **在调用 `plt.show()` 之前，必须将图表保存到名为 '{plot_filename}' 的文件中。**
3. **最后必须调用 `plt.show()` 来显示图像。**
4. 代码必须是完整且可以直接运行的。
5. 使用英文作为图表的标签、标题，以避免乱码问题。
6. 如果提供了数据，请务必使用提供的数据。如果没有提供，可以使用合理、简洁的示例数据。
7. 给图表添加合适的标题 (Title) 和坐标轴标签 (X/Y Label)。
8. 在图表底部中心位置添加注释：'Note: Data is for reference only.'
9. 只返回Python代码块，用 ```python ... ``` 包围，不要任何额外的解释。
""")  # wh_add_draw
        final_prompt = plot_prompt_template.format(question=question, plot_context=plot_context,
                                                   plot_filename=plot_filename)  # wh_add_draw
        attempt = 0  # wh_add_draw
        max_attempts = 5  # wh_add_draw
        conversation = [{"role": "system",
                         "content": "You are a helpful AI assistant that generates Python code for plotting graphs using matplotlib."}]  # wh_add_draw
        conversation.append({"role": "user", "content": final_prompt})  # wh_add_draw
        while attempt < max_attempts:  # wh_add_draw
            attempt += 1  # wh_add_draw
            print(f"\n[绘图尝试 {attempt}/{max_attempts}] 正在向LLM请求绘图代码...")  # wh_add_draw
            response = self.llm.invoke(conversation)  # wh_add_draw
            ai_response = response.content.strip()  # wh_add_draw
            code = self._extract_code(ai_response)  # wh_add_draw
            if not code:  # wh_add_draw
                print(f"❌ 绘图失败: LLM未返回有效的代码。")  # wh_add_draw
                conversation.append({"role": "assistant", "content": ai_response})  # wh_add_draw
                conversation.append(
                    {"role": "user", "content": "你没有返回任何代码。请只返回被```python包围的代码块。"})  # wh_add_draw
                continue  # wh_add_draw

            code = code.replace("matplotlib.use('Agg')", "")  # wh_add_draw
            code = code.replace("plt.show()", "")  # wh_add_draw
            code = re.sub(r"plt\.savefig\s*\(['\"].*?['\"]\)", "", code, flags=re.DOTALL)  # wh_add_draw
            code += f"\n\n# Adding save and show commands by the system #wh_add_draw\n"  # wh_add_draw
            code += f"plt.savefig('{plot_filename}') #wh_add_draw\n"  # wh_add_draw
            code += f"plt.show() #wh_add_draw\n"  # wh_add_draw

            script_name = f"temp_plot_{timestamp}_{attempt}.py"  # wh_add_draw
            with open(script_name, "w", encoding="utf-8") as f:  # wh_add_draw
                f.write(code)  # wh_add_draw
            try:  # wh_add_draw
                result = subprocess.run(  # wh_add_draw
                    [sys.executable, script_name],  # wh_add_draw
                    capture_output=True,  # wh_add_draw
                    text=True,  # wh_add_draw
                    timeout=30  # wh_add_draw
                )  # wh_add_draw
                if result.returncode == 0 and os.path.exists(plot_filename):  # wh_add_draw
                    print(f"✅ 绘图成功! 图像已保存到: {os.path.abspath(plot_filename)}")  # wh_add_draw
                    os.remove(script_name)  # wh_add_draw
                    return f"绘图成功，文件保存在: {os.path.abspath(plot_filename)}"  # wh_add_draw
                else:  # wh_add_draw
                    error_msg = f"代码执行失败或未生成图像文件。\nReturn Code: {result.returncode}\nStderr: {result.stderr}"  # wh_add_draw
                    print(f"❌ {error_msg}")  # wh_add_draw
                    conversation.append({"role": "assistant", "content": ai_response})  # wh_add_draw
                    feedback = f"你生成的代码执行失败了，错误信息是: {error_msg}。请修复它并重新生成完整的代码。"  # wh_add_draw
                    conversation.append({"role": "user", "content": feedback})  # wh_add_draw
            except subprocess.TimeoutExpired:  # wh_add_draw
                error_msg = "执行超时: 绘图代码运行时间过长。"  # wh_add_draw
                print(f"❌ {error_msg}")  # wh_add_draw
                conversation.append({"role": "assistant", "content": ai_response})  # wh_add_draw
                conversation.append(
                    {"role": "user", "content": f"你生成的代码执行超时了。请优化代码，使其能快速执行。"})  # wh_add_draw
            except Exception as e:  # wh_add_draw
                error_msg = f"执行异常: {str(e)}"  # wh_add_draw
                print(f"❌ {error_msg}")  # wh_add_draw
                os.remove(script_name)  # wh_add_draw
                return f"绘图时发生未知错误: {error_msg}"  # wh_add_draw
            finally:  # wh_add_draw
                if os.path.exists(script_name):  # wh_add_draw
                    os.remove(script_name)  # wh_add_draw
        return f"⚠️ 经过 {max_attempts} 次尝试，仍然无法成功生成图像。"  # wh_add_draw


class TopAgent:
    """TopAgent - 作为中枢大脑，负责理解、分析和Agent协调"""

    def __init__(self, memory_agent: MemoryAgent, db_agent, kb, drawing_agent):  # wh_add_draw
        self.memory_agent = memory_agent
        self.db_agent = db_agent
        self.kb = kb
        self.drawing_agent = drawing_agent  # wh_add_draw
        self.llm = ChatOpenAI(
            model_name=os.getenv("MODEL_NAME", "deepseek-chat"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_api_base=os.getenv("OPENAI_API_URL"),
            temperature=0.3
        )
        # 初始化语义检索组件
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2")
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
                context_parts.append(
                    f"相关任务{i + 1}: {candidate['task']} - {candidate['text']} (相似度: {similarity:.2f})")

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
    "requires_database": true/false,  // 是否需要数据库查询获取数据
    "requires_knowledge_base": true/false,  // 是否需要知识库检索
    "requires_drawing": true/false, // 是否需要调用绘图Agent
    "primary_agent": "database/knowledge_base/drawing/multi",  // 主要Agent
    "reasoning": "分析理由"
}}

- 如果问题是关于“画图”、“绘制图表”、“可视化”等，请设置 "requires_drawing": true 并且 "primary_agent": "drawing"。
- 如果绘图需要查询数据库中的数据（如“画出每个仓库的库存量”），请同时设置 "requires_database": true。
- 其他情况照常分析。

只返回JSON，不要其他内容。
""")  # wh_add_draw

            response = self.llm.invoke(intent_prompt.format(
                question=question,
                context=context
            ))

            # 解析JSON响应
            intent_data = json.loads(response.content.strip())
            return intent_data

        except Exception as e:
            if any(keyword in question for keyword in ["画图", "绘制", "plot", "draw", "可视化"]):  # wh_add_draw
                return {  # wh_add_draw
                    "requires_database": True,  # wh_add_draw
                    "requires_knowledge_base": False,  # wh_add_draw
                    "requires_drawing": True,  # wh_add_draw
                    "primary_agent": "drawing",  # wh_add_draw
                    "reasoning": "关键词触发绘图模式"  # wh_add_draw
                }  # wh_add_draw
            # 默认返回多Agent模式
            return {
                "requires_database": True,
                "requires_knowledge_base": True,
                "requires_drawing": False,  # wh_add_draw
                "primary_agent": "multi",
                "reasoning": "默认多Agent模式"
            }

    def coordinate_agents(self, question: str, context: str = "") -> Dict:
        """协调各个Agent，获取综合回答"""
        if question.startswith("画图"):  # wh_add_draw
            print("INFO: 检测到'画图'关键词，启动绘图流程。")  # wh_add_draw
            db_data_context = ""  # wh_add_draw
            print("INFO: 绘图任务，尝试从数据库获取相关数据...")  # wh_add_draw
            sql = self.db_agent.generate_sql(question)  # wh_add_draw
            if sql:  # wh_add_draw
                plot_data = self.db_agent.get_data_for_plotting(sql)  # wh_add_draw
                if plot_data:  # wh_add_draw
                    db_data_context = json.dumps(plot_data, ensure_ascii=False, indent=2)  # wh_add_draw
                    print(f"INFO: 成功获取数据上下文用于绘图:\n{db_data_context[:300]}...")  # wh_add_draw
                else:  # wh_add_draw
                    print("WARN: 未能从数据库获取用于绘图的数据。将依赖LLM生成示例数据。")  # wh_add_draw
            else:  # wh_add_draw
                print("WARN: 未能生成SQL来获取绘图数据。将依赖LLM生成示例数据。")  # wh_add_draw
            plot_result = self.drawing_agent.draw(question, db_data_context)  # wh_add_draw
            return {  # wh_add_draw
                "answer": plot_result,  # wh_add_draw
                "knowledge_context": "",  # wh_add_draw
                "db_result": db_data_context,  # wh_add_draw
                "source_type": "drawing_agent",  # wh_add_draw
                "confidence": 0.95,  # wh_add_draw
                "agent_decision": {  # wh_add_draw
                    "primary_agent": "drawing",  # wh_add_draw
                    "reasoning": "用户输入以'画图'开头，直接触发。",  # wh_add_draw
                    "requires_database": True,  # wh_add_draw
                    "requires_knowledge_base": False,  # wh_add_draw
                    "requires_drawing": True  # wh_add_draw
                },  # wh_add_draw
                "semantic_results": [],  # wh_add_draw
                "plot_path": plot_result if "成功" in plot_result else None  # wh_add_draw
            }  # wh_add_draw

        # 1. 语义检索增强
        enhanced_question = self._enhance_query_with_semantic_context(question)
        semantic_results = self._knn_semantic_search(question, k=3)
        # 检查最高相关性
        max_similarity = max([r['similarity'] for r in semantic_results], default=0)
        if max_similarity < 0.3:
            # 相关性低，直接由大模型回答
            llm_prompt = PromptTemplate.from_template("""
你是智能仓储系统的专家，请直接、专业地回答下列用户问题：

用户问题：{question}

请用结构化、简明的方式作答。
""")
            answer = self.llm.invoke(llm_prompt.format(question=question)).content.strip()
            return {
                "answer": answer,
                "knowledge_context": "",
                "db_result": "",
                "source_type": "llm_fallback",
                "confidence": 0.7,
                "agent_decision": {
                    "primary_agent": "llm_fallback",
                    "reasoning": "语义相关性低，直接由大模型回答",
                    "requires_database": False,
                    "requires_knowledge_base": False
                },
                "semantic_results": semantic_results
            }

        # 2. 分析查询意图
        try:
            intent = self.analyze_query_intent(enhanced_question, context)
        except Exception as e:
            intent = None
        # 如果意图分析失败或返回空/无效，直接由LLM回答
        if not intent or not isinstance(intent, dict) or not intent.get('primary_agent'):
            llm_prompt = PromptTemplate.from_template("""
你是智能仓储系统的专家，请直接、专业地回答下列用户问题：

用户问题：{question}

请用结构化、简明的方式作答。
""")
            answer = self.llm.invoke(llm_prompt.format(question=question)).content.strip()
            return {
                "answer": answer,
                "knowledge_context": "",
                "db_result": "",
                "source_type": "llm_fallback",
                "confidence": 0.7,
                "agent_decision": {
                    "primary_agent": "llm_fallback",
                    "reasoning": "意图分析失败或无效，直接由大模型回答",
                    "requires_database": False,
                    "requires_knowledge_base": False
                },
                "semantic_results": semantic_results
            }

        # 3. 根据意图调用相应Agent
        results = {}

        if intent.get("requires_knowledge_base", True):
            try:
                docs = self.kb.vectorstore.similarity_search(question, k=5)
                results["knowledge_context"] = self._format_knowledge_context(docs)
            except Exception as e:
                results["knowledge_context"] = f"知识库检索失败: {e}"

        if intent.get("requires_database", True):
            try:
                results["db_result"] = self.db_agent.query(question, context)
            except Exception as e:
                results["db_result"] = f"数据库查询失败: {e}"

        # 4. 生成综合回答
        final_answer = self._generate_comprehensive_answer(question, results, intent)

        return {
            "answer": final_answer,
            "knowledge_context": results.get("knowledge_context", ""),
            "db_result": results.get("db_result", ""),
            "source_type": "top_agent_coordinated",
            "confidence": 0.9,
            "agent_decision": intent,
            "semantic_results": semantic_results
        }

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

            formatted_contexts.append(f"知识片段{i + 1}: {content}")

        return "\n".join(formatted_contexts)

    def _generate_comprehensive_answer(self, question: str, results: Dict, intent: Dict) -> str:
        """生成综合回答"""
        try:
            synthesis_prompt = PromptTemplate.from_template("""
作为智能仓储系统的中枢大脑，请基于以下信息生成专业、结构化的综合回答：

用户问题：{question}
Agent决策：{intent_reasoning}

【知识库信息】
{knowledge_context}

【数据库分析】
{db_result}

请提供：
1. 直接回答用户问题
2. 基于多源信息的综合分析
3. 如果有上下文关联，请体现连续性
4. 回答要简洁、专业、结构化

综合回答：
""")

            response = self.llm.invoke(synthesis_prompt.format(
                question=question,
                intent_reasoning=intent.get("reasoning", ""),
                knowledge_context=results.get("knowledge_context", "无相关信息"),
                db_result=results.get("db_result", "无数据库结果")
            ))

            return response.content.strip()

        except Exception as e:
            return f"综合回答生成失败: {str(e)}"


class AgenticRAGSystem:
    def __init__(self):
        self.kb = InMemoryKnowledgeBase()
        self.kb.load_from_sqlite()  # 从SQLite加载知识
        self.kb.build_vectorstore()
        self.db_agent = UniversalDatabaseAgent()  # 使用通用数据库Agent
        self.memory_agent = MemoryAgent()  # 添加记忆Agent
        self.drawing_agent = DrawingAgent()  # wh_add_draw
        self.top_agent = TopAgent(self.memory_agent, self.db_agent, self.kb, self.drawing_agent)  # wh_add_draw
        self.llm = ChatOpenAI(
            model_name=os.getenv("MODEL_NAME"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_api_base=os.getenv("OPENAI_API_URL"),
            temperature=0.3
        )

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
        self.memory_agent.clear_memory()  # 清理记忆


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


def display_result(result: Dict):
    """格式化显示结果"""
    print("\n" + "=" * 50)
    print("📝 智能结构化回答")
    print("=" * 50)
    print(result.get('answer', '无回答'))

    if result.get("plot_path"):  # wh_add_draw
        print("✅ 图像已尝试在窗口中显示，并已保存到本地。")  # wh_add_draw
    # 置信度和相关性
    if 'confidence' in result:
        print(f"\n🎯 置信度: {result['confidence']:.1%}")
    if 'relevance_score' in result:
        print(f"📊 知识库匹配度: {result['relevance_score']:.1%}")

    # 语义检索结果
    if 'semantic_results' in result and result['semantic_results']:
        print("\n🔍 语义相似度检索")
        print("-" * 20)
        for i, semantic_result in enumerate(result['semantic_results'][:3]):
            candidate = semantic_result['candidate']
            similarity = semantic_result['similarity']
            if similarity > 0.3:  # 只显示相似度较高的结果
                print(f"相关任务{i + 1}: {candidate['task']} - {candidate['text']}")
                print(f"相似度: {similarity:.3f}")

    # Agent决策信息
    if 'agent_decision' in result:
        print("\n🤖 Agent决策分析")
        print("-" * 20)
        decision = result['agent_decision']
        print(f"主要Agent: {decision.get('primary_agent', 'unknown')}")
        print(f"分析理由: {decision.get('reasoning', '无')}")
        print(f"数据库查询: {'✅' if decision.get('requires_database') else '❌'}")
        print(f"知识库检索: {'✅' if decision.get('requires_knowledge_base') else '❌'}")

    # 信息来源
    print("\n📋 信息来源")
    print("-" * 20)
    source_type = result.get('source_type', 'unknown')
    if source_type == "drawing_agent":  # wh_add_draw
        print("🎨 绘图Agent")  # wh_add_draw
    elif source_type == "top_agent_coordinated":
        print("🧠 TopAgent协调系统")
    elif source_type == "knowledge_base":
        print("✅ 知识库直接匹配")
    elif source_type == "agent_system":
        print("🤖 多Agent协调系统")
    elif source_type == "llm_fallback":
        print("⚠️ LLM直接生成")
    else:
        print("❓ 未知来源")

    # 详细上下文（可选）
    if 'knowledge_context' in result and result['knowledge_context']:
        print("\n🧠 知识库片段:")
        print(result['knowledge_context'])
    if 'db_result' in result and result['db_result']:
        print("\n💾 数据库分析:")
        print(result['db_result'])


def main():
    print("🚀 === 智能多Agent RAG仓库管理系统（SQLite版） ===")
    print("💡 请输入您的查询：")
    print("🔚 输入'退出'、'quit'、'exit'或'q'结束会话")
    print("🧹 输入'clear'清空对话记忆\n")

    rag = AgenticRAGSystem()
    try:
        while True:
            query = input("\n🤔 请输入您的查询> ").strip()
            if not query:
                continue
            if query.lower() in ['quit', 'exit', '退出', 'q']:
                print("🧹 正在清空对话记忆...")
                rag.memory_agent.clear_memory()
                print("✅ 对话记忆已清空")
                break
            if query.lower() == 'clear':
                rag.memory_agent.clear_memory()
                print("🧹 对话记忆已清空")
                continue
            result = rag.process_query(query)
            display_result(result)
    finally:
        rag.close()
        print("\n👋 系统已关闭")


# 命令行交互
if __name__ == "__main__":
    main()