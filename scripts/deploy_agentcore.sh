#!/bin/bash
# Deployment script for AgentCore

set -e

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

AGENT_NAME="strands-data-pipeline-agent"
REGION=${AWS_REGION:-us-west-2}
OWNER=${OWNER:-AI-Hackathon}
TEAM=${TEAM:-09_Glue}

echo "Deploying Strands Data Pipeline Agent to AgentCore..."
echo "Environment: $ENVIRONMENT"
echo "Version: $VERSION"

# Build and deploy
cd src
agentcore deploy \
    --name $AGENT_NAME \
    --region $REGION \
    --entrypoint agent:invoke \
    --requirements ../requirements.txt \
    --tags "Environment=$ENVIRONMENT,Version=$VERSION,Project=WhisperPlanet,ManagedBy=AgentCore"

echo "Deployment complete!"
echo "Agent Name: $AGENT_NAME"
echo "Region: $REGION"
echo "Tags: Environment=$ENVIRONMENT, Version=$VERSION"
