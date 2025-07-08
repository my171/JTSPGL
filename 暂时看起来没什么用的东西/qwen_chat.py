import os
import sys
from openai import OpenAI


def main():
    # 初始化客户端
    client = OpenAI(
        api_key="sk-9b72700e16234e9fa4a42bf949fe8327",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )

    # 创建对话历史
    conversation_history = [
        {"role": "system", "content": "你是一个有用的人工智能助手，请用中文回答用户问题。"}
    ]

    print("千问模型命令行对话工具 (输入 'exit' 退出)")
    print("=" * 50)

    while True:
        try:
            # 获取用户输入
            user_input = input("\nYou: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['exit', 'quit']:
                print("对话结束。")
                break

            # 添加用户消息到历史
            conversation_history.append({"role": "user", "content": user_input})

            # 调用API获取回复
            response = client.chat.completions.create(
                model="qwen-vl-plus",
                messages=conversation_history,
                stream=False
            )

            # 获取AI回复
            ai_response = response.choices[0].message.content.strip()

            # 添加AI回复到历史
            conversation_history.append({"role": "assistant", "content": ai_response})

            # 打印回复
            print(f"\nAssistant: {ai_response}")

        except KeyboardInterrupt:
            print("\n\n对话被用户中断。")
            break
        except Exception as e:
            print(f"\n发生错误: {str(e)}")
            print("请重新输入您的问题...")


if __name__ == "__main__":
    main()