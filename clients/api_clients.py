import os
import asyncio
import logging
from typing import Any, Dict, Optional, List
import httpx
from datetime import datetime

from .service_discovery import discover_service

logger = logging.getLogger(__name__)


class BaseAPIClient:
	def __init__(self, service_name: str, default_env: Optional[str] = None, timeout_seconds: float = 5.0):
		self.service_name = service_name
		self.base_url = discover_service(service_name, default_env) or ""
		self.timeout = timeout_seconds
		self._client = None
		self._connection_lock = asyncio.Lock()
		
		# TLS configuration
		verify_env = os.getenv("OUTBOUND_TLS_VERIFY", "true").lower() in {"1", "true", "yes"}
		ca_bundle = os.getenv("OUTBOUND_CA_BUNDLE")
		verify: Any
		if not verify_env:
			verify = False
		elif ca_bundle:
			verify = ca_bundle
		else:
			verify = True
		
		client_cert = os.getenv("OUTBOUND_CLIENT_CERT")
		client_key = os.getenv("OUTBOUND_CLIENT_KEY")
		cert = (client_cert, client_key) if client_cert and client_key else None
		
		# Store client configuration for lazy initialization
		self._client_config = {
			"timeout": self.timeout,
			"verify": verify,
			"cert": cert
		}

	async def _get_client(self) -> httpx.AsyncClient:
		"""Get or create HTTP client with lazy initialization"""
		if self._client is None:
			async with self._connection_lock:
				if self._client is None:
					self._client = httpx.AsyncClient(**self._client_config)
		return self._client

	async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
		if not self.base_url:
			raise RuntimeError(f"Service URL for {self.service_name} not configured")
		
		url = self.base_url.rstrip("/") + "/" + path.lstrip("/")
		client = await self._get_client()
		
		# Add default headers
		headers = kwargs.get("headers", {})
		headers.setdefault("User-Agent", f"{self.service_name}-client/1.0")
		headers.setdefault("Content-Type", "application/json")
		kwargs["headers"] = headers
		
		try:
			response = await client.request(method, url, **kwargs)
			response.raise_for_status()
			return response
		except httpx.HTTPStatusError as e:
			logger.error(f"HTTP error for {self.service_name}: {e.response.status_code} - {e.response.text}")
			raise
		except httpx.RequestError as e:
			logger.error(f"Request error for {self.service_name}: {e}")
			raise

	async def aclose(self):
		"""Close HTTP client"""
		if self._client is not None:
			await self._client.aclose()
			self._client = None


class UserServiceClient(BaseAPIClient):
	def __init__(self):
		super().__init__("USER_SERVICE", default_env="USER_SERVICE_URL", timeout_seconds=float(os.getenv("USER_SERVICE_TIMEOUT_SECONDS", "5")))

	async def get_user(self, user_id: str) -> Dict[str, Any]:
		"""Get user by ID"""
		resp = await self._request("GET", f"/users/{user_id}")
		return resp.json()

	async def create_user(self, email: str, username: str, password: str, 
						 first_name: str = "", last_name: str = "", 
						 roles: List[str] = None, metadata: Dict[str, str] = None) -> Dict[str, Any]:
		"""Create a new user"""
		data = {
			"email": email,
			"username": username,
			"password": password,
			"first_name": first_name,
			"last_name": last_name,
			"roles": roles or [],
			"metadata": metadata or {}
		}
		resp = await self._request("POST", "/users", json=data)
		return resp.json()

	async def update_user(self, user_id: str, **kwargs) -> Dict[str, Any]:
		"""Update user information"""
		resp = await self._request("PUT", f"/users/{user_id}", json=kwargs)
		return resp.json()

	async def delete_user(self, user_id: str) -> bool:
		"""Delete a user"""
		resp = await self._request("DELETE", f"/users/{user_id}")
		return resp.status_code == 204

	async def list_users(self, page: int = 1, page_size: int = 10, 
						filter_str: str = "", sort_by: str = "created_at", 
						sort_desc: bool = True) -> Dict[str, Any]:
		"""List users with pagination"""
		params = {
			"page": page,
			"page_size": page_size,
			"filter": filter_str,
			"sort_by": sort_by,
			"sort_desc": sort_desc
		}
		resp = await self._request("GET", "/users", params=params)
		return resp.json()

	async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
		"""Get user profile with additional data"""
		resp = await self._request("GET", f"/users/{user_id}/profile")
		return resp.json()

	async def update_user_profile(self, user_id: str, profile_data: Dict[str, Any]) -> Dict[str, Any]:
		"""Update user profile"""
		resp = await self._request("PUT", f"/users/{user_id}/profile", json=profile_data)
		return resp.json()

	async def authenticate_user(self, email: str, password: str) -> Dict[str, Any]:
		"""Authenticate user and get tokens"""
		data = {"email": email, "password": password}
		resp = await self._request("POST", "/auth/login", json=data)
		return resp.json()

	async def validate_token(self, token: str) -> Dict[str, Any]:
		"""Validate JWT token"""
		headers = {"Authorization": f"Bearer {token}"}
		resp = await self._request("POST", "/auth/validate", headers=headers)
		return resp.json()

	async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
		"""Refresh access token"""
		data = {"refresh_token": refresh_token}
		resp = await self._request("POST", "/auth/refresh", json=data)
		return resp.json()

	async def revoke_token(self, token: str) -> bool:
		"""Revoke a token"""
		headers = {"Authorization": f"Bearer {token}"}
		resp = await self._request("POST", "/auth/revoke", headers=headers)
		return resp.status_code == 200


class QuestionServiceClient(BaseAPIClient):
	def __init__(self):
		super().__init__("QUESTION_SERVICE", default_env="QUESTION_SERVICE_URL", timeout_seconds=float(os.getenv("QUESTION_SERVICE_TIMEOUT_SECONDS", "5")))

	async def get_question(self, question_id: str) -> Dict[str, Any]:
		"""Get question by ID"""
		resp = await self._request("GET", f"/questions/{question_id}")
		return resp.json()

	async def create_question(self, user_id: str, title: str, content: str,
							type: str = "general", category: str = "general",
							tags: List[str] = None, difficulty: str = "medium",
							metadata: Dict[str, str] = None) -> Dict[str, Any]:
		"""Create a new question"""
		data = {
			"user_id": user_id,
			"title": title,
			"content": content,
			"type": type,
			"category": category,
			"tags": tags or [],
			"difficulty": difficulty,
			"metadata": metadata or {}
		}
		resp = await self._request("POST", "/questions", json=data)
		return resp.json()

	async def update_question(self, question_id: str, **kwargs) -> Dict[str, Any]:
		"""Update question"""
		resp = await self._request("PUT", f"/questions/{question_id}", json=kwargs)
		return resp.json()

	async def delete_question(self, question_id: str) -> bool:
		"""Delete a question"""
		resp = await self._request("DELETE", f"/questions/{question_id}")
		return resp.status_code == 204

	async def list_questions(self, page: int = 1, page_size: int = 10,
						   category: str = "", type: str = "", difficulty: str = "",
						   tags: List[str] = None, sort_by: str = "created_at",
						   sort_desc: bool = True) -> Dict[str, Any]:
		"""List questions with filters"""
		params = {
			"page": page,
			"page_size": page_size,
			"category": category,
			"type": type,
			"difficulty": difficulty,
			"sort_by": sort_by,
			"sort_desc": sort_desc
		}
		if tags:
			params["tags"] = ",".join(tags)
		
		resp = await self._request("GET", "/questions", params=params)
		return resp.json()

	async def get_user_questions(self, user_id: str, page: int = 1, page_size: int = 10,
							   sort_by: str = "created_at", sort_desc: bool = True) -> Dict[str, Any]:
		"""Get questions by user ID"""
		params = {
			"page": page,
			"page_size": page_size,
			"sort_by": sort_by,
			"sort_desc": sort_desc
		}
		resp = await self._request("GET", f"/users/{user_id}/questions", params=params)
		return resp.json()

	async def search_questions(self, query: str, page: int = 1, page_size: int = 10,
							 category: str = "", type: str = "", difficulty: str = "",
							 tags: List[str] = None, sort_by: str = "created_at",
							 sort_desc: bool = True) -> Dict[str, Any]:
		"""Search questions"""
		params = {
			"q": query,
			"page": page,
			"page_size": page_size,
			"category": category,
			"type": type,
			"difficulty": difficulty,
			"sort_by": sort_by,
			"sort_desc": sort_desc
		}
		if tags:
			params["tags"] = ",".join(tags)
		
		resp = await self._request("GET", "/questions/search", params=params)
		return resp.json()

	async def get_question_answers(self, question_id: str, page: int = 1, page_size: int = 10,
								 sort_by: str = "created_at", sort_desc: bool = True) -> Dict[str, Any]:
		"""Get answers for a question"""
		params = {
			"page": page,
			"page_size": page_size,
			"sort_by": sort_by,
			"sort_desc": sort_desc
		}
		resp = await self._request("GET", f"/questions/{question_id}/answers", params=params)
		return resp.json()

	async def create_answer(self, question_id: str, user_id: str, content: str,
						  metadata: Dict[str, str] = None) -> Dict[str, Any]:
		"""Create an answer to a question"""
		data = {
			"question_id": question_id,
			"user_id": user_id,
			"content": content,
			"metadata": metadata or {}
		}
		resp = await self._request("POST", f"/questions/{question_id}/answers", json=data)
		return resp.json()

	async def update_answer(self, answer_id: str, content: str, metadata: Dict[str, str] = None) -> Dict[str, Any]:
		"""Update an answer"""
		data = {
			"content": content,
			"metadata": metadata or {}
		}
		resp = await self._request("PUT", f"/answers/{answer_id}", json=data)
		return resp.json()

	async def delete_answer(self, answer_id: str) -> bool:
		"""Delete an answer"""
		resp = await self._request("DELETE", f"/answers/{answer_id}")
		return resp.status_code == 204


class APIGatewayClient(BaseAPIClient):
	def __init__(self):
		super().__init__("API_GATEWAY", default_env="API_GATEWAY_URL", timeout_seconds=float(os.getenv("API_GATEWAY_TIMEOUT_SECONDS", "5")))

	async def proxy(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
		"""Proxy request through API Gateway"""
		resp = await self._request(method, path, **kwargs)
		return resp.json()

	async def route_request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
		"""Route request through API Gateway with routing logic"""
		data = {
			"method": method,
			"path": path,
			**kwargs
		}
		resp = await self._request("POST", "/gateway/route", json=data)
		return resp.json()

	async def validate_request(self, method: str, path: str, user_id: str = "",
							 user_roles: List[str] = None, user_permissions: List[str] = None) -> Dict[str, Any]:
		"""Validate request authorization through API Gateway"""
		data = {
			"method": method,
			"path": path,
			"user_id": user_id,
			"user_roles": user_roles or [],
			"user_permissions": user_permissions or []
		}
		resp = await self._request("POST", "/gateway/validate", json=data)
		return resp.json()

	async def get_service_health(self, service_name: str) -> Dict[str, Any]:
		"""Get service health status through API Gateway"""
		resp = await self._request("GET", f"/gateway/health/{service_name}")
		return resp.json()

	async def get_service_metrics(self, service_name: str, start_time: Optional[datetime] = None,
								end_time: Optional[datetime] = None) -> Dict[str, Any]:
		"""Get service metrics through API Gateway"""
		params = {}
		if start_time:
			params["start_time"] = start_time.isoformat()
		if end_time:
			params["end_time"] = end_time.isoformat()
		
		resp = await self._request("GET", f"/gateway/metrics/{service_name}", params=params)
		return resp.json()

	async def rate_limit_check(self, user_id: str = "", api_key: str = "",
							 endpoint: str = "", service_name: str = "") -> Dict[str, Any]:
		"""Check rate limit through API Gateway"""
		data = {
			"user_id": user_id,
			"api_key": api_key,
			"endpoint": endpoint,
			"service_name": service_name
		}
		resp = await self._request("POST", "/gateway/rate-limit/check", json=data)
		return resp.json()

	async def load_balance_request(self, service_name: str, request_id: str = "",
								 request_context: Dict[str, str] = None) -> Dict[str, Any]:
		"""Get load balanced service instance through API Gateway"""
		data = {
			"service_name": service_name,
			"request_id": request_id,
			"request_context": request_context or {}
		}
		resp = await self._request("POST", "/gateway/load-balance", json=data)
		return resp.json()



