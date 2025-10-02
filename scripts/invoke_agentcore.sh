#!/bin/bash
# Invoke deployed AgentCore agent

AGENT_NAME="strands-data-pipeline-agent"
REGION=${AWS_REGION:-us-east-1}
PROMPT=${1:-"Collect news data for Japan"}

echo "Invoking AgentCore agent..."
echo "Prompt: $PROMPT"

agentcore invoke \
    --name $AGENT_NAME \
    --region $REGION \
    --payload "{\"prompt\": \"$PROMPT\"}"
