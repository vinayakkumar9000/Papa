"""RPC failover and health management for reliable chain communication."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Optional
from threading import Lock

from web3 import HTTPProvider, Web3


@dataclass
class RpcEndpoint:
    """Represents a single RPC endpoint with health tracking."""

    url: str
    healthy: bool = True
    last_failure_time: Optional[float] = None
    failure_count: int = 0
    success_count: int = 0

    def mark_success(self) -> None:
        """Record successful RPC call."""
        self.success_count += 1
        self.healthy = True
        self.failure_count = 0
        self.last_failure_time = None

    def mark_failure(self) -> None:
        """Record failed RPC call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        # Mark unhealthy after 3 consecutive failures
        if self.failure_count >= 3:
            self.healthy = False

    def is_available(self, health_check_timeout: float = 30.0) -> bool:
        """
        Check if endpoint is available.
        
        If unhealthy and enough time has passed, allow retry.
        This implements circuit breaker pattern.
        """
        if self.healthy:
            return True

        if self.last_failure_time is None:
            return True

        elapsed = time.time() - self.last_failure_time
        # After timeout, give the endpoint a chance again
        if elapsed > health_check_timeout:
            return True

        return False


class RpcManager:
    """Manage multiple RPC endpoints with failover and health checking."""

    def __init__(self, rpc_urls: List[str], timeout: int = 20, health_check_timeout: float = 30.0):
        """
        Initialize RPC manager.
        
        Args:
            rpc_urls: List of RPC endpoint URLs
            timeout: Request timeout in seconds
            health_check_timeout: Time before retrying unhealthy endpoints
        """
        if not rpc_urls:
            raise ValueError("At least one RPC URL is required")

        self.endpoints = [RpcEndpoint(url=url) for url in rpc_urls]
        self.timeout = timeout
        self.health_check_timeout = health_check_timeout
        self.current_index = 0
        self._lock = Lock()

    def get_web3(self) -> Web3:
        """
        Get a Web3 instance connected to a healthy RPC endpoint.
        
        Returns:
            Web3 instance
            
        Raises:
            ConnectionError: If no healthy endpoints are available
        """
        with self._lock:
            # Try to find a healthy endpoint
            available_endpoints = [ep for ep in self.endpoints if ep.is_available(self.health_check_timeout)]

            if not available_endpoints:
                # All endpoints are unavailable, try the first one anyway
                available_endpoints = self.endpoints

            # Rotate through endpoints for load balancing
            endpoint = available_endpoints[self.current_index % len(available_endpoints)]
            self.current_index += 1

        try:
            w3 = Web3(HTTPProvider(endpoint.url, request_kwargs={"timeout": self.timeout}))
            if w3.is_connected():
                endpoint.mark_success()
                return w3
            else:
                endpoint.mark_failure()
                # Try to find another endpoint
                return self._get_web3_recursive(visited={endpoint.url})
        except Exception as exc:
            endpoint.mark_failure()
            # Recursively try other endpoints
            return self._get_web3_recursive(visited={endpoint.url})

    def _get_web3_recursive(self, visited: set, depth: int = 0) -> Web3:
        """
        Recursively try to connect to available endpoints.
        
        Args:
            visited: Set of already-tried URLs
            depth: Recursion depth (prevent infinite recursion)
            
        Returns:
            Web3 instance
            
        Raises:
            ConnectionError: If no endpoint is available
        """
        if depth > len(self.endpoints):
            raise ConnectionError("All RPC endpoints failed")

        available = [ep for ep in self.endpoints if ep.url not in visited and ep.is_available(self.health_check_timeout)]

        if not available:
            raise ConnectionError(f"All RPC endpoints failed or unavailable after trying {len(visited)} endpoints")

        endpoint = available[0]
        visited.add(endpoint.url)

        try:
            w3 = Web3(HTTPProvider(endpoint.url, request_kwargs={"timeout": self.timeout}))
            if w3.is_connected():
                endpoint.mark_success()
                return w3
            else:
                endpoint.mark_failure()
                return self._get_web3_recursive(visited=visited, depth=depth + 1)
        except Exception as exc:
            endpoint.mark_failure()
            return self._get_web3_recursive(visited=visited, depth=depth + 1)

    def reset_health(self) -> None:
        """Reset health status of all endpoints (useful for recovery)."""
        with self._lock:
            for endpoint in self.endpoints:
                endpoint.healthy = True
                endpoint.failure_count = 0
                endpoint.last_failure_time = None

    def get_status(self) -> dict:
        """Get health status of all endpoints."""
        with self._lock:
            return {
                ep.url: {
                    "healthy": ep.healthy,
                    "success_count": ep.success_count,
                    "failure_count": ep.failure_count,
                    "last_failure": ep.last_failure_time,
                }
                for ep in self.endpoints
            }
