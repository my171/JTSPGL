from API_TextToText.API_of_RAG._2_AgenticRAGSystem import AgenticRAGSystem
from typing import Dict

RAG_DEBUG = True

def entryFunc():
    print("🚀 === 智能多Agent RAG仓库管理系统 ===")
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
            # 只在调试模式下显示SQL相关日志
            # result = rag.process_query(query)
            if RAG_DEBUG:
                result = rag.process_query(query)
            else:
                # 临时屏蔽SQL相关print
                import sys
                class DummyFile:
                    def write(self, x): pass
                old_stdout = sys.stdout
                sys.stdout = DummyFile()
                result = rag.process_query(query)
                sys.stdout = old_stdout
            display_result(result)
    finally:
        rag.close()
        print("\n👋 系统已关闭")

def display_result(result: Dict):
    """格式化显示结果（不显示数据库状态、Agent决策分析、信息来源和SQL相关内容）"""
    print("\n" + "="*50)
    print("📝 智能结构化回答")
    print("="*50)
    print(result.get('answer', '无回答'))
    
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
                print(f"相关任务{i+1}: {candidate['task']} - {candidate['text']}")
                print(f"相似度: {similarity:.3f}")
                
    # 详细上下文（可选）
    if 'knowledge_context' in result and result['knowledge_context']:
        print("\n🧠 知识库片段:")
        print(result['knowledge_context'])
    if 'db_result' in result and result['db_result']:
        print("\n💾 数据库分析:")
        print(result['db_result'])
    if 'pdf_result' in result and result['pdf_result']:
        print("\n📄 PDF检索:")
        print(result['pdf_result'])


Global_RAG = AgenticRAGSystem()

def API_RAG_TextGen(inputText) -> str:
    """输入问题，返回字符串回答"""


    if inputText.lower() == 'clear':
        Global_RAG.memory_agent.clear_memory()
        return "对话记忆已清空"
    # 只在调试模式下显示SQL相关日志
    # result = rag.process_query(inputText)
    
    result = Global_RAG.process_query(inputText)
    '''
    if RAG_DEBUG:
        result = rag.process_query(inputText)
    else:
        # 临时屏蔽SQL相关print
        import sys
        class DummyFile:
            def write(self, x): pass
        old_stdout = sys.stdout
        sys.stdout = DummyFile()
        result = rag.process_query(inputText)
        sys.stdout = old_stdout
    '''
    return format_result(result)

def format_result(result: Dict) -> str:
    """将模型获取的回答转换为字符串格式"""
    resultString = "\n" + "="*50 + "\n"
    resultString += "智能结构化回答" + "\n"
    resultString += "="*50 + "\n"
    resultString += result.get('answer', '无回答') + "\n"
    
    # 置信度和相关性
    if 'confidence' in result:
        resultString += f"\n🎯 置信度: {result['confidence']:.1%}" + "\n"
    if 'relevance_score' in result:
        resultString += f"📊 知识库匹配度: {result['relevance_score']:.1%}" + "\n"
    
    # 语义检索结果
    if 'semantic_results' in result and result['semantic_results']:
        resultString += "\n🔍 语义相似度检索" + "\n"
        resultString += "-" * 20 + "\n"
        for i, semantic_result in enumerate(result['semantic_results'][:3]):
            candidate = semantic_result['candidate']
            similarity = semantic_result['similarity']
            if similarity > 0.3:  # 只显示相似度较高的结果
                resultString += f"相关任务{i+1}: {candidate['task']} - {candidate['text']}" + "\n"
                resultString += f"相似度: {similarity:.3f}" + "\n"
                
    # 详细上下文（可选）
    if 'knowledge_context' in result and result['knowledge_context']:
        resultString += "\n🧠 知识库片段:" + "\n"
        resultString += result['knowledge_context'] + "\n"
    if 'db_result' in result and result['db_result']:
        resultString += "\n💾 数据库分析:" + "\n"
        resultString += result['db_result'] + "\n"
    if 'pdf_result' in result and result['pdf_result']:
        resultString += "\n📄 PDF检索:" + "\n"
        resultString += result['pdf_result'] + "\n"

if __name__ == '__main__':
    print(API_RAG_TextGen("仓库里有哪些华为产品"))