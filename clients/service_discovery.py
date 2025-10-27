import os
import asyncio
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ServiceDiscovery:
    """Enhanced service discovery with caching and multiple backends"""
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = int(os.getenv("SERVICE_DISCOVERY_CACHE_TTL_SECONDS", "30"))
        self._consul_client = None
        self._istio_enabled = os.getenv("USE_ISTIO_DNS", "false").lower() in {"1", "true", "yes"}
        
    def _is_cache_valid(self, service_name: str) -> bool:
        """Check if cached service info is still valid"""
        if service_name not in self._cache:
            return False
        
        cached_time = self._cache[service_name].get("cached_at")
        if not cached_time:
            return False
        
        return datetime.now() - cached_time < timedelta(seconds=self._cache_ttl)
    
    def _cache_service(self, service_name: str, url: str, metadata: Dict[str, Any] = None):
        """Cache service discovery result"""
        self._cache[service_name] = {
            "url": url,
            "cached_at": datetime.now(),
            "metadata": metadata or {}
        }
    
    def _get_cached_service(self, service_name: str) -> Optional[str]:
        """Get cached service URL if valid"""
        if self._is_cache_valid(service_name):
            return self._cache[service_name]["url"]
        return None
    
    async def _discover_consul_service(self, service_name: str) -> Optional[str]:
        """Discover service using Consul HTTP API"""
        consul_host = os.getenv("CONSUL_HOST")
        consul_port = os.getenv("CONSUL_PORT", "8500")
        consul_token = os.getenv("CONSUL_TOKEN")
        
        if not consul_host:
            return None
        
        try:
            import httpx
            
            headers = {}
            if consul_token:
                headers["X-Consul-Token"] = consul_token
            
            async with httpx.AsyncClient(timeout=float(os.getenv("CONSUL_HTTP_TIMEOUT_SECONDS", "2"))) as client:
                # Try health check endpoint first
                url = f"http://{consul_host}:{consul_port}/v1/health/service/{service_name}?passing=true"
                resp = await client.get(url, headers=headers)
                
                if resp.status_code == 200:
                    services = resp.json()
                    if services:
                        # Get the first healthy service
                        svc = services[0].get("Service", {})
                        address = svc.get("Address") or "localhost"
                        port = svc.get("Port") or 80
                        service_url = f"http://{address}:{port}"
                        
                        # Cache the result
                        self._cache_service(service_name, service_url, {
                            "discovery_method": "consul_health",
                            "service_id": svc.get("ID"),
                            "service_tags": svc.get("Tags", [])
                        })
                        
                        return service_url
                
                # Fallback to catalog service
                url = f"http://{consul_host}:{consul_port}/v1/catalog/service/{service_name}"
                resp = await client.get(url, headers=headers)
                
                if resp.status_code == 200:
                    services = resp.json()
                    if services:
                        svc = services[0]
                        address = svc.get("ServiceAddress") or svc.get("Address") or "localhost"
                        port = svc.get("ServicePort") or svc.get("Port") or 80
                        service_url = f"http://{address}:{port}"
                        
                        # Cache the result
                        self._cache_service(service_name, service_url, {
                            "discovery_method": "consul_catalog",
                            "service_id": svc.get("ServiceID"),
                            "service_tags": svc.get("ServiceTags", [])
                        })
                        
                        return service_url
                        
        except Exception as e:
            logger.warning(f"Consul service discovery failed for {service_name}: {e}")
        
        return None
    
    async def _discover_istio_service(self, service_name: str) -> Optional[str]:
        """Discover service using Istio/Kubernetes DNS"""
        if not self._istio_enabled:
            return None
        
        namespace = os.getenv("ISTIO_NAMESPACE", "default")
        cluster_domain = os.getenv("K8S_CLUSTER_DOMAIN", "cluster.local")
        
        # Standard Kubernetes service DNS
        service_url = f"http://{service_name}.{namespace}.svc.{cluster_domain}"
        
        # Cache the result
        self._cache_service(service_name, service_url, {
            "discovery_method": "istio_dns",
            "namespace": namespace,
            "cluster_domain": cluster_domain
        })
        
        return service_url
    
    async def _discover_etcd_service(self, service_name: str) -> Optional[str]:
        """Discover service using etcd"""
        etcd_host = os.getenv("ETCD_HOST")
        etcd_port = os.getenv("ETCD_PORT", "2379")
        
        if not etcd_host:
            return None
        
        try:
            import httpx
            
            async with httpx.AsyncClient(timeout=float(os.getenv("ETCD_HTTP_TIMEOUT_SECONDS", "2"))) as client:
                # etcd v3 API
                url = f"http://{etcd_host}:{etcd_port}/v3/kv/range"
                data = {
                    "key": f"/services/{service_name}".encode().hex()
                }
                
                resp = await client.post(url, json=data)
                if resp.status_code == 200:
                    result = resp.json()
                    if result.get("kvs"):
                        # Parse service info from etcd
                        service_info = result["kvs"][0]["value"]
                        # Assuming service info is stored as JSON
                        import json
                        service_data = json.loads(bytes.fromhex(service_info).decode())
                        service_url = service_data.get("url")
                        
                        if service_url:
                            self._cache_service(service_name, service_url, {
                                "discovery_method": "etcd",
                                "service_data": service_data
                            })
                            return service_url
                            
        except Exception as e:
            logger.warning(f"etcd service discovery failed for {service_name}: {e}")
        
        return None
    
    async def discover_service_async(
        self,
        service_name: str,
        default_url_env: Optional[str] = None,
        discovery_methods: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Async service discovery with multiple backends and caching
        
        Args:
            service_name: Name of the service to discover
            default_url_env: Environment variable name for fallback URL
            discovery_methods: List of discovery methods to try (consul, istio, etcd)
        
        Returns:
            Service URL or None if not found
        """
        # Check cache first
        cached_url = self._get_cached_service(service_name)
        if cached_url:
            logger.debug(f"Using cached service URL for {service_name}: {cached_url}")
            return cached_url
        
        # 1) Explicit URL environment variable
        explicit_url = os.getenv(f"{service_name.upper()}_URL")
        if explicit_url:
            self._cache_service(service_name, explicit_url, {"discovery_method": "explicit_env"})
            return explicit_url
        
        # Default discovery methods if not specified
        if discovery_methods is None:
            discovery_methods = ["consul", "istio", "etcd"]
        
        # Try each discovery method
        for method in discovery_methods:
            try:
                if method == "consul":
                    url = await self._discover_consul_service(service_name)
                elif method == "istio":
                    url = await self._discover_istio_service(service_name)
                elif method == "etcd":
                    url = await self._discover_etcd_service(service_name)
                else:
                    logger.warning(f"Unknown discovery method: {method}")
                    continue
                
                if url:
                    logger.info(f"Discovered {service_name} via {method}: {url}")
                    return url
                    
            except Exception as e:
                logger.warning(f"Service discovery method {method} failed for {service_name}: {e}")
        
        # 4) Fallback to default URL environment variable
        if default_url_env:
            fallback_url = os.getenv(default_url_env)
            if fallback_url:
                self._cache_service(service_name, fallback_url, {"discovery_method": "fallback_env"})
                return fallback_url
        
        logger.error(f"Could not discover service: {service_name}")
        return None
    
    def get_service_metadata(self, service_name: str) -> Dict[str, Any]:
        """Get cached service metadata"""
        if service_name in self._cache:
            return self._cache[service_name].get("metadata", {})
        return {}
    
    def clear_cache(self, service_name: Optional[str] = None):
        """Clear service discovery cache"""
        if service_name:
            self._cache.pop(service_name, None)
        else:
            self._cache.clear()


# Global service discovery instance
_service_discovery = ServiceDiscovery()


def discover_service(
    service_name: str,
    default_url_env: Optional[str] = None,
    consul_env_prefix: str = "CONSUL",
    istio_namespace_env: str = "ISTIO_NAMESPACE",
) -> Optional[str]:
    """
    Synchronous wrapper for service discovery
    
    This maintains backward compatibility with the original function signature
    while using the enhanced async implementation.
    """
    try:
        # Try to get the current event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an async context, we need to use a different approach
            # For now, fall back to the original synchronous implementation
            return _discover_service_sync(service_name, default_url_env, consul_env_prefix, istio_namespace_env)
        else:
            # We can run the async version
            return loop.run_until_complete(
                _service_discovery.discover_service_async(service_name, default_url_env)
            )
    except RuntimeError:
        # No event loop, fall back to sync implementation
        return _discover_service_sync(service_name, default_url_env, consul_env_prefix, istio_namespace_env)


async def discover_service_async(
    service_name: str,
    default_url_env: Optional[str] = None,
    discovery_methods: Optional[List[str]] = None
) -> Optional[str]:
    """
    Async service discovery function
    
    Args:
        service_name: Name of the service to discover
        default_url_env: Environment variable name for fallback URL
        discovery_methods: List of discovery methods to try
    
    Returns:
        Service URL or None if not found
    """
    return await _service_discovery.discover_service_async(service_name, default_url_env, discovery_methods)


def _discover_service_sync(
    service_name: str,
    default_url_env: Optional[str] = None,
    consul_env_prefix: str = "CONSUL",
    istio_namespace_env: str = "ISTIO_NAMESPACE",
) -> Optional[str]:
    """
    Original synchronous service discovery implementation for backward compatibility
    """
    # 1) Explicit URL
    explicit = os.getenv(f"{service_name.upper()}_URL")
    if explicit:
        return explicit

    # 2) Consul
    consul_host = os.getenv(f"{consul_env_prefix}_HOST")
    consul_port = os.getenv(f"{consul_env_prefix}_PORT", "8500")
    if consul_host:
        try:
            import requests
            resp = requests.get(
                f"http://{consul_host}:{consul_port}/v1/health/service/{service_name}?passing=true",
                timeout=float(os.getenv("CONSUL_HTTP_TIMEOUT_SECONDS", "2")),
            )
            if resp.status_code == 200:
                services = resp.json()
                for item in services or []:
                    svc = item.get("Service", {})
                    address = svc.get("Address") or "localhost"
                    port = svc.get("Port") or 80
                    return f"http://{address}:{port}"
        except Exception:
            pass

    # 3) Istio/K8s DNS
    ns = os.getenv(istio_namespace_env, "default")
    cluster_domain = os.getenv("K8S_CLUSTER_DOMAIN", "cluster.local")
    # We return an http URL using typical service: http://<svc>.<ns>.svc.cluster.local
    if os.getenv("USE_ISTIO_DNS", "false").lower() in {"1", "true", "yes"}:
        return f"http://{service_name}.{ns}.svc.{cluster_domain}"

    # 4) Fallback
    if default_url_env:
        return os.getenv(default_url_env)

    return None


