import os
from bedrock_agentcore.runtime import BedrockAgentCoreApp, RequestContext
from dotenv import load_dotenv

# --- 依存関係をインポート ---
from agents.strands_data_pipeline_agent import StrandsDataPipelineAgent
from tools import (
    collect_news_data,
    collect_weather_data,
    collect_web_data,
    validate_data,
    format_data,
    categorize_data,
    store_in_database,
    store_in_s3,
    filter_fake_news,
    analyze_sentiment,
    query_rag,
)

# .envファイルをロード (ローカル開発用)
load_dotenv()

# --- 依存関係の組み立て (Dependency Injection) ---
# 1. エージェントが使用するツールをリストにまとめる
TOOL_KIT = [
    collect_news_data,
    collect_weather_data,
    collect_web_data,
    validate_data,
    format_data,
    categorize_data,
    store_in_database,
    store_in_s3,
    filter_fake_news,
    analyze_sentiment,
    query_rag,
]

# 2. エージェントの設定
MODEL_ID = os.getenv("AGENT_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
SYSTEM_PROMPT = """あなたは、グローバルなデータ収集と処理を行うStrandsデータパイプラインエージェントです。以下の手順でデータ処理をサポートしてください：

1. まずユーザーの要求に応じて、ニュース、天気、ウェブデータの収集を行います
2. 収集したデータの検証と標準化フォーマットへの変換を実行します
3. データをカテゴリ別に分類し、適切なストレージ（データベース、S3）に保存します
4. オプション機能として、フェイクニュースフィルタリングや感情分析を実行できます
5. 保存されたデータに対してRAG（検索拡張生成）を使用した自然言語クエリが可能です

各ツールの実行結果をユーザーに分かりやすく伝え、データパイプラインの状況を詳細に報告してください。
エラーが発生した場合は、適切なエラーハンドリングを行い、代替手段を提案してください。"""

# 3. AgentCore アプリケーションを作成
app = BedrockAgentCoreApp()

# 4. エージェントのインスタンスを生成し、ツールを注入する
agent = StrandsDataPipelineAgent(
    tools=TOOL_KIT,
    model_id=MODEL_ID,
    system_prompt=SYSTEM_PROMPT,
)


# 5. エージェントを呼び出すエントリポイント関数を指定
@app.entrypoint
def invoke(payload, context: RequestContext):
    """Handler for agent invocation"""
    user_message = payload.get(
        "prompt",
        "プロンプトが見つかりません。promptキーを含むJSONペイロードを作成してください。",
    )

    result = agent(user_message)
    return {"result": result.message}


if __name__ == "__main__":
    app.run()
