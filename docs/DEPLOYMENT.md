# Deployment Guide

## Prerequisites

- Python 3.9+
- AWS CLI configured
- AgentCore CLI installed: `pip install bedrock-agentcore`
- Required environment variables in `.env` and config.json files

## Local Execution

### Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys and AWS credentials
```

3. Run locally:
```bash
chmod +x scripts/run_local.sh
./scripts/run_local.sh
```

### Interactive Mode

In interactive mode, you can test the agent with natural language:

```
> Collect news data for Japan and USA
> Store weather data for Tokyo
> Query: What are the latest news about technology?
> quit
```

## AgentCore Deployment

### Deploy Agent

1. Ensure AWS credentials are configured:
```bash
aws configure
```

2. Deploy to AgentCore:
```bash
chmod +x scripts/deploy_agentcore.sh
./scripts/deploy_agentcore.sh
```

The deployment script automatically adds tags:
- `Environment`: From `ENVIRONMENT` env var (default: development)
- `Version`: From `VERSION` env var (default: 1.0.0)
- `Project`: WhisperPlanet
- `ManagedBy`: AgentCore

### Invoke Deployed Agent

```bash
chmod +x scripts/invoke_agentcore.sh
./scripts/invoke_agentcore.sh "Collect news data for Japan"
```

### Using AgentCore CLI Directly

Deploy:
```bash
cd src
agentcore deploy \
    --name strands-data-pipeline-agent \
    --region us-east-1 \
    --entrypoint agent:invoke \
    --requirements ../requirements.txt
```

Invoke:
```bash
agentcore invoke \
    --name strands-data-pipeline-agent \
    --region us-east-1 \
    --payload '{"prompt": "Collect news data for Japan"}'
```

List deployed agents:
```bash
agentcore list --region us-east-1
```

Delete agent:
```bash
agentcore delete --name strands-data-pipeline-agent --region us-east-1
```

## Environment Variables

All configuration is managed through `.env` file. Copy `.env.example` to `.env` and configure:

### Required Variables

```bash
# Agent Configuration
AGENT_MODEL_ID=amazon.nova-premier-v1:0

# API Keys
NEWS_API_KEY=your_news_api_key
WEATHER_API_KEY=your_weather_api_key

# AWS Configuration
AWS_REGION=us-east-1

# Database Configuration
DB_HOST=your-db-host
DB_PORT=5432
DB_NAME=strands_data
DB_USER=your-db-user
DB_PASSWORD=your-db-password

# S3 Configuration
S3_BUCKET_NAME=your-bucket-name
S3_REGION=us-east-1
```

### Optional Variables

```bash
# Knowledge Base (for RAG)
KNOWLEDGE_BASE_ID=your-kb-id
DATA_SOURCE_ID=your-ds-id

# SageMaker (for fake news filtering)
SAGEMAKER_FAKE_NEWS_ENDPOINT=your-endpoint-name

# Pipeline Settings
PIPELINE_ENABLE_FAKE_NEWS_FILTER=false
PIPELINE_FAKE_NEWS_THRESHOLD=0.7
```

See `.env.example` for complete list of available configuration options.

## Troubleshooting

### Local Execution Issues

- **Import errors**: Ensure you're in the project root and `src/` is in PYTHONPATH
- **API key errors**: Check `.env` file has valid API keys (copy from `.env.example`)
- **Database connection**: Verify database credentials and network access
- **Missing .env**: Copy `.env.example` to `.env` and configure all required variables

### AgentCore Deployment Issues

- **Authentication errors**: Run `aws configure` and verify credentials
- **Region mismatch**: Ensure `AWS_REGION` matches your deployment region
- **Deployment timeout**: Large dependencies may take time; wait for completion
- **Invocation errors**: Check CloudWatch logs for detailed error messages

## Architecture

### Local Mode
```
User Input → agent.py (--interactive) → Strands Agent → Tools → Response
```

### AgentCore Mode
```
API Request → Lambda (AgentCore) → agent:invoke → Strands Agent → Tools → Response
```

## Next Steps

1. Test locally first to validate functionality
2. Deploy to AgentCore for production use
3. Monitor CloudWatch logs for errors
4. Set up CI/CD pipeline for automated deployments
