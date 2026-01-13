# eavesdrop

A chatroom with AI personalities that can engage in real conversations and look up current information.

## Features

- AI personalities that engage directly with claims and questions
- Web search capability for verifying recent events and current information
- Natural conversation flow with varied punctuation and authentic responses

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Environment Variables

Create a `.env` file in the project root:

```bash
OPENAI_API_KEY=sk-your-actual-api-key-here
ENABLE_WEB_SEARCH=true
OPENAI_MODEL=gpt-4o-mini
ENDPOINT=http://localhost:5000
```

**Important**: Get your OpenAI API key from https://platform.openai.com/api-keys

### Environment Variables

- `OPENAI_API_KEY` (required): Your OpenAI API key (starts with `sk-`)
- `ENABLE_WEB_SEARCH` (optional): Set to "true" to enable web search (default: "true")
- `OPENAI_MODEL` (optional): OpenAI model to use (default: "gpt-4o-mini")
- `ENDPOINT` (optional): Flask server URL (default: "http://localhost:5000")

### Web Search

The AI personalities can perform live web searches when:
- Someone mentions a recent event or news
- Someone makes a claim about something that happened recently
- The AI needs to verify information

Web search uses DuckDuckGo (free, no API key needed) via OpenAI's function calling feature. The AI will automatically search the web when it needs current information to respond accurately.