"""
Integration tests for Strands Data Pipeline Agent
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from strands import Agent


class TestAgentIntegration:
    """Test cases for agent integration"""

    def test_agent_creation_without_tools(self):
        """Test agent can be created without tools"""
        agent = Agent(
            model="us.anthropic.claude-3-haiku-20240307-v1:0",
            system_prompt="Test prompt"
        )
        
        assert agent is not None

    def test_agent_creation_with_system_prompt(self):
        """Test agent with custom system prompt"""
        agent = Agent(
            model="us.anthropic.claude-3-haiku-20240307-v1:0",
            system_prompt="Custom test prompt"
        )
        
        assert agent is not None
