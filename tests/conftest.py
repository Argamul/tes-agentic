import sys
import os
import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List, Any

# Ensure project root is on sys.path for imports like `vector_db.*`
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Set test environment variables
os.environ["ENVIRONMENT"] = "test"
os.environ["LOG_LEVEL"] = "DEBUG"
os.environ["OPENAI_API_KEY"] = "test-key"
os.environ["ANTHROPIC_API_KEY"] = "test-key"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["ELASTICSEARCH_URL"] = "http://localhost:9200"
os.environ["QDRANT_URL"] = "http://localhost:6333"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_openai():
    """Mock OpenAI API responses"""
    with patch('openai.AsyncOpenAI') as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        
        # Mock completion response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "This is a test response from OpenAI"
        mock_instance.chat.completions.create.return_value = mock_response
        
        yield mock_instance


@pytest.fixture
def mock_anthropic():
    """Mock Anthropic API responses"""
    with patch('anthropic.AsyncAnthropic') as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        
        # Mock message response
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = "This is a test response from Claude"
        mock_instance.messages.create.return_value = mock_response
        
        yield mock_instance


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    with patch('redis.Redis') as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        mock_instance.ping.return_value = True
        mock_instance.get.return_value = None
        mock_instance.set.return_value = True
        mock_instance.delete.return_value = 1
        
        yield mock_instance


@pytest.fixture
def mock_elasticsearch():
    """Mock Elasticsearch client"""
    with patch('elasticsearch.AsyncElasticsearch') as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        
        # Mock search response
        mock_response = {
            "hits": {
                "hits": [
                    {
                        "_id": "1",
                        "_source": {"text": "Test document", "metadata": {"type": "question"}},
                        "_score": 0.9
                    }
                ],
                "total": {"value": 1}
            }
        }
        mock_instance.search.return_value = mock_response
        mock_instance.index.return_value = {"_id": "1", "result": "created"}
        
        yield mock_instance


@pytest.fixture
def mock_qdrant():
    """Mock Qdrant client"""
    with patch('qdrant_client.QdrantClient') as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        
        # Mock search response
        mock_response = MagicMock()
        mock_response.points = [
            MagicMock(
                id="1",
                payload={"text": "Test document", "metadata": {"type": "question"}},
                score=0.8
            )
        ]
        mock_instance.search.return_value = mock_response
        mock_instance.upsert.return_value = MagicMock(operation_id="test_op")
        
        yield mock_instance


@pytest.fixture
def mock_httpx():
    """Mock httpx client for external API calls"""
    with patch('httpx.AsyncClient') as mock:
        mock_instance = MagicMock()
        mock.return_value.__aenter__.return_value = mock_instance
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success", "data": "test"}
        mock_instance.get.return_value = mock_response
        mock_instance.post.return_value = mock_response
        
        yield mock_instance


@pytest.fixture
def sat_utbk_test_data():
    """SAT/UTBK test data fixture"""
    return {
        "sat_math_questions": [
            {
                "id": "sat_math_001",
                "text": "If 2x + 3y = 12 and x - y = 1, what is the value of x?",
                "type": "math",
                "difficulty": "medium",
                "subject": "algebra",
                "answer_choices": ["A) 3", "B) 4", "C) 5", "D) 6"],
                "correct_answer": "A"
            }
        ],
        "utbk_questions": [
            {
                "id": "utbk_math_001",
                "text": "Jika f(x) = x² + 2x - 3, maka nilai f(-1) adalah...",
                "type": "math",
                "difficulty": "easy",
                "subject": "matematika",
                "language": "indonesian",
                "answer_choices": ["A) -4", "B) -2", "C) 0", "D) 2"],
                "correct_answer": "A"
            }
        ],
        "student_profiles": [
            {
                "id": "student_001",
                "name": "Alice Johnson",
                "email": "alice.johnson@example.com",
                "grade": "12",
                "target_university": "MIT",
                "test_type": "SAT"
            }
        ]
    }


@pytest.fixture
def mock_services():
    """Comprehensive mock services fixture"""
    services = {}
    
    with patch('main.user_client') as mock_user, \
         patch('main.question_client') as mock_question, \
         patch('main.api_gateway_client') as mock_gateway, \
         patch('main.llm_service') as mock_llm, \
         patch('main.embedding_service') as mock_embedding, \
         patch('main.bm25_service') as mock_bm25, \
         patch('main.qdrant_service') as mock_qdrant, \
         patch('main.agent_service') as mock_agent, \
         patch('main.tool_registry') as mock_tools:
        
        # Configure mock responses
        mock_user.get_user.return_value = {"id": "student_001", "name": "Test Student"}
        mock_user.get_user_profile.return_value = {"study_plan": "intensive_math"}
        
        mock_question.get_user_questions.return_value = {
            "questions": [{"id": "1", "text": "Test question", "type": "math"}]
        }
        
        mock_gateway.proxy.return_value = {"status": "success"}
        
        mock_llm.generate_text.return_value = "This is a generated explanation."
        mock_llm.chat_completion.return_value = "Here's how to solve this step by step..."
        
        mock_embedding.generate_embedding.return_value = [0.1, 0.2, 0.3, 0.4, 0.5]
        mock_embedding.generate_batch_embeddings.return_value = [
            [0.1, 0.2, 0.3], [0.4, 0.5, 0.6]
        ]
        
        mock_bm25.add_documents_batch.return_value = ["doc_1", "doc_2"]
        mock_bm25.search.return_value = [
            {"id": "1", "document": "Test document", "score": 0.9, "metadata": {"type": "question"}}
        ]
        
        mock_qdrant.add_documents_batch.return_value = ["qdrant_1", "qdrant_2"]
        mock_qdrant.search.return_value = [
            {"id": "1", "document": "Test document", "score": 0.8, "metadata": {"type": "question"}}
        ]
        
        mock_agent.execute.return_value = "I'll help you solve this step by step."
        
        mock_tools.list_tools.return_value = [
            {"name": "calculator", "description": "Mathematical calculations"},
            {"name": "text_analysis", "description": "Text metrics and analysis"}
        ]
        mock_tools.execute_tool.return_value = {"result": "Tool execution result"}
        
        services.update({
            "user": mock_user,
            "question": mock_question,
            "gateway": mock_gateway,
            "llm": mock_llm,
            "embedding": mock_embedding,
            "bm25": mock_bm25,
            "qdrant": mock_qdrant,
            "agent": mock_agent,
            "tools": mock_tools
        })
        
        yield services


@pytest.fixture
def test_client():
    """FastAPI test client"""
    from main import app
    from fastapi.testclient import TestClient
    return TestClient(app)


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test names"""
    for item in items:
        if "test_e2e" in item.nodeid:
            item.add_marker(pytest.mark.e2e)
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        if "performance" in item.nodeid or "large" in item.nodeid:
            item.add_marker(pytest.mark.slow)

