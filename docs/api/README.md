# NLP/AI Microservice API Documentation

This directory contains comprehensive API documentation for the NLP/AI Microservice, specifically designed for educational content handling with SAT/UTBK data.

## Files

- `openapi.json` - Complete OpenAPI 3.0 specification
- `redoc.html` - Interactive ReDoc documentation (open in browser)
- `postman_collection.json` - Postman collection for API testing
- `api_examples.json` - Example requests and test data

## Quick Start

### 1. View Interactive Documentation

Open `redoc.html` in your web browser to view the interactive API documentation.

### 2. Import Postman Collection

1. Open Postman
2. Click "Import" 
3. Select `postman_collection.json`
4. Set environment variables:
   - `base_url`: http://localhost:8000 (or your server URL)
   - `jwt_token`: Your JWT token (obtained from login)
   - `api_key`: Your API key (for external endpoints)

### 3. Test with Examples

Use the examples in `api_examples.json` to test the API endpoints.

## Authentication

The API supports two authentication methods:

### JWT Token Authentication
- Use `/auth/login` to obtain JWT tokens
- Include `Authorization: Bearer <token>` header
- Required for user-specific endpoints

### API Key Authentication
- Include `X-API-Key: <your-api-key>` header
- Required for external API endpoints

## Educational Content

The API is specifically designed for educational content:

### SAT Questions
- Math, Reading, and Writing questions
- Multiple choice format with explanations
- Difficulty levels: easy, medium, hard

### UTBK Questions
- Indonesian university entrance exam questions
- Mathematics, Physics, Chemistry, Biology
- Indonesian language support

### Student Profiles
- Track student progress and preferences
- Identify weak and strong subjects
- Set study goals

## Key Endpoints

### LLM Operations
- `POST /llm/generate` - Generate text explanations
- `POST /llm/chat` - Interactive chat completion

### Vector Search
- `POST /search/hybrid` - Hybrid BM25 + semantic search
- `POST /search/questions` - Search educational questions
- `POST /search/materials` - Search study materials

### Content Management
- `POST /ingest` - Add documents to search index
- `POST /embedding/generate` - Generate text embeddings

### AI Agents
- `POST /agent/execute` - Execute AI agents with tools
- `GET /tools/list` - List available tools

### Authentication
- `POST /auth/login` - User login
- `POST /auth/register` - User registration
- `GET /me` - Get user profile

## Rate Limiting

- Default: 100 requests per minute per user/API key
- Exempt endpoints: `/health`, `/metrics`, `/docs`, `/openapi.json`, `/redoc`

## Error Handling

All endpoints return consistent error responses:

```json
{
  "detail": "Error message",
  "error_code": "ERROR_CODE",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## Support

For questions and support:
- Email: support@nlp-ai-microservice.com
- GitHub: https://github.com/your-org/nlp-ai-microservice
