"""
StrandsDataPipelineAgent - Main agent class for orchestrating data collection and processing pipeline
"""

import logging
from typing import Any, Dict, List, Optional
from strands import Agent

logger = logging.getLogger(__name__)


class StrandsDataPipelineAgent(Agent):
    """
    Main agent class that orchestrates the complete data pipeline:
    1. Data collection from multiple sources
    2. Data validation and formatting
    3. Storage in database and S3
    4. Optional fake news filtering
    5. RAG query functionality
    """

    def __init__(self, tools: List, model_id: str, system_prompt: str):
        """Initialize the agent with tools and configuration"""
        super().__init__(tools=tools, model_id=model_id, system_prompt=system_prompt)

    def execute_data_pipeline(
        self,
        countries: List[str],
        data_sources: List[str] = None,
        categories: List[str] = None,
        urls: List[str] = None,
        enable_fake_news_filter: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute complete data pipeline for specified countries and sources

        Args:
            countries: List of country codes to collect data for
            data_sources: List of data sources ('news', 'weather', 'web')
            categories: List of news categories for news collection
            urls: List of URLs for web scraping
            enable_fake_news_filter: Whether to apply fake news filtering

        Returns:
            Dictionary containing pipeline execution results
        """
        try:
            if data_sources is None:
                data_sources = ["news", "weather"]
            if categories is None:
                categories = ["general"]

            pipeline_results = {
                "success": True,
                "countries": countries,
                "data_sources": data_sources,
                "collection_results": {},
                "processing_results": {},
                "storage_results": {},
                "errors": [],
            }

            # Step 1: Data Collection
            collected_data = {}

            if "news" in data_sources:
                for category in categories:
                    try:
                        result = self.tools_map["collect_news_data"](
                            countries, category
                        )
                        if result.get("success"):
                            collected_data.setdefault("news", []).extend(
                                result.get("data", [])
                            )
                        pipeline_results["collection_results"][
                            f"news_{category}"
                        ] = result
                    except Exception as e:
                        error_msg = (
                            f"News collection failed for category {category}: {str(e)}"
                        )
                        pipeline_results["errors"].append(error_msg)
                        logger.error(error_msg)

            if "weather" in data_sources:
                try:
                    result = self.tools_map["collect_weather_data"](countries)
                    if result.get("success"):
                        collected_data["weather"] = result.get("data", [])
                    pipeline_results["collection_results"]["weather"] = result
                except Exception as e:
                    error_msg = f"Weather collection failed: {str(e)}"
                    pipeline_results["errors"].append(error_msg)
                    logger.error(error_msg)

            if "web" in data_sources and urls:
                try:
                    result = self.tools_map["collect_web_data"](urls, "blog")
                    if result.get("success"):
                        collected_data["web"] = result.get("data", [])
                    pipeline_results["collection_results"]["web"] = result
                except Exception as e:
                    error_msg = f"Web collection failed: {str(e)}"
                    pipeline_results["errors"].append(error_msg)
                    logger.error(error_msg)

            # Step 2: Data Processing
            processed_data = {}

            for data_type, data_list in collected_data.items():
                if not data_list:
                    continue

                try:
                    # Validation
                    validation_result = self.tools_map["validate_data"](
                        data_list, data_type
                    )
                    pipeline_results["processing_results"][
                        f"{data_type}_validation"
                    ] = validation_result

                    if validation_result.get("success"):
                        # Formatting
                        format_result = self.tools_map["format_data"](
                            data_list, data_type, countries[0] if countries else "us"
                        )
                        pipeline_results["processing_results"][
                            f"{data_type}_formatting"
                        ] = format_result

                        if format_result.get("success"):
                            processed_data[data_type] = format_result.get("data", [])

                except Exception as e:
                    error_msg = f"Processing failed for {data_type}: {str(e)}"
                    pipeline_results["errors"].append(error_msg)
                    logger.error(error_msg)

            # Step 3: Storage
            if processed_data:
                try:
                    # Database storage
                    db_result = self.tools_map["store_in_database"](processed_data)
                    pipeline_results["storage_results"]["database"] = db_result

                    # S3 storage
                    all_data = []
                    for data_list in processed_data.values():
                        all_data.extend(data_list)

                    if all_data:
                        s3_result = self.tools_map["store_in_s3"](all_data)
                        pipeline_results["storage_results"]["s3"] = s3_result

                except Exception as e:
                    error_msg = f"Storage failed: {str(e)}"
                    pipeline_results["errors"].append(error_msg)
                    logger.error(error_msg)

            # Set overall success based on errors
            pipeline_results["success"] = len(pipeline_results["errors"]) == 0

            return pipeline_results

        except Exception as e:
            logger.error(f"Pipeline execution failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "countries": countries,
                "data_sources": data_sources,
            }

    def query_data(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """
        Query stored data using RAG functionality

        Args:
            query: Natural language query
            max_results: Maximum number of results to return

        Returns:
            Dictionary containing query results and generated response
        """
        try:
            result = self.tools_map["query_rag"](query, max_results)
            return result

        except Exception as e:
            logger.error(f"RAG query failed: {str(e)}")
            return {"success": False, "error": str(e), "query": query}

    @property
    def tools_map(self) -> Dict[str, Any]:
        """Create a mapping of tool names to tool functions for easy access"""
        if not hasattr(self, "_tools_map"):
            self._tools_map = {}
            for tool in self.tools:
                if hasattr(tool, "__name__"):
                    self._tools_map[tool.__name__] = tool
        return self._tools_map
