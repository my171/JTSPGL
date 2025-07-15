'''
-->> RAG无法生效时的替代方案
-->> 藉此判断调用生成sql语句还是调用qwen画图功能
判断程序应当调用哪个智能体
'''
from httpx import ReadTimeout
from openai import OpenAI, APIConnectionError, APIError

# 初始化 OpenAI 客户端

client = OpenAI(api_key="sk-ubjkrzodjlihepttrgdmmqsxaulmoktrzvmvzzwpkaftmtcn", 
                base_url="https://api.siliconflow.cn/v1")

def GetJudge(requirement: str) -> str:
    prompt = (
        "公司领导向你提出了一个要求，你需要判断:1.是否需要进行数据库相关操作来获取相关数据 2.是否执行了查询语句 3.是否需要绘制图表\n"
        f"需求: {requirement}\n"
        "请通过以下格式回复 {\"1\": Y/N, \"2\": Y/N, \"3\": Y/N}，不需要额外的解释内容。"
    )
    #输出提示词
    backoff = 1.0
    try:
        resp = client.chat.completions.create(
            model="Qwen/Qwen2.5-72B-Instruct",
            messages=[
                {'role': 'user', 'content': prompt}
            ],
            timeout=300
        )
        content = resp.choices[0].message.content
        return extract_sql(content)
    except (APIConnectionError, APIError, ReadTimeout) as e:
        print(str(e))
        return 0