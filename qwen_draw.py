import os
import sys
import time
import subprocess
import re
from openai import OpenAI


def extract_code(text):
    """
    从文本中提取Python代码块
    """
    if '```python' in text:
        start = text.find('```python') + len('```python')
        end = text.find('```', start)
        return text[start:end].strip()
    elif '```' in text:
        start = text.find('```') + 3
        end = text.find('```', start)
        return text[start:end].strip()
    return text


def main():
    # 初始化客户端
    client = OpenAI(
        api_key="sk-9b72700e16234e9fa4a42bf949fe8327",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )

    # 创建对话历史
    conversation_history = [
        {"role": "system",
         "content": "你是一个有用的人工智能助手，请用中文回答用户问题。生成绘图代码时请确保代码语法正确，数据简洁有效，数据点数量匹配，并使用英文标签避免中文字体问题。"}
    ]

    print("千问模型命令行对话工具 (输入 'exit' 退出)")
    print("=" * 50)

    while True:
        try:
            # 获取用户输入
            user_input = input("\nYou: ").strip()
            original_input = user_input  # 保存原始输入
            plot_filename = None  # 存储绘图文件名

            if not user_input:
                continue

            if user_input.lower() in ['exit', 'quit']:
                print("对话结束。")
                break

            # 处理画图请求
            if user_input.startswith("画图"):
                # 生成唯一文件名
                timestamp = int(time.time())
                plot_filename = f"plot_{timestamp}.png"
                # 修改用户输入，添加绘图要求
                user_input = (
                    f"{user_input}\n"
                    "请生成完整的Python绘图代码，要求：\n"
                    "1. 使用matplotlib库绘图\n"
                    "2. 将图像保存到本地文件\n"
                    f"3. 保存文件名为'{plot_filename}'\n"
                    "4. 只返回代码，不要任何解释\n"
                    "5. 确保代码能直接运行\n"
                    "6. 不要使用plt.show()，只保存图像\n"
                    "7. 使用简洁有效的数据，确保数据点数量匹配\n"
                    "8. 添加详细的标题、坐标轴标签和单位说明（使用英文）\n"
                    "9. 包含数据来源说明（使用英文）\n"
                    "10. 使用真实可靠的数据，如果没有具体数据则使用示例数据\n"
                    "11. 在图表底部添加注释：'Note: Data may be simulated for demonstration purposes'"
                )

                # 添加用户消息到历史
                conversation_history.append({"role": "user", "content": user_input})

                # 尝试次数计数器
                attempt = 0
                max_attempts = 10
                success = False

                while attempt < max_attempts and not success:
                    attempt += 1

                    # 调用API获取回复
                    response = client.chat.completions.create(
                        model="qwen-vl-plus",
                        messages=conversation_history,
                        stream=False
                    )

                    # 获取AI回复
                    ai_response = response.choices[0].message.content.strip()

                    # 更新对话历史（只保留最后一次生成的代码）
                    if attempt > 1:
                        # 移除上一次的错误反馈和回复
                        conversation_history = conversation_history[:-2]

                    # 添加AI回复到历史
                    conversation_history.append({"role": "assistant", "content": ai_response})

                    # 提取代码
                    code = extract_code(ai_response)
                    print(f"\n[尝试 {attempt}/{max_attempts}] Assistant: 生成的绘图代码:\n{code}")

                    # 移除plt.show()调用（如果存在）
                    code = code.replace('plt.show()', '')

                    # 确保保存文件名正确
                    if f"'{plot_filename}'" not in code and f'"{plot_filename}"' not in code:
                        # 如果代码中没有正确的保存文件名，添加保存命令
                        if code.strip().endswith(')') and 'plt.savefig' not in code:
                            code += f"\nplt.savefig('{plot_filename}')"
                        elif 'plt.savefig' in code:
                            # 替换已有的保存命令
                            code = re.sub(r"plt\.savefig\(['\"].*?['\"]\)", f"plt.savefig('{plot_filename}')", code)

                    # 确保使用Agg后端
                    if "matplotlib.use('Agg')" not in code:
                        code = "import matplotlib\nmatplotlib.use('Agg')\n" + code

                    # 确保使用英文标签
                    if "plt.xlabel(" in code and "中文" in code:
                        code = code.replace("中文", "English")

                    # 确保添加数据说明注释
                    if "plt.figtext" not in code and "plt.text" not in code:
                        code = code.replace("plt.savefig(",
                                            "plt.figtext(0.5, 0.01, 'Note: Data may be simulated for demonstration purposes', ha='center', fontsize=10)\nplt.savefig(")

                    # 保存代码到临时文件
                    script_name = f"temp_plot_{timestamp}_{attempt}.py"
                    with open(script_name, "w", encoding="utf-8") as f:
                        f.write("import matplotlib.pyplot as plt\n")
                        f.write("import numpy as np\n")
                        f.write("import pandas as pd\n")
                        f.write("\n")
                        f.write(code)
                        f.write("\n")

                    # 执行绘图代码
                    print(f"正在执行绘图代码 (尝试 {attempt}/{max_attempts})...")
                    try:
                        result = subprocess.run(
                            [sys.executable, script_name],
                            capture_output=True,
                            text=True,
                            timeout=60
                        )

                        if result.returncode == 0:
                            if os.path.exists(plot_filename):
                                print(f"✅ 绘图成功! 图像已保存到: {os.path.abspath(plot_filename)}")
                                # 添加数据可能不准确的提醒
                                print("⚠️ 注意: 图表数据可能为模拟数据，仅供参考")
                                success = True
                                # 清理临时文件
                                try:
                                    os.remove(script_name)
                                except:
                                    pass
                                break
                            else:
                                error_msg = "❌ 绘图失败: 代码未生成图像文件"
                                print(error_msg)
                                if result.stderr:
                                    print(f"错误输出: {result.stderr}")
                        else:
                            error_msg = f"❌ 执行错误 (返回码: {result.returncode}):"
                            print(error_msg)
                            if result.stderr:
                                print(f"错误信息:\n{result.stderr}")
                                error_msg += f"\n错误信息:\n{result.stderr}"
                    except subprocess.TimeoutExpired:
                        error_msg = "❌ 执行超时: 绘图代码运行时间过长"
                        print(error_msg)
                    except Exception as e:
                        error_msg = f"❌ 执行异常: {str(e)}"
                        print(error_msg)
                    finally:
                        # 清理临时文件
                        try:
                            os.remove(script_name)
                        except:
                            pass

                    # 如果执行失败，准备反馈给AI
                    if not success and attempt < max_attempts:
                        feedback = (
                            f"上次生成的代码执行失败:\n"
                            f"错误信息: {error_msg}\n\n"
                            f"请修复以下代码中的问题:\n"
                            f"```python\n{code}\n```\n\n"
                            "请重新生成完整的绘图代码，确保修复所有问题。"
                        )
                        print(f"\n将错误反馈给AI进行修复 (尝试 {attempt + 1}/{max_attempts})...")
                        conversation_history.append({"role": "user", "content": feedback})

                if not success:
                    print(f"\n⚠️ 经过 {max_attempts} 次尝试，仍然无法成功生成图像。")
            else:
                # 非画图请求
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

                # 普通回复
                print(f"\nAssistant: {ai_response}")

        except KeyboardInterrupt:
            print("\n\n对话被用户中断。")
            break
        except Exception as e:
            print(f"\n发生错误: {str(e)}")
            print("请重新输入您的问题...")


if __name__ == "__main__":
    main()