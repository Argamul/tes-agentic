from typing import Any, Dict, Optional, List
import os
import asyncio
import logging
from datetime import datetime

# Optional gRPC dependencies; guard imports for environments without stubs
try:
	import grpc  # type: ignore
	from grpc import aio  # type: ignore
except Exception:  # pragma: no cover
	grpc = None  # type: ignore
	aio = None  # type: ignore

# Try to import generated stubs
try:
	from generated import user_service_pb2
	from generated import user_service_pb2_grpc
	from generated import question_service_pb2
	from generated import question_service_pb2_grpc
	from generated import api_gateway_pb2
	from generated import api_gateway_pb2_grpc
	GRPC_STUBS_AVAILABLE = True
except ImportError:
	GRPC_STUBS_AVAILABLE = False
	# Create mock stubs for development
	user_service_pb2 = None
	user_service_pb2_grpc = None
	question_service_pb2 = None
	question_service_pb2_grpc = None
	api_gateway_pb2 = None
	api_gateway_pb2_grpc = None

logger = logging.getLogger(__name__)


class BaseGRPCClient:
	def __init__(self, target_env: str, default_target: str, service_name: str):
		self.target = os.getenv(target_env, default_target)
		self.service_name = service_name
		self._channel = None
		self._stub = None
		self._connected = False
		self._connection_lock = asyncio.Lock()

	async def connect(self):
		"""Establish gRPC connection"""
		if grpc is None:
			raise RuntimeError("gRPC not available in this environment")
		
		async with self._connection_lock:
			if self._connected:
				return
			
			try:
				# Create secure channel if TLS is configured
				tls_enabled = os.getenv("GRPC_TLS_ENABLED", "false").lower() in {"1", "true", "yes"}
				
				if tls_enabled:
					# Load TLS credentials
					cert_file = os.getenv("GRPC_CERT_FILE")
					key_file = os.getenv("GRPC_KEY_FILE")
					ca_file = os.getenv("GRPC_CA_FILE")
					
					if cert_file and key_file:
						# Client certificate authentication
						with open(cert_file, 'rb') as f:
							cert = f.read()
						with open(key_file, 'rb') as f:
							key = f.read()
						
						if ca_file:
							with open(ca_file, 'rb') as f:
								ca = f.read()
							credentials = grpc.ssl_channel_credentials(ca, key, cert)
						else:
							credentials = grpc.ssl_channel_credentials(key, cert)
						
						self._channel = aio.secure_channel(self.target, credentials)
					else:
						# Server certificate verification only
						credentials = grpc.ssl_channel_credentials()
						self._channel = aio.secure_channel(self.target, credentials)
				else:
					# Insecure channel
					self._channel = aio.insecure_channel(self.target)
				
				self._connected = True
				logger.info(f"Connected to {self.service_name} gRPC service at {self.target}")
				
			except Exception as e:
				logger.error(f"Failed to connect to {self.service_name} gRPC service: {e}")
				raise

	async def aclose(self):
		"""Close gRPC connection"""
		if self._channel is not None:
			await self._channel.close()
			self._connected = False
			logger.info(f"Disconnected from {self.service_name} gRPC service")

	async def _ensure_connected(self):
		"""Ensure gRPC connection is established"""
		if not self._connected:
			await self.connect()


class UserServiceGRPCClient(BaseGRPCClient):
	def __init__(self):
		super().__init__("USER_SERVICE_GRPC_TARGET", "localhost:50051", "UserService")
		self._stub = None

	async def _get_stub(self):
		"""Get or create gRPC stub"""
		if not GRPC_STUBS_AVAILABLE:
			raise RuntimeError("gRPC stubs not available. Run scripts/generate_grpc_stubs.py first")
		
		await self._ensure_connected()
		if self._stub is None:
			self._stub = user_service_pb2_grpc.UserServiceStub(self._channel)
		return self._stub

	async def get_user(self, user_id: str) -> Dict[str, Any]:
		"""Get user by ID"""
		try:
			stub = await self._get_stub()
			request = user_service_pb2.GetUserRequest(user_id=user_id)
			response = await stub.GetUser(request)
			
			if response.success:
				return {
					"id": response.user.id,
					"email": response.user.email,
					"username": response.user.username,
					"first_name": response.user.first_name,
					"last_name": response.user.last_name,
					"roles": list(response.user.roles),
					"permissions": list(response.user.permissions),
					"is_active": response.user.is_active,
					"created_at": response.user.created_at,
					"updated_at": response.user.updated_at,
					"metadata": dict(response.user.metadata)
				}
			else:
				raise Exception(f"Failed to get user: {response.message}")
		except Exception as e:
			logger.error(f"Error getting user {user_id}: {e}")
			raise

	async def create_user(self, email: str, username: str, password: str, 
						 first_name: str = "", last_name: str = "", 
						 roles: List[str] = None, metadata: Dict[str, str] = None) -> Dict[str, Any]:
		"""Create a new user"""
		try:
			stub = await self._get_stub()
			request = user_service_pb2.CreateUserRequest(
				email=email,
				username=username,
				password=password,
				first_name=first_name,
				last_name=last_name,
				roles=roles or [],
				metadata=metadata or {}
			)
			response = await stub.CreateUser(request)
			
			if response.success:
				return {
					"id": response.user.id,
					"email": response.user.email,
					"username": response.user.username,
					"first_name": response.user.first_name,
					"last_name": response.user.last_name,
					"roles": list(response.user.roles),
					"permissions": list(response.user.permissions),
					"is_active": response.user.is_active,
					"created_at": response.user.created_at,
					"updated_at": response.user.updated_at,
					"metadata": dict(response.user.metadata)
				}
			else:
				raise Exception(f"Failed to create user: {response.message}")
		except Exception as e:
			logger.error(f"Error creating user {email}: {e}")
			raise

	async def update_user(self, user_id: str, **kwargs) -> Dict[str, Any]:
		"""Update user information"""
		try:
			stub = await self._get_stub()
			request = user_service_pb2.UpdateUserRequest(
				user_id=user_id,
				email=kwargs.get("email", ""),
				username=kwargs.get("username", ""),
				first_name=kwargs.get("first_name", ""),
				last_name=kwargs.get("last_name", ""),
				roles=kwargs.get("roles", []),
				is_active=kwargs.get("is_active", True),
				metadata=kwargs.get("metadata", {})
			)
			response = await stub.UpdateUser(request)
			
			if response.success:
				return {
					"id": response.user.id,
					"email": response.user.email,
					"username": response.user.username,
					"first_name": response.user.first_name,
					"last_name": response.user.last_name,
					"roles": list(response.user.roles),
					"permissions": list(response.user.permissions),
					"is_active": response.user.is_active,
					"created_at": response.user.created_at,
					"updated_at": response.user.updated_at,
					"metadata": dict(response.user.metadata)
				}
			else:
				raise Exception(f"Failed to update user: {response.message}")
		except Exception as e:
			logger.error(f"Error updating user {user_id}: {e}")
			raise

	async def delete_user(self, user_id: str) -> bool:
		"""Delete a user"""
		try:
			stub = await self._get_stub()
			request = user_service_pb2.DeleteUserRequest(user_id=user_id)
			response = await stub.DeleteUser(request)
			
			if response.success:
				return True
			else:
				raise Exception(f"Failed to delete user: {response.message}")
		except Exception as e:
			logger.error(f"Error deleting user {user_id}: {e}")
			raise

	async def list_users(self, page: int = 1, page_size: int = 10, 
						filter_str: str = "", sort_by: str = "created_at", 
						sort_desc: bool = True) -> Dict[str, Any]:
		"""List users with pagination"""
		try:
			stub = await self._get_stub()
			request = user_service_pb2.ListUsersRequest(
				page=page,
				page_size=page_size,
				filter=filter_str,
				sort_by=sort_by,
				sort_desc=sort_desc
			)
			response = await stub.ListUsers(request)
			
			if response.success:
				users = []
				for user in response.users:
					users.append({
						"id": user.id,
						"email": user.email,
						"username": user.username,
						"first_name": user.first_name,
						"last_name": user.last_name,
						"roles": list(user.roles),
						"permissions": list(user.permissions),
						"is_active": user.is_active,
						"created_at": user.created_at,
						"updated_at": user.updated_at,
						"metadata": dict(user.metadata)
					})
				
				return {
					"users": users,
					"total_count": response.total_count,
					"page": response.page,
					"page_size": response.page_size
				}
			else:
				raise Exception(f"Failed to list users: {response.message}")
		except Exception as e:
			logger.error(f"Error listing users: {e}")
			raise

	async def authenticate_user(self, email: str, password: str) -> Dict[str, Any]:
		"""Authenticate user and get tokens"""
		try:
			stub = await self._get_stub()
			request = user_service_pb2.AuthenticateUserRequest(
				email=email,
				password=password
			)
			response = await stub.AuthenticateUser(request)
			
			if response.success:
				return {
					"access_token": response.access_token,
					"refresh_token": response.refresh_token,
					"expires_in": response.expires_in,
					"user": {
						"id": response.user.id,
						"email": response.user.email,
						"username": response.user.username,
						"first_name": response.user.first_name,
						"last_name": response.user.last_name,
						"roles": list(response.user.roles),
						"permissions": list(response.user.permissions),
						"is_active": response.user.is_active,
						"created_at": response.user.created_at,
						"updated_at": response.user.updated_at,
						"metadata": dict(response.user.metadata)
					}
				}
			else:
				raise Exception(f"Authentication failed: {response.message}")
		except Exception as e:
			logger.error(f"Error authenticating user {email}: {e}")
			raise

	async def validate_token(self, token: str) -> Dict[str, Any]:
		"""Validate JWT token"""
		try:
			stub = await self._get_stub()
			request = user_service_pb2.ValidateTokenRequest(token=token)
			response = await stub.ValidateToken(request)
			
			if response.success and response.is_valid:
				return {
					"is_valid": response.is_valid,
					"expires_at": response.expires_at,
					"user": {
						"id": response.user.id,
						"email": response.user.email,
						"username": response.user.username,
						"first_name": response.user.first_name,
						"last_name": response.user.last_name,
						"roles": list(response.user.roles),
						"permissions": list(response.user.permissions),
						"is_active": response.user.is_active,
						"created_at": response.user.created_at,
						"updated_at": response.user.updated_at,
						"metadata": dict(response.user.metadata)
					}
				}
			else:
				return {
					"is_valid": False,
					"expires_at": 0,
					"user": None
				}
		except Exception as e:
			logger.error(f"Error validating token: {e}")
			raise


class QuestionServiceGRPCClient(BaseGRPCClient):
	def __init__(self):
		super().__init__("QUESTION_SERVICE_GRPC_TARGET", "localhost:50052", "QuestionService")
		self._stub = None

	async def _get_stub(self):
		"""Get or create gRPC stub"""
		if not GRPC_STUBS_AVAILABLE:
			raise RuntimeError("gRPC stubs not available. Run scripts/generate_grpc_stubs.py first")
		
		await self._ensure_connected()
		if self._stub is None:
			self._stub = question_service_pb2_grpc.QuestionServiceStub(self._channel)
		return self._stub

	async def get_question(self, question_id: str) -> Dict[str, Any]:
		"""Get question by ID"""
		try:
			stub = await self._get_stub()
			request = question_service_pb2.GetQuestionRequest(question_id=question_id)
			response = await stub.GetQuestion(request)
			
			if response.success:
				return {
					"id": response.question.id,
					"user_id": response.question.user_id,
					"title": response.question.title,
					"content": response.question.content,
					"type": response.question.type,
					"category": response.question.category,
					"tags": list(response.question.tags),
					"difficulty": response.question.difficulty,
					"created_at": response.question.created_at,
					"updated_at": response.question.updated_at,
					"is_answered": response.question.is_answered,
					"answer_count": response.question.answer_count,
					"view_count": response.question.view_count,
					"metadata": dict(response.question.metadata)
				}
			else:
				raise Exception(f"Failed to get question: {response.message}")
		except Exception as e:
			logger.error(f"Error getting question {question_id}: {e}")
			raise

	async def create_question(self, user_id: str, title: str, content: str,
							type: str = "general", category: str = "general",
							tags: List[str] = None, difficulty: str = "medium",
							metadata: Dict[str, str] = None) -> Dict[str, Any]:
		"""Create a new question"""
		try:
			stub = await self._get_stub()
			request = question_service_pb2.CreateQuestionRequest(
				user_id=user_id,
				title=title,
				content=content,
				type=type,
				category=category,
				tags=tags or [],
				difficulty=difficulty,
				metadata=metadata or {}
			)
			response = await stub.CreateQuestion(request)
			
			if response.success:
				return {
					"id": response.question.id,
					"user_id": response.question.user_id,
					"title": response.question.title,
					"content": response.question.content,
					"type": response.question.type,
					"category": response.question.category,
					"tags": list(response.question.tags),
					"difficulty": response.question.difficulty,
					"created_at": response.question.created_at,
					"updated_at": response.question.updated_at,
					"is_answered": response.question.is_answered,
					"answer_count": response.question.answer_count,
					"view_count": response.question.view_count,
					"metadata": dict(response.question.metadata)
				}
			else:
				raise Exception(f"Failed to create question: {response.message}")
		except Exception as e:
			logger.error(f"Error creating question: {e}")
			raise

	async def get_user_questions(self, user_id: str, page: int = 1, page_size: int = 10,
							   sort_by: str = "created_at", sort_desc: bool = True) -> Dict[str, Any]:
		"""Get questions by user ID"""
		try:
			stub = await self._get_stub()
			request = question_service_pb2.GetUserQuestionsRequest(
				user_id=user_id,
				page=page,
				page_size=page_size,
				sort_by=sort_by,
				sort_desc=sort_desc
			)
			response = await stub.GetUserQuestions(request)
			
			if response.success:
				questions = []
				for question in response.questions:
					questions.append({
						"id": question.id,
						"user_id": question.user_id,
						"title": question.title,
						"content": question.content,
						"type": question.type,
						"category": question.category,
						"tags": list(question.tags),
						"difficulty": question.difficulty,
						"created_at": question.created_at,
						"updated_at": question.updated_at,
						"is_answered": question.is_answered,
						"answer_count": question.answer_count,
						"view_count": question.view_count,
						"metadata": dict(question.metadata)
					})
				
				return {
					"questions": questions,
					"total_count": response.total_count,
					"page": response.page,
					"page_size": response.page_size
				}
			else:
				raise Exception(f"Failed to get user questions: {response.message}")
		except Exception as e:
			logger.error(f"Error getting user questions for {user_id}: {e}")
			raise

	async def search_questions(self, query: str, page: int = 1, page_size: int = 10,
							 category: str = "", type: str = "", difficulty: str = "",
							 tags: List[str] = None, sort_by: str = "created_at",
							 sort_desc: bool = True) -> Dict[str, Any]:
		"""Search questions"""
		try:
			stub = await self._get_stub()
			request = question_service_pb2.SearchQuestionsRequest(
				query=query,
				page=page,
				page_size=page_size,
				category=category,
				type=type,
				difficulty=difficulty,
				tags=tags or [],
				sort_by=sort_by,
				sort_desc=sort_desc
			)
			response = await stub.SearchQuestions(request)
			
			if response.success:
				questions = []
				for question in response.questions:
					questions.append({
						"id": question.id,
						"user_id": question.user_id,
						"title": question.title,
						"content": question.content,
						"type": question.type,
						"category": question.category,
						"tags": list(question.tags),
						"difficulty": question.difficulty,
						"created_at": question.created_at,
						"updated_at": question.updated_at,
						"is_answered": question.is_answered,
						"answer_count": question.answer_count,
						"view_count": question.view_count,
						"metadata": dict(question.metadata)
					})
				
				return {
					"questions": questions,
					"total_count": response.total_count,
					"page": response.page,
					"page_size": response.page_size
				}
			else:
				raise Exception(f"Failed to search questions: {response.message}")
		except Exception as e:
			logger.error(f"Error searching questions: {e}")
			raise


class APIGatewayGRPCClient(BaseGRPCClient):
	def __init__(self):
		super().__init__("API_GATEWAY_GRPC_TARGET", "localhost:50053", "APIGateway")
		self._stub = None

	async def _get_stub(self):
		"""Get or create gRPC stub"""
		if not GRPC_STUBS_AVAILABLE:
			raise RuntimeError("gRPC stubs not available. Run scripts/generate_grpc_stubs.py first")
		
		await self._ensure_connected()
		if self._stub is None:
			self._stub = api_gateway_pb2_grpc.APIGatewayStub(self._channel)
		return self._stub

	async def proxy_request(self, method: str, path: str, headers: Dict[str, str] = None,
						  body: str = "", query_params: Dict[str, str] = None,
						  target_service: str = "", timeout_seconds: int = 30) -> Dict[str, Any]:
		"""Proxy request through API Gateway"""
		try:
			stub = await self._get_stub()
			request = api_gateway_pb2.ProxyRequestMessage(
				method=method,
				path=path,
				headers=headers or {},
				body=body,
				query_params=query_params or {},
				target_service=target_service,
				timeout_seconds=timeout_seconds
			)
			response = await stub.ProxyRequest(request)
			
			return {
				"success": response.success,
				"status_code": response.status_code,
				"message": response.message,
				"headers": dict(response.headers),
				"body": response.body,
				"response_time_ms": response.response_time_ms
			}
		except Exception as e:
			logger.error(f"Error proxying request: {e}")
			raise

	async def validate_request(self, method: str, path: str, headers: Dict[str, str] = None,
							 body: str = "", user_id: str = "", user_roles: List[str] = None,
							 user_permissions: List[str] = None) -> Dict[str, Any]:
		"""Validate request authorization"""
		try:
			stub = await self._get_stub()
			request = api_gateway_pb2.ValidateRequestMessage(
				method=method,
				path=path,
				headers=headers or {},
				body=body,
				user_id=user_id,
				user_roles=user_roles or [],
				user_permissions=user_permissions or []
			)
			response = await stub.ValidateRequest(request)
			
			return {
				"success": response.success,
				"message": response.message,
				"is_authorized": response.is_authorized,
				"required_permissions": list(response.required_permissions),
				"missing_permissions": list(response.missing_permissions)
			}
		except Exception as e:
			logger.error(f"Error validating request: {e}")
			raise

	async def get_service_health(self, service_name: str) -> Dict[str, Any]:
		"""Get service health status"""
		try:
			stub = await self._get_stub()
			request = api_gateway_pb2.GetServiceHealthRequest(service_name=service_name)
			response = await stub.GetServiceHealth(request)
			
			return {
				"success": response.success,
				"message": response.message,
				"service_name": response.service_name,
				"status": response.status,
				"last_check": response.last_check,
				"health_details": dict(response.health_details)
			}
		except Exception as e:
			logger.error(f"Error getting service health: {e}")
			raise

	async def rate_limit_check(self, user_id: str = "", api_key: str = "",
							 endpoint: str = "", service_name: str = "") -> Dict[str, Any]:
		"""Check rate limit for request"""
		try:
			stub = await self._get_stub()
			request = api_gateway_pb2.RateLimitCheckRequest(
				user_id=user_id,
				api_key=api_key,
				endpoint=endpoint,
				service_name=service_name
			)
			response = await stub.RateLimitCheck(request)
			
			return {
				"success": response.success,
				"message": response.message,
				"is_allowed": response.is_allowed,
				"remaining_requests": response.remaining_requests,
				"reset_time": response.reset_time,
				"limit": response.limit
			}
		except Exception as e:
			logger.error(f"Error checking rate limit: {e}")
			raise



