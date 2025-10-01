"""
Unit tests for FakeNewsFilter

Tests the fake news detection functionality with mocked SageMaker calls.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from tools.analyzers.fake_news_filter import FakeNewsFilter


class TestFakeNewsFilter:
    """Test cases for FakeNewsFilter class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.endpoint_name = "test-fake-news-endpoint"
        self.region = "us-east-1"
        
    @patch('boto3.client')
    def test_init(self, mock_boto_client):
        """Test FakeNewsFilter initialization"""
        filter_tool = FakeNewsFilter(self.endpoint_name, self.region)
        
        assert filter_tool.endpoint_name == self.endpoint_name
        assert filter_tool.region == self.region
        mock_boto_client.assert_called_once_with("sagemaker-runtime", region_name=self.region)

    @patch('boto3.client')
    def test_filter_content_success_real_label(self, mock_boto_client):
        """Test successful content filtering with REAL label"""
        # Mock SageMaker response
        mock_response = {
            "Body": Mock()
        }
        mock_response["Body"].read.return_value.decode.return_value = json.dumps([
            {"label": "REAL", "score": 0.85}
        ])
        
        mock_runtime = Mock()
        mock_runtime.invoke_endpoint.return_value = mock_response
        mock_boto_client.return_value = mock_runtime
        
        filter_tool = FakeNewsFilter(self.endpoint_name, self.region)
        result = filter_tool.filter_content("This is a test article", 0.7)
        
        assert result.success is True
        assert result.data["credibility_score"] == 0.85
        assert result.data["is_credible"] is True
        assert result.data["threshold"] == 0.7
        assert "Content analysis completed" in result.message

    @patch('boto3.client')
    def test_filter_content_success_fake_label(self, mock_boto_client):
        """Test successful content filtering with FAKE label"""
        # Mock SageMaker response
        mock_response = {
            "Body": Mock()
        }
        mock_response["Body"].read.return_value.decode.return_value = json.dumps([
            {"label": "FAKE", "score": 0.9}
        ])
        
        mock_runtime = Mock()
        mock_runtime.invoke_endpoint.return_value = mock_response
        mock_boto_client.return_value = mock_runtime
        
        filter_tool = FakeNewsFilter(self.endpoint_name, self.region)
        result = filter_tool.filter_content("This is fake news", 0.7)
        
        assert result.success is True
        assert abs(result.data["credibility_score"] - 0.1) < 0.001  # 1 - 0.9
        assert result.data["is_credible"] is False
        assert result.data["threshold"] == 0.7

    @patch('boto3.client')
    def test_filter_content_empty_content(self, mock_boto_client):
        """Test filtering with empty content"""
        filter_tool = FakeNewsFilter(self.endpoint_name, self.region)
        result = filter_tool.filter_content("", 0.7)
        
        assert result.success is False
        assert "Empty content provided" in result.message
        assert result.error == "Content cannot be empty"

    @patch('boto3.client')
    def test_filter_content_sagemaker_error(self, mock_boto_client):
        """Test handling of SageMaker ClientError"""
        mock_runtime = Mock()
        mock_runtime.invoke_endpoint.side_effect = ClientError(
            {"Error": {"Code": "ValidationException", "Message": "Invalid endpoint"}},
            "InvokeEndpoint"
        )
        mock_boto_client.return_value = mock_runtime
        
        filter_tool = FakeNewsFilter(self.endpoint_name, self.region)
        result = filter_tool.filter_content("Test content", 0.7)
        
        assert result.success is False
        assert "Failed to analyze content due to SageMaker error" in result.message
        assert "AWS SageMaker error" in result.error

    @patch('boto3.client')
    def test_filter_content_json_decode_error(self, mock_boto_client):
        """Test handling of JSON decode error"""
        mock_response = {
            "Body": Mock()
        }
        mock_response["Body"].read.return_value.decode.return_value = "invalid json"
        
        mock_runtime = Mock()
        mock_runtime.invoke_endpoint.return_value = mock_response
        mock_boto_client.return_value = mock_runtime
        
        filter_tool = FakeNewsFilter(self.endpoint_name, self.region)
        result = filter_tool.filter_content("Test content", 0.7)
        
        assert result.success is False
        assert "Invalid response from fake news detection model" in result.message
        assert "Failed to parse model response" in result.error

    @patch('boto3.client')
    def test_extract_credibility_score_dict_format(self, mock_boto_client):
        """Test credibility score extraction from dict format"""
        filter_tool = FakeNewsFilter(self.endpoint_name, self.region)
        
        # Test direct score format
        response = {"score": 0.75}
        score = filter_tool._extract_credibility_score(response)
        assert score == 0.75
        
        # Test credibility format
        response = {"credibility": 0.65}
        score = filter_tool._extract_credibility_score(response)
        assert score == 0.65

    @patch('boto3.client')
    def test_extract_credibility_score_bert_labels(self, mock_boto_client):
        """Test credibility score extraction with BERT-style labels"""
        filter_tool = FakeNewsFilter(self.endpoint_name, self.region)
        
        # Test LABEL_0 (real)
        response = [{"label": "LABEL_0", "score": 0.85}]
        score = filter_tool._extract_credibility_score(response)
        assert score == 0.85
        
        # Test LABEL_1 (fake)
        response = [{"label": "LABEL_1", "score": 0.9}]
        score = filter_tool._extract_credibility_score(response)
        assert abs(score - 0.1) < 0.001  # 1 - 0.9

    @patch('boto3.client')
    def test_extract_credibility_score_binary_format(self, mock_boto_client):
        """Test credibility score extraction with binary format"""
        filter_tool = FakeNewsFilter(self.endpoint_name, self.region)
        
        # Test direct binary output
        score = filter_tool._extract_credibility_score(1)
        assert score == 1.0
        
        score = filter_tool._extract_credibility_score(0)
        assert score == 0.0
        
        # Test binary list format
        score = filter_tool._extract_credibility_score([0.85])
        assert score == 0.85
        
        score = filter_tool._extract_credibility_score([1])
        assert score == 1.0

    @patch('boto3.client')
    def test_extract_credibility_score_unknown_format(self, mock_boto_client):
        """Test credibility score extraction with unknown format"""
        filter_tool = FakeNewsFilter(self.endpoint_name, self.region)
        
        response = {"unknown": "format"}
        score = filter_tool._extract_credibility_score(response)
        assert score == 0.5  # Fallback value

    @patch('boto3.client')
    def test_batch_filter_success(self, mock_boto_client):
        """Test successful batch filtering"""
        # Mock SageMaker responses
        mock_responses = [
            json.dumps([{"label": "REAL", "score": 0.85}]),
            json.dumps([{"label": "FAKE", "score": 0.9}]),
            json.dumps([{"label": "REAL", "score": 0.6}])
        ]
        
        mock_runtime = Mock()
        mock_boto_client.return_value = mock_runtime
        
        def mock_invoke_endpoint(*args, **kwargs):
            response = {"Body": Mock()}
            response["Body"].read.return_value.decode.return_value = mock_responses.pop(0)
            return response
        
        mock_runtime.invoke_endpoint.side_effect = mock_invoke_endpoint
        
        filter_tool = FakeNewsFilter(self.endpoint_name, self.region)
        contents = ["Real news", "Fake news", "Borderline news"]
        result = filter_tool.batch_filter(contents, 0.7)
        
        assert result.success is True
        assert result.data["total_items"] == 3
        assert result.data["credible_count"] == 1  # Only first item above threshold
        assert result.data["threshold"] == 0.7
        assert len(result.data["results"]) == 3

    @patch('boto3.client')
    def test_batch_filter_with_errors(self, mock_boto_client):
        """Test batch filtering with some errors"""
        mock_runtime = Mock()
        mock_boto_client.return_value = mock_runtime
        
        def mock_invoke_endpoint(*args, **kwargs):
            if "error" in kwargs.get("Body", ""):
                raise ClientError(
                    {"Error": {"Code": "ValidationException", "Message": "Error"}},
                    "InvokeEndpoint"
                )
            response = {"Body": Mock()}
            response["Body"].read.return_value.decode.return_value = json.dumps([
                {"label": "REAL", "score": 0.85}
            ])
            return response
        
        mock_runtime.invoke_endpoint.side_effect = mock_invoke_endpoint
        
        filter_tool = FakeNewsFilter(self.endpoint_name, self.region)
        contents = ["Good content", "error content"]
        result = filter_tool.batch_filter(contents, 0.7)
        
        assert result.success is True
        assert result.data["total_items"] == 2
        assert result.data["credible_count"] == 1
        assert len(result.data["results"]) == 2
        assert "error" in result.data["results"][1]


if __name__ == "__main__":
    pytest.main([__file__])