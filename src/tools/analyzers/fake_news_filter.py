"""
Fake News Filter for content credibility analysis

Integrates with SageMaker endpoint hosting HuggingFace model for fake news detection.
"""

import json
import logging
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError, BotoCoreError

from ..utilities.data_models import ToolResponse
from ..utilities.error_handler import ErrorHandler

logger = logging.getLogger(__name__)


class FakeNewsFilter:
    """Filter for detecting fake news using SageMaker endpoint"""

    def __init__(self, endpoint_name: str, region: str = "us-east-1"):
        """
        Initialize fake news filter with SageMaker endpoint

        Args:
            endpoint_name: SageMaker endpoint name or ARN
            region: AWS region for SageMaker endpoint
        """
        self.endpoint_name = endpoint_name
        self.region = region
        self.sagemaker_runtime = boto3.client("sagemaker-runtime", region_name=region)
        self.error_handler = ErrorHandler()

    def filter_content(self, content: str, threshold: float = 0.7) -> ToolResponse:
        """
        Analyze content for fake news detection

        Args:
            content: Text content to analyze
            threshold: Credibility threshold (0.0 to 1.0)

        Returns:
            ToolResponse with credibility score and filter decision
        """
        try:
            if not content or not content.strip():
                return ToolResponse(
                    success=False,
                    message="Empty content provided for analysis",
                    error="Content cannot be empty"
                )

            # Prepare input for HuggingFace model
            payload = {
                "inputs": content.strip()
            }

            # Call SageMaker endpoint
            response = self.sagemaker_runtime.invoke_endpoint(
                EndpointName=self.endpoint_name,
                ContentType="application/json",
                Body=json.dumps(payload)
            )

            # Parse response
            result = json.loads(response["Body"].read().decode())
            
            # Extract credibility score (assuming model returns probability)
            credibility_score = self._extract_credibility_score(result)
            is_credible = credibility_score >= threshold

            logger.info(
                f"Analyzed content (length: {len(content)}), "
                f"credibility: {credibility_score:.3f}, "
                f"threshold: {threshold}, "
                f"credible: {is_credible}"
            )

            return ToolResponse(
                success=True,
                message=f"Content analysis completed. Credibility: {credibility_score:.3f}",
                data={
                    "credibility_score": credibility_score,
                    "is_credible": is_credible,
                    "threshold": threshold,
                    "content_length": len(content),
                    "model_response": result
                }
            )

        except ClientError as e:
            error_msg = f"AWS SageMaker error: {str(e)}"
            logger.error(error_msg)
            return ToolResponse(
                success=False,
                message="Failed to analyze content due to SageMaker error",
                error=error_msg
            )

        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse model response: {str(e)}"
            logger.error(error_msg)
            return ToolResponse(
                success=False,
                message="Invalid response from fake news detection model",
                error=error_msg
            )

        except Exception as e:
            error_msg = self.error_handler.handle_error(e, "fake_news_filter")
            logger.error(f"Unexpected error in fake news filter: {error_msg}")
            return ToolResponse(
                success=False,
                message="Failed to analyze content for fake news",
                error=error_msg
            )

    def _extract_credibility_score(self, model_response: Any) -> float:
        """
        Extract credibility score from model response with universal format support

        Args:
            model_response: Raw response from any model format

        Returns:
            Credibility score between 0.0 and 1.0
        """
        try:
            # Flatten nested structures
            data = self._flatten_response(model_response)
            
            # Find score and label pairs
            for item in data:
                if isinstance(item, dict):
                    score = self._extract_score_from_dict(item)
                    if score is not None:
                        return score
            
            # Try direct numeric values
            for item in data:
                if isinstance(item, (int, float)):
                    return max(0.0, min(1.0, float(item)))
            
            return 0.5  # Neutral fallback
            
        except Exception as e:
            logger.warning(f"Error extracting credibility score: {e}")
            return 0.5
    
    def _flatten_response(self, response: Any) -> list:
        """Flatten response to list of items for processing"""
        if isinstance(response, list):
            return response
        elif isinstance(response, dict):
            return [response]
        else:
            return [response]
    
    def _extract_score_from_dict(self, item: dict) -> Optional[float]:
        """Extract credibility score from dictionary item"""
        if "label" in item and "score" in item:
            return self._interpret_labeled_score(item["label"], item["score"])
        
        # Direct score fields
        for key in ["score", "credibility", "confidence", "probability"]:
            if key in item:
                return max(0.0, min(1.0, float(item[key])))
        
        return None
    
    def _interpret_labeled_score(self, label: str, score: float) -> float:
        """Interpret score based on label semantics"""
        label = str(label).upper().strip()
        score = max(0.0, min(1.0, float(score)))
        
        # Fake/non-credible indicators (check first to handle NOT_CREDIBLE correctly)
        if any(term in label for term in ["FAKE", "FALSE", "NOT_CREDIBLE", "ILLEGITIMATE", "LABEL_1"]):
            return 1.0 - score
        
        # Real/credible indicators
        if any(term in label for term in ["REAL", "TRUE", "CREDIBLE", "LEGITIMATE", "AUTHENTIC", "LABEL_0"]):
            return score
        
        # Default: assume higher score = more credible
        return score

    def batch_filter(self, contents: list, threshold: float = 0.7) -> ToolResponse:
        """
        Filter multiple content items for fake news

        Args:
            contents: List of text content to analyze
            threshold: Credibility threshold

        Returns:
            ToolResponse with batch analysis results
        """
        try:
            results = []
            credible_count = 0
            
            for i, content in enumerate(contents):
                result = self.filter_content(content, threshold)
                
                if result.success:
                    is_credible = result.data.get("is_credible", False)
                    if is_credible:
                        credible_count += 1
                    
                    results.append({
                        "index": i,
                        "credibility_score": result.data.get("credibility_score", 0.0),
                        "is_credible": is_credible,
                        "content_length": len(content)
                    })
                else:
                    results.append({
                        "index": i,
                        "error": result.error,
                        "content_length": len(content)
                    })

            return ToolResponse(
                success=True,
                message=f"Batch analysis completed: {credible_count}/{len(contents)} items credible",
                data={
                    "total_items": len(contents),
                    "credible_count": credible_count,
                    "threshold": threshold,
                    "results": results
                }
            )

        except Exception as e:
            error_msg = self.error_handler.handle_error(e, "batch_fake_news_filter")
            logger.error(f"Error in batch fake news filtering: {error_msg}")
            return ToolResponse(
                success=False,
                message="Failed to perform batch fake news analysis",
                error=error_msg
            )