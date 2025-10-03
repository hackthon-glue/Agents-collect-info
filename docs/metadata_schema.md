# RAG Metadata Schema

## Overview
This document defines the metadata schema used for RAG (Retrieval-Augmented Generation) optimization in the Strands Data Pipeline.

## Common Metadata Fields

All data items stored in S3 include the following metadata fields to improve RAG search accuracy:

### Core Metadata
- **summary** (string): 2-3 sentence concise summary of the content
- **keywords** (array): 5-10 relevant keywords extracted from content
- **semantic_tags** (array): 3-5 high-level categories/topics
- **data_type** (string): Type of data (news, weather, other)
- **country** (string): Country code (e.g., "us", "jp", "uk")
- **source** (string): Data source name
- **published_at** (string): ISO 8601 timestamp of publication
- **generated_at** (string): ISO 8601 timestamp of metadata generation

### Optional Metadata
- **location** (string): Geographic location mentioned in content
- **temporal_context** (string): Temporal information extracted from content

## Data Type Specific Fields

### News Articles
- **category** (string): News category (general, business, technology, etc.)
- **author** (string): Article author
- **fake_news_score** (float): Credibility score (0.0-1.0)

### Weather Data
- **temperature** (float): Temperature value
- **conditions** (string): Weather conditions description

## Example Metadata Structure

```json
{
  "metadata": {
    "summary": "AI technology advances in natural language processing with new breakthrough.",
    "keywords": ["AI", "NLP", "technology", "breakthrough", "language"],
    "semantic_tags": ["technology", "artificial intelligence", "innovation"],
    "data_type": "news",
    "country": "us",
    "source": "TechNews",
    "published_at": "2024-01-15T10:00:00Z",
    "generated_at": "2024-01-15T10:05:00Z",
    "location": "Silicon Valley",
    "temporal_context": "January 2024",
    "stored_at": "2024-01-15T10:05:30Z",
    "prefix": "us/2024/01/15/TechNews/"
  },
  "data": {
    "title": "Breaking News: AI Advances",
    "content": "...",
    "author": "John Doe",
    "url": "https://example.com/article",
    "category": "technology"
  }
}
```

## Usage in RAG Queries

The metadata enables:
1. **Semantic Search**: Keywords and tags improve vector search relevance
2. **Filtering**: Country, data_type, and temporal_context enable precise filtering
3. **Context Enhancement**: Summary provides quick context for LLM processing
4. **Source Attribution**: Source and published_at enable proper citation
