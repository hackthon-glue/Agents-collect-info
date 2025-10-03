"""
Metadata generator for RAG enhancement

Generates metadata (summary, keywords, semantic tags) for data items
to improve RAG search accuracy.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import boto3
import json

from ..utilities.data_models import ToolResponse


class MetadataGenerator:
    """Generate metadata for RAG enhancement using Bedrock"""

    def __init__(self, region: str = "us-east-1", model_id: str = "amazon.nova-lite-v1:0"):
        self.logger = logging.getLogger(__name__)
        self.region = region
        self.model_id = model_id
        self.bedrock_client = boto3.client("bedrock-runtime", region_name=region)

    def generate_metadata(self, data: Dict[str, Any]) -> ToolResponse:
        """
        Generate metadata for a single data item

        Args:
            data: Data item to generate metadata for

        Returns:
            ToolResponse with generated metadata
        """
        try:
            # Extract content based on data type
            content = self._extract_content(data)
            if not content:
                return ToolResponse(
                    success=False,
                    message="No content available for metadata generation"
                )

            # Generate metadata using Bedrock
            metadata = self._generate_with_bedrock(content, data)

            return ToolResponse(
                success=True,
                message="Metadata generated successfully",
                data=metadata
            )

        except Exception as e:
            self.logger.error(f"Failed to generate metadata: {str(e)}")
            return ToolResponse(
                success=False,
                message=f"Failed to generate metadata: {str(e)}",
                error=str(e)
            )

    def _extract_content(self, data: Dict[str, Any]) -> str:
        """Extract relevant content from data item"""
        # News/article content
        if "title" in data and "content" in data:
            return f"Title: {data['title']}\n\nContent: {data['content']}"
        elif "title" in data:
            return f"Title: {data['title']}"
        
        # Weather data
        elif "description" in data and "location" in data:
            return f"Location: {data['location']}, Weather: {data['description']}, Temperature: {data.get('temperature', 'N/A')}"
        
        return ""

    def _generate_with_bedrock(self, content: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate metadata using Bedrock"""
        prompt = f"""Analyze the following content and generate metadata for RAG search optimization.

Content:
{content[:2000]}

Generate:
1. A concise summary (2-3 sentences)
2. 5-10 relevant keywords
3. 3-5 semantic tags (categories/topics)
4. Geographic location if mentioned
5. Temporal context if mentioned

Respond in JSON format:
{{
  "summary": "...",
  "keywords": ["...", "..."],
  "semantic_tags": ["...", "..."],
  "location": "...",
  "temporal_context": "..."
}}"""

        try:
            response = self.bedrock_client.converse(
                modelId=self.model_id,
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                inferenceConfig={"maxTokens": 500, "temperature": 0.3}
            )

            response_text = response["output"]["message"]["content"][0]["text"]
            
            # Parse JSON response
            metadata = json.loads(response_text)
            
            # Add base metadata
            metadata.update({
                "data_type": self._infer_data_type(data),
                "country": data.get("country", "unknown"),
                "source": data.get("source_name", "unknown"),
                "published_at": data.get("published_at", data.get("collected_at", "")),
                "generated_at": datetime.now(timezone.utc).isoformat()
            })

            return metadata

        except Exception as e:
            self.logger.warning(f"Bedrock generation failed, using fallback: {str(e)}")
            return self._generate_fallback_metadata(content, data)

    def _generate_fallback_metadata(self, content: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate basic metadata without AI"""
        words = content.lower().split()
        keywords = list(set([w for w in words if len(w) > 4]))[:10]

        return {
            "summary": content[:200] + "..." if len(content) > 200 else content,
            "keywords": keywords,
            "semantic_tags": [self._infer_data_type(data)],
            "location": data.get("country", "unknown"),
            "temporal_context": data.get("published_at", ""),
            "data_type": self._infer_data_type(data),
            "country": data.get("country", "unknown"),
            "source": data.get("source_name", "unknown"),
            "published_at": data.get("published_at", data.get("collected_at", "")),
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

    def _infer_data_type(self, data: Dict[str, Any]) -> str:
        """Infer data type from data structure"""
        if "title" in data and "content" in data:
            return "news"
        elif "temperature" in data and "humidity" in data:
            return "weather"
        return "other"
