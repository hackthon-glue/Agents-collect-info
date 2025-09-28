# Strands Data Pipeline Agent

A comprehensive data collection and processing agent designed for deployment on AgentCore. The system collects news, weather, and social media data from various sources, processes and standardizes the data, stores it in both relational and object storage, and provides intelligent querying capabilities through RAG (Retrieval-Augmented Generation).

## Project Structure

```
src/
├── agent.py                 # Main agent entry point
├── tools.py                 # Tool definitions with @tool decorators
└── tools/                   # Tool implementation classes
    ├── collectors/          # Data collection tools
    ├── processors/          # Data processing tools
    ├── storage/             # Data storage tools
    ├── analyzers/           # Analysis tools (optional)
    ├── query/               # Query and RAG tools
    └── utilities/           # Common utilities and data models
```

## Features

### Core Data Collection
- **News APIs**: Collect news data from multiple countries using free APIs
- **Weather APIs**: Collect weather data for specified locations
- **Web Scraping**: Collect blog posts and social media data using AgentCore Browser

### Data Processing
- **Validation**: Validate collected data against predefined schemas
- **Formatting**: Transform data to standardized NEWS API structure
- **Categorization**: Organize data into appropriate categories

### Storage
- **Database Storage**: Store categorized data in PostgreSQL/Aurora
- **S3 Storage**: Store JSON files with organized prefix structure
- **Knowledge Base Sync**: Automatic vectorization for RAG queries

### Optional Features
- **Fake News Filtering**: Filter content using HuggingFace models on SageMaker
- **Sentiment Analysis**: Analyze emotional sentiment of text content
- **RAG Queries**: Natural language querying of stored data

## Configuration

The agent uses a hierarchical configuration system:

1. **Default values** (built-in)
2. **Configuration file** (`config.json`)
3. **Environment variables** (highest priority)

### Environment Variables

Key environment variables:
- `NEWS_API_KEY`: API key for news data collection
- `WEATHER_API_KEY`: API key for weather data collection
- `DB_HOST`, `DB_USERNAME`, `DB_PASSWORD`: Database connection
- `S3_BUCKET_NAME`: S3 bucket for data storage
- `OPENSEARCH_ENDPOINT`: Knowledge Base endpoint
- `SAGEMAKER_FAKE_NEWS_ENDPOINT`: SageMaker endpoint for fake news filtering

### Configuration File

Copy `config.example.json` to `config.json` and update with your values:

```bash
cp config.example.json config.json
```

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure the agent (see Configuration section above)

3. Deploy to AgentCore using the `create_agent()` factory function

## Usage

### Running the Agent with BedrockAgentCoreApp

The agent is designed to run with the Strands framework using BedrockAgentCoreApp:

```bash
# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run the agent
python agent.py
```

### Agent Invocation

The agent accepts JSON payloads with a "prompt" key:

```json
{
  "prompt": "日本とアメリカのニュースデータを収集して、データベースに保存してください"
}
```

### Direct Agent Usage

```python
from agent import create_agent

# Create agent instance
agent = create_agent()

# Direct invocation
response = agent("Collect news data for Japan and US")

# Execute data pipeline
config = {
    "countries": ["us", "jp"],
    "collect_news": True,
    "collect_weather": True,
    "store_in_database": True,
    "store_in_s3": True
}

result = agent.execute_data_pipeline(config)
```

### RAG Queries

```python
# Query stored data
response = agent.query_data("What are the latest news about technology in Japan?")
```

## Development

### Project Status

This is the initial project structure setup. Individual tools will be implemented in subsequent development phases:

- **Task 2**: Data collection tools (News API, Weather API, Browser)
- **Task 3**: Data processing tools (Validation, Formatting, Categorization)
- **Task 4**: Storage tools (Database, S3, Knowledge Base sync)
- **Task 5**: Analysis tools (Fake news filtering, Sentiment analysis)
- **Task 6**: Query tools (RAG implementation)

### Error Handling

The system includes comprehensive error handling:
- Centralized error management with `ErrorHandler`
- Custom exception types for different error categories
- Automatic error logging and tracking
- Graceful degradation for optional features

### Data Models

Standardized data models ensure consistency:
- `NewsArticle`: Standard news article structure
- `WeatherData`: Weather information structure
- `PipelineConfig`: Pipeline execution configuration
- `ToolResponse`: Standard tool response format

## AgentCore Integration

The agent is designed for seamless AgentCore deployment:
- Uses `@tool` decorators for tool registration
- Implements standard AgentCore interfaces
- Supports AgentCore configuration management
- Integrates with AgentCore Browser for web scraping

## License

See LICENSE file for details.