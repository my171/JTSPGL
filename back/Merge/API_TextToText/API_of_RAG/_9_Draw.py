# import psycopg2
# import fitz
# import json
# import os#运行需要1分钟左右，回答15-30秒左右
# import numpy as np
# from typing import List, Dict, Tuple, Optional
# from fastapi import FastAPI, Request
# from pydantic import BaseModel
# from langchain_openai import ChatOpenAI
# from langchain_huggingface import HuggingFaceEmbeddings
# from langchain_community.vectorstores import FAISS
# from langchain.schema import Document
# from langchain.text_splitter import RecursiveCharacterTextSplitter
# from langchain.prompts import PromptTemplate
# from fastapi.responses import JSONResponse
# from contextlib import asynccontextmanager
# from collections import deque
# import re
# import textwrap
# import subprocess  # 添加绘图功能
# import sys  # 添加绘图功能
# import time  # 添加绘图功能
# from back.Merge._1_Entry import Global_RAG

# class DrawingAgent:
#     """绘图Agent - 负责生成并执行绘图代码"""
    
#     def __init__(self):
#         self.llm = ChatOpenAI(
#             model_name=os.getenv("MODEL_NAME", "gpt-4.1"),
#             openai_api_key=os.getenv("OPENAI_API_KEY"),
#             openai_api_base=os.getenv("OPENAI_API_URL"),
#             temperature=0.4
#         )
    
#     def _extract_code(self, text: str) -> str:
#         """从文本中提取Python代码块"""
#         if '```python' in text:
#             start = text.find('```python') + len('```python')
#             end = text.find('```', start)
#             return text[start:end].strip()
#         elif '```' in text:
#             start = text.find('```') + 3
#             end = text.find('```', start)
#             return text[start:end].strip()
#         return text
    
#     def draw(self, question: str, data_context: str = "") -> str:
#         """根据问题和数据上下文生成并执行绘图代码"""
#         timestamp = int(time.time())
#         plot_filename = f"plot_{timestamp}.png"
#         plot_context = ""
#         if data_context:
#             plot_context = f"""
# Please use the following JSON data for plotting, do not fabricate data:
# --- DATA START ---
# {data_context}
# --- DATA END ---
# """
#         plot_prompt_template = PromptTemplate.from_template("""
# You are a data visualization expert. Please generate complete Python code to create charts based on the user's question and provided data.

# {plot_context}

# User Question: {question}

# Code Requirements:
# 1. Use `matplotlib.pyplot` library and alias it as `plt`.
# 2. **Before calling `plt.show()`, you must save the chart to a file named '{plot_filename}'.**
# 3. **Finally, you must call `plt.show()` to display the image.**
# 4. The code must be complete and directly runnable.
# 5. Use English for chart labels and titles to avoid encoding issues.
# 6. If JSON data is provided, parse it and use the actual data. If no data provided, create reasonable sample data.
# 7. Add appropriate title and axis labels to the chart.
# 8. Add a note at the bottom center: 'Note: Data is for reference only.'
# 9. For database data, focus on meaningful visualizations like bar charts, pie charts, or line charts.
# 10. Only return Python code block wrapped in ```python ... ```, no additional explanations.

# Data Processing Tips:
# - If JSON data is provided, use `json.loads()` to parse it
# - Handle potential encoding issues with Chinese characters
# - Choose appropriate chart types based on data structure
# - For numerical data, consider bar charts or line charts
# - For categorical data, consider pie charts or bar charts
# """)
#         final_prompt = plot_prompt_template.format(question=question, plot_context=plot_context,
#                                                    plot_filename=plot_filename)
#         attempt = 0
#         max_attempts = 5
#         conversation = [{"role": "system",
#                          "content": "You are a helpful AI assistant that generates Python code for plotting graphs using matplotlib."}]
#         conversation.append({"role": "user", "content": final_prompt})
#         while attempt < max_attempts:
#             attempt += 1
#             print(f"\n[绘图尝试 {attempt}/{max_attempts}] 正在向LLM请求绘图代码...")
#             response = self.llm.invoke(conversation)
#             ai_response = response.content.strip()
#             code = self._extract_code(ai_response)
#             if not code:
#                 print(f"❌ 绘图失败: LLM未返回有效的代码。")
#                 conversation.append({"role": "assistant", "content": ai_response})
#                 conversation.append(
#                     {"role": "user", "content": "You did not return any code. Please only return code blocks wrapped in ```python."})
#                 continue

#             # 清理代码，移除可能的问题代码
#             code = code.replace("matplotlib.use('Agg')", "")
#             code = code.replace("plt.show()", "")
#             code = re.sub(r"plt\.savefig\s*\(['\"].*?['\"]\)", "", code, flags=re.DOTALL)
            
#             # 添加系统控制的保存和显示命令
#             code += f"\n\n# Adding save and show commands by the system #wh_add_draw\n"
#             code += f"plt.savefig('{plot_filename}', dpi=300, bbox_inches='tight') #wh_add_draw\n"
#             code += f"plt.show() #wh_add_draw\n"

#             script_name = f"temp_plot_{timestamp}_{attempt}.py"
#             with open(script_name, "w", encoding="utf-8") as f:
#                 f.write(code)
#             try:
#                 # 修复Windows编码问题
#                 result = subprocess.run(
#                     [sys.executable, script_name],
#                     capture_output=True,
#                     text=True,
#                     encoding='utf-8',  # 明确指定UTF-8编码
#                     timeout=30,
#                     env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}  # 设置Python IO编码
#                 )
#                 if result.returncode == 0 and os.path.exists(plot_filename):
#                     print(f"✅ 绘图成功! 图像已保存到: {os.path.abspath(plot_filename)}")
#                     os.remove(script_name)
#                     return f"绘图成功，文件保存在: {os.path.abspath(plot_filename)}"
#                 else:
#                     error_msg = f"代码执行失败或未生成图像文件。\nReturn Code: {result.returncode}\nStderr: {result.stderr}"
#                     print(f"❌ {error_msg}")
#                     conversation.append({"role": "assistant", "content": ai_response})
#                     feedback = f"Your generated code execution failed, error message: {error_msg}. Please fix it and regenerate complete code."
#                     conversation.append({"role": "user", "content": feedback})
#             except subprocess.TimeoutExpired:
#                 error_msg = "Execution timeout: Plotting code ran too long."
#                 print(f"❌ {error_msg}")
#                 conversation.append({"role": "assistant", "content": ai_response})
#                 conversation.append(
#                     {"role": "user", "content": f"Your generated code execution timed out. Please optimize the code to run faster."})
#             except Exception as e:
#                 error_msg = f"Execution exception: {str(e)}"
#                 print(f"❌ {error_msg}")
#                 os.remove(script_name)
#                 return f"绘图时发生未知错误: {error_msg}"
#             finally:
#                 if os.path.exists(script_name):
#                     os.remove(script_name)
#         return f"⚠️ 经过 {max_attempts} 次尝试，仍然无法成功生成图像。"



# def _generate_data_summary_for_plot(self, plot_data: List[Dict], question: str) -> str:
#         """为绘图生成数据摘要"""
#         try:
#             if not plot_data:
#                 return ""
            
#             # 分析数据结构
#             sample_record = plot_data[0]
#             columns = list(sample_record.keys())
            
#             # 生成摘要
#             summary_parts = []
#             summary_parts.append(f"📊 数据概览：基于 {len(plot_data)} 条记录")
            
#             # 识别关键字段
#             numeric_fields = []
#             categorical_fields = []
            
#             for field in columns:
#                 if field in ['quantity', 'total_amount', 'unit_price', 'cost_price', 'stock_quantity', 'safety_stock']:
#                     numeric_fields.append(field)
#                 elif field in ['product_name', 'category', 'warehouse_name', 'store_name']:
#                     categorical_fields.append(field)
            
#             # 添加数值字段统计
#             if numeric_fields:
#                 for field in numeric_fields[:3]:  # 最多显示3个数值字段
#                     try:
#                         values = [float(record[field]) for record in plot_data if record[field] is not None]
#                         if values:
#                             total = sum(values)
#                             avg = total / len(values)
#                             summary_parts.append(f"• {field}: 总计 {total:,.2f}, 平均 {avg:.2f}")
#                     except:
#                         continue
            
#             # 添加分类字段统计
#             if categorical_fields:
#                 for field in categorical_fields[:2]:  # 最多显示2个分类字段
#                     try:
#                         unique_values = set(record[field] for record in plot_data if record[field] is not None)
#                         if unique_values:
#                             summary_parts.append(f"• {field}: {len(unique_values)} 个不同值")
#                     except:
#                         continue
            
#             return "\n".join(summary_parts)
            
#         except Exception as e:
#             return f"数据摘要生成失败: {str(e)}"

# def process_draw_input(query: str) -> str:
#     """专门处理画图请求，结合数据库数据，返回图片路径或错误信息"""
#     try:
#         # 1. 用数据库Agent生成SQL
#         sql = Global_RAG.db_agent.generate_sql(query)
#         plot_data = None
#         if sql:
#             plot_data = Global_RAG.db_agent.get_data_for_plotting(sql)
#         db_data_context = ''
#         if plot_data and len(plot_data) > 0:
#             import json
#             db_data_context = json.dumps(plot_data, ensure_ascii=False, indent=2)
#         # 2. 只用数据库数据作图
#         plot_result = Global_RAG.drawing_agent.draw(query, db_data_context)
#         if '成功' in plot_result and '文件保存在' in plot_result:
#             # 提取图片路径
#             import re
#             m = re.search(r'文件保存在: (.+)', plot_result)
#             if m:
#                 return m.group(1).strip()
#         return plot_result
#     except Exception as e:
#         return f"❌ 画图失败: {str(e)}"
