"""
Factory function to create the Strands Data Pipeline Agent

This module provides a simple way to create and configure the agent
without requiring the full Strands SDK for testing and development.
"""

from typing import List, Callable, Optional
from agents.strands_data_pipeline_agent import StrandsDataPipelineAgent


def create_agent(
    tools: Optional[List[Callable]] = None,
    model_id: Optional[str] = None,
    system_prompt: Optional[str] = None,
) -> StrandsDataPipelineAgent:
    """
    Factory function to create the Strands Data Pipeline Agent

    Args:
        tools: List of tool functions (optional)
        model_id: Model ID for the LLM (optional)
        system_prompt: System prompt for the agent (optional)

    Returns:
        Configured StrandsDataPipelineAgent instance
    """

    # Default system prompt in Japanese
    default_system_prompt = """あなたは、グローバルなデータ収集と処理を行うStrandsデータパイプラインエージェントです。以下の手順でデータ処理をサポートしてください：

1. まずユーザーの要求に応じて、ニュース、天気、ウェブデータの収集を行います
2. 収集したデータの検証と標準化フォーマットへの変換を実行します
3. データをカテゴリ別に分類し、適切なストレージ（データベース、S3）に保存します
4. オプション機能として、フェイクニュースフィルタリングや感情分析を実行できます
5. 保存されたデータに対してRAG（検索拡張生成）を使用した自然言語クエリが可能です

各ツールの実行結果をユーザーに分かりやすく伝え、データパイプラインの状況を詳細に報告してください。
エラーが発生した場合は、適切なエラーハンドリングを行い、代替手段を提案してください。"""

    return StrandsDataPipelineAgent(
        tools=tools or [],
        model_id=model_id or "anthropic.claude-3-haiku-20240307-v1:0",
        system_prompt=system_prompt or default_system_prompt,
    )


def create_agent_with_mock_tools() -> StrandsDataPipelineAgent:
    """
    Create agent with mock tool functions for testing

    Returns:
        StrandsDataPipelineAgent with mock tools
    """

    def mock_collect_news_data(countries, category="general"):
        return {"success": False, "message": "Mock tool - not implemented"}

    def mock_collect_weather_data(countries, cities=None):
        return {"success": False, "message": "Mock tool - not implemented"}

    def mock_validate_data(data, schema_type):
        return {"success": False, "message": "Mock tool - not implemented"}

    mock_tools = [mock_collect_news_data, mock_collect_weather_data, mock_validate_data]

    return create_agent(tools=mock_tools)


if __name__ == "__main__":
    # Test the factory function
    print("Testing agent creation...")

    # Test basic agent creation
    agent = create_agent()
    print(f"✓ Created agent: {agent.agent_name}")
    print(f"✓ Tools available: {len(agent.tools)}")

    # Test agent with mock tools
    agent_with_tools = create_agent_with_mock_tools()
    print(f"✓ Created agent with mock tools: {len(agent_with_tools.tools)} tools")

    # Test agent response
    response = agent("データパイプラインの状態を教えてください")
    print(f"✓ Agent response success: {response.success}")
    print(f"✓ Agent message: {response.message}")

    print("\n✅ Agent factory function working correctly!")
