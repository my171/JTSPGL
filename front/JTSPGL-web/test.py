from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 示例处理函数 - 反转文本并统计字符
def process_text(input_text):
    # 在这里添加你的自定义处理逻辑
    reversed_text = input_text[::-1]
    char_count = len(input_text)
    word_count = len(input_text.split())
    
    return f"""原始文本: {input_text}
反转结果: {reversed_text}
字符统计: {char_count} 个字符
词语统计: {word_count} 个词语"""

@app.route('/process', methods=['POST'])
def process():
    try:
        data = request.get_json()
        input_text = data.get('text', '')
        
        if not input_text:
            return jsonify({'error': '输入文本为空'}), 400
        
        result = process_text(input_text)
        return jsonify({'result': result})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
