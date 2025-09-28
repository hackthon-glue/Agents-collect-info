"""
Strands Data Pipeline Agent - Main orchestrator for data collection and processing
Follows Single Responsibility Principle and Clean Architecture
"""

from typing import Dict, Any, List
import json
import logging
from datetime import datetime


class StrandsDataPipelineAgent:
    """
    Main agent orchestrating data pipeline operations
    Follows Single Responsibility Principle - orchestrates tool execution
    """
    
    def __init__(self, tools: List, model_id: str, system_prompt: str):
        """
        Initialize agent with tools and configuration
        
        Args:
            tools: List of available tools for the agent
            model_id: Model identifier for LLM
            system_prompt: System prompt for agent behavior
        """
        self.tools = tools
        self.model_id = model_id
        self.system_prompt = system_prompt
        self.logger = self._setup_logger()
        
        # Create tool mapping for easy access
        self.tool_map = {tool.__name__: tool for tool in tools}
    
    def _setup_logger(self) -> logging.Logger:
        """Setup logger for the agent"""
        logger = logging.getLogger(__name__)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def __call__(self, user_message: str) -> Dict[str, Any]:
        """
        Process user request and orchestrate pipeline execution
        
        Args:
            user_message: User's natural language request
            
        Returns:
            Dictionary containing execution results and message
        """
        try:
            self.logger.info(f"Processing user request: {user_message[:100]}...")
            
            # Parse user intent and execute appropriate pipeline
            result = self._execute_pipeline(user_message)
            
            return {
                "message": result.get("message", "Pipeline executed successfully"),
                "results": result.get("results", {}),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Pipeline execution failed: {e}")
            return {
                "message": f"Error: {str(e)}",
                "error": True,
                "timestamp": datetime.now().isoformat()
            }
    
    def _execute_pipeline(self, message: str) -> Dict[str, Any]:
        """
        Execute data pipeline based on user message
        
        Args:
            message: User message to process
            
        Returns:
            Dictionary containing pipeline execution results
        """
        # Parse user intent (simplified - in real implementation would use NLP)
        config = self._parse_user_intent(message)
        
        pipeline_results = {}
        collected_data = []
        
        try:
            # Step 1: Data Collection
            if config.get("collect_news", False):
                news_result = self._execute_tool("collect_news_data", {
                    "countries": config.get("countries", ["us", "jp"]),
                    "category": config.get("news_category", "general")
                })
                pipeline_results["news_collection"] = news_result
                if news_result.get("success"):
                    collected_data.extend(news_result.get("articles", []))
            
            if config.get("collect_weather", False):
                weather_result = self._execute_tool("collect_weather_data", {
                    "countries": config.get("countries", ["us", "jp"]),
                    "cities": config.get("cities")
                })
                pipeline_results["weather_collection"] = weather_result
                if weather_result.get("success"):
                    collected_data.extend(weather_result.get("weather_reports", []))
            
            if config.get("collect_web_data", False) and config.get("web_urls"):
                web_result = self._execute_tool("collect_web_data", {
                    "urls": config.get("web_urls", []),
                    "data_type": config.get("web_data_type", "blog"),
                    "selectors": config.get("web_selectors")
                })
                pipeline_results["web_collection"] = web_result
                if web_result.get("success"):
                    collected_data.extend(web_result.get("scraped_data", []))
            
            # Step 2: Data Processing (if data was collected)
            if collected_data:
                processed_results = self._process_collected_data(collected_data, config)
                pipeline_results.update(processed_results)
            
            # Step 3: Query Processing (if query requested)
            if config.get("query"):
                query_result = self._execute_tool("query_rag", {
                    "query": config.get("query"),
                    "max_results": config.get("max_results", 5)
                })
                pipeline_results["query_result"] = query_result
            
            return {
                "message": self._generate_summary_message(pipeline_results),
                "results": pipeline_results
            }
            
        except Exception as e:
            self.logger.error(f"Pipeline execution error: {e}")
            return {
                "message": f"Pipeline execution failed: {str(e)}",
                "results": pipeline_results,
                "error": True
            }
    
    def _parse_user_intent(self, message: str) -> Dict[str, Any]:
        """
        Parse user message to extract intent and configuration
        Simplified implementation - in production would use more sophisticated NLP
        
        Args:
            message: User message
            
        Returns:
            Configuration dictionary based on parsed intent
        """
        message_lower = message.lower()
        config = {}
        
        # Detect data collection requests
        if any(word in message_lower for word in ["news", "article", "headline"]):
            config["collect_news"] = True
            
        if any(word in message_lower for word in ["weather", "temperature", "forecast"]):
            config["collect_weather"] = True
            
        if any(word in message_lower for word in ["web", "scrape", "blog", "social"]):
            config["collect_web_data"] = True
        
        # Detect countries (simplified)
        if "japan" in message_lower or "jp" in message_lower:
            config["countries"] = config.get("countries", []) + ["jp"]
        if "usa" in message_lower or "us" in message_lower or "america" in message_lower:
            config["countries"] = config.get("countries", []) + ["us"]
        if "uk" in message_lower or "britain" in message_lower:
            config["countries"] = config.get("countries", []) + ["gb"]
        
        # Default countries if none specified
        if not config.get("countries"):
            config["countries"] = ["us", "jp"]
        
        # Detect query requests
        if any(word in message_lower for word in ["search", "find", "query", "what", "how", "when"]):
            config["query"] = message
        
        # If no specific collection type detected, default to news
        if not any(config.get(key, False) for key in ["collect_news", "collect_weather", "collect_web_data", "query"]):
            config["collect_news"] = True
        
        return config
    
    def _process_collected_data(self, collected_data: List[Dict], config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process collected data through validation, formatting, and storage
        
        Args:
            collected_data: Raw collected data
            config: Processing configuration
            
        Returns:
            Dictionary containing processing results
        """
        results = {}
        
        try:
            # Validation
            validation_result = self._execute_tool("validate_data", {
                "data": collected_data,
                "schema_type": "news"
            })
            results["validation"] = validation_result
            
            if validation_result.get("success"):
                valid_data = validation_result.get("valid_data", [])
                
                # Formatting
                format_result = self._execute_tool("format_data", {
                    "raw_data": valid_data,
                    "source_type": 0,  # Mixed sources
                    "country": config.get("primary_country", "us")
                })
                results["formatting"] = format_result
                
                if format_result.get("success"):
                    formatted_data = format_result.get("formatted_data", [])
                    
                    # Categorization
                    categorize_result = self._execute_tool("categorize_data", {
                        "data": formatted_data,
                        "use_ai_categorization": config.get("use_ai_categorization", False)
                    })
                    results["categorization"] = categorize_result
                    
                    if categorize_result.get("success"):
                        categorized_data = categorize_result.get("categorized_data", {})
                        
                        # Storage
                        if config.get("store_in_database", True):
                            db_result = self._execute_tool("store_in_database", {
                                "categorized_data": categorized_data
                            })
                            results["database_storage"] = db_result
                        
                        if config.get("store_in_s3", True):
                            s3_result = self._execute_tool("store_in_s3", {
                                "data": formatted_data,
                                "metadata": config.get("metadata")
                            })
                            results["s3_storage"] = s3_result
                        
                        # Optional analysis
                        if config.get("filter_fake_news", False):
                            for item in formatted_data:
                                if item.get("content"):
                                    filter_result = self._execute_tool("filter_fake_news", {
                                        "content": item["content"],
                                        "threshold": config.get("fake_news_threshold", 0.7)
                                    })
                                    results.setdefault("fake_news_filtering", []).append(filter_result)
                        
                        if config.get("analyze_sentiment", False):
                            for item in formatted_data:
                                if item.get("content"):
                                    sentiment_result = self._execute_tool("analyze_sentiment", {
                                        "content": item["content"]
                                    })
                                    results.setdefault("sentiment_analysis", []).append(sentiment_result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Data processing error: {e}")
            results["error"] = str(e)
            return results
    
    def _execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a specific tool with given parameters
        
        Args:
            tool_name: Name of the tool to execute
            params: Parameters to pass to the tool
            
        Returns:
            Tool execution result
        """
        try:
            if tool_name not in self.tool_map:
                raise ValueError(f"Tool {tool_name} not found")
            
            tool = self.tool_map[tool_name]
            self.logger.info(f"Executing tool: {tool_name}")
            
            # Execute tool with parameters
            if tool_name == "collect_news_data":
                return tool(params["countries"], params.get("category", "general"))
            elif tool_name == "collect_weather_data":
                return tool(params["countries"], params.get("cities"))
            elif tool_name == "collect_web_data":
                return tool(params["urls"], params["data_type"], params.get("selectors"))
            elif tool_name == "validate_data":
                return tool(params["data"], params["schema_type"])
            elif tool_name == "format_data":
                return tool(params["raw_data"], params["source_type"], params.get("country", "us"))
            elif tool_name == "categorize_data":
                return tool(params["data"], params.get("use_ai_categorization", False))
            elif tool_name == "store_in_database":
                return tool(params["categorized_data"])
            elif tool_name == "store_in_s3":
                return tool(params["data"], params.get("metadata"))
            elif tool_name == "filter_fake_news":
                return tool(params["content"], params.get("threshold", 0.7))
            elif tool_name == "analyze_sentiment":
                return tool(params["content"])
            elif tool_name == "query_rag":
                return tool(params["query"], params.get("max_results", 5))
            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}
                
        except Exception as e:
            self.logger.error(f"Tool execution error for {tool_name}: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_summary_message(self, results: Dict[str, Any]) -> str:
        """
        Generate a human-readable summary of pipeline execution results
        
        Args:
            results: Pipeline execution results
            
        Returns:
            Summary message string
        """
        messages = []
        
        # Collection results
        if "news_collection" in results:
            news_result = results["news_collection"]
            if news_result.get("success"):
                count = news_result.get("count", 0)
                messages.append(f"✓ Collected {count} news articles")
            else:
                messages.append("✗ News collection failed")
        
        if "weather_collection" in results:
            weather_result = results["weather_collection"]
            if weather_result.get("success"):
                count = weather_result.get("count", 0)
                messages.append(f"✓ Collected {count} weather reports")
            else:
                messages.append("✗ Weather collection failed")
        
        if "web_collection" in results:
            web_result = results["web_collection"]
            if web_result.get("success"):
                count = web_result.get("count", 0)
                messages.append(f"✓ Collected {count} web data items")
            else:
                messages.append("✗ Web data collection failed")
        
        # Processing results
        if "validation" in results:
            validation = results["validation"]
            if validation.get("success"):
                messages.append("✓ Data validation completed")
            else:
                messages.append("✗ Data validation failed")
        
        if "database_storage" in results:
            db_result = results["database_storage"]
            if db_result.get("success"):
                messages.append("✓ Data stored in database")
            else:
                messages.append("✗ Database storage failed")
        
        if "s3_storage" in results:
            s3_result = results["s3_storage"]
            if s3_result.get("success"):
                messages.append("✓ Data stored in S3")
            else:
                messages.append("✗ S3 storage failed")
        
        # Query results
        if "query_result" in results:
            query_result = results["query_result"]
            if query_result.get("success"):
                messages.append("✓ Query processed successfully")
            else:
                messages.append("✗ Query processing failed")
        
        if not messages:
            return "Pipeline executed but no operations were performed."
        
        return "Pipeline execution summary:\n" + "\n".join(messages)