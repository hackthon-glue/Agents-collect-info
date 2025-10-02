import os
from bedrock_agentcore.runtime import BedrockAgentCoreApp, RequestContext
from dotenv import load_dotenv
from strands import Agent

# --- 依存関係をインポート ---
from tools import *  # All tools with @tool decorator

# .envファイルをロード
load_dotenv()

# --- 設定 ---
MODEL_ID = os.getenv("AGENT_MODEL_ID", "amazon.nova-premier-v1:0")
SYSTEM_PROMPT = """You are a Data Pipeline Agent that performs global data collection and processing. Support data processing with the following steps:

1. Collect news, weather, and other web data based on user requests
2. Validate collected data and convert to standardized format
3. Apply fake news filtering before storing data when enabled
4. Store standardized data in Aurora database according to table definitions, and save to S3 with metadata as RAG datasource

Communicate tool execution results clearly to users and provide detailed reports on data pipeline status.
When errors occur, handle them appropriately and suggest alternative approaches."""

# --- エージェント作成 ---
agent = Agent(
    model=MODEL_ID,
    system_prompt=SYSTEM_PROMPT,
    tools=[
        collect_news_data,
        collect_weather_data,
        collect_web_data,
        validate_data,
        format_data,
        store_in_database,
        store_in_s3,
        filter_fake_news,
        filter_fake_news_batch,
        analyze_sentiment,
        query_rag,
        trigger_knowledge_base_sync,
        get_knowledge_base_sync_status,
    ],
)

# --- AgentCore統合 ---
app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload, context: RequestContext):
    """AgentCore entrypoint"""
    prompt = payload.get("prompt", "prompt is not found")
    result = agent(prompt)
    return {"result": result.message}


# --- 直接実行用 ---
def main():
    """Direct execution for testing"""
    while True:
        try:
            user_input = input("\n> ")
            if user_input.lower() in ["quit", "exit", "q"]:
                break
            result = agent(user_input)
            print(f"\n{result.message}")
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        main()
    else:
        app.run()
