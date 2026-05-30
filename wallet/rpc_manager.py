"""RPC failover and health management for reliable chain communication."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import List, Optional
from threading import Lock
import logging

import aiohttp
from web3 import Web3, HTTPProvider

logger = logging.getLogger(__name__)


class RpcConnectionError(ConnectionError):
    """Structured error for RPC connection failures."""
    
    def __init__(
        self,
        message: str,
        endpoint_url: Optional[str] = None,
        reason: Optional[str] = None,
        attempts: int = 0,
    ):
        """
        Initialize RPC connection error.
        
        Args:
            message: Error message
            endpoint_url: The RPC endpoint that failed
            reason: Specific reason for failure (timeout, refused, etc.)
            attempts: Number of attempts made
        """
        self.endpoint_url = endpoint_url
        self.reason = reason
        self.attempts = attempts
        
        full_msg = message
        if endpoint_url:
            full_msg += f" (endpoint: {endpoint_url})"
        if reason:
            full_msg += f" - {reason}"
        if attempts > 0:
            full_msg += f" (after {attempts} attempts)"
        
        super().__init__(full_msg)
class RpcEndpoint:
    """Represents a single RPC endpoint with health tracking."""

    url: str
    healthy: bool = True
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    last_health_check_time: Optional[float] = None
    failure_count: int = 0
    success_count: int = 0
    consecutive_failures: int = 0
    circuit_open: bool = False
    circuit_open_time: Optional[float] = None
    circuit_open_attempts: int = 0  # Track how many times circuit has been opened

    def mark_success(self) -> None:
        """Record successful RPC call."""
        self.success_count += 1
        self.last_success_time = time.time()
        self.healthy = True
        self.failure_count = 0
        self.consecutive_failures = 0
        self.circuit_open = False
        self.circuit_open_time = None
        self.last_failure_time = None

    def mark_failure(self) -> None:
        """Record failed RPC call and update circuit breaker state."""
        self.failure_count += 1
        self.consecutive_failures += 1
        self.last_failure_time = time.time()
        
        # Open circuit after 3 consecutive failures (for single RPC)
        if self.consecutive_failures >= 3:
            self.healthy = False
            if not self.circuit_open:
                self.circuit_open = True
                self.circuit_open_time = time.time()
                self.circuit_open_attempts += 1
                logger.warning(
                    "Circuit opened for RPC endpoint %s (attempt %d)",
                    self.url,
                    self.circuit_open_attempts,
                )

    def mark_health_check(self) -> None:
        """Record that a health check was performed."""
        self.last_health_check_time = time.time()

    def get_circuit_break_duration(self) -> float:
        """
        Calculate circuit break duration with exponential backoff.
        
        After circuit opens, wait before trying again:
        - 1st open: 30 seconds
        - 2nd open: 60 seconds
        - 3rd+ open: 120 seconds
        
        Returns:
            Duration in seconds before circuit can be reopened
        """
        if self.circuit_open_attempts <= 1:
            return 30.0
        elif self.circuit_open_attempts == 2:
            return 60.0
        else:
            return 120.0

    def is_available(self, health_check_timeout: float = 30.0) -> bool:
        """
        Check if endpoint is available for use.
        
        Circuit breaker logic:
        - If healthy, return True
        - If circuit open and timeout not elapsed, return False
        - If circuit open and timeout elapsed, return True (attempt recovery)
        - If unhealthy but no circuit open yet, return True (still in test phase)
        
        Args:
            health_check_timeout: Timeout before retrying unhealthy endpoints
            
        Returns:
            True if endpoint should be attempted
        """
        if self.healthy:
            return True

        # If circuit is open, check if we should try to recover
        if self.circuit_open and self.circuit_open_time is not None:
            elapsed = time.time() - self.circuit_open_time
            circuit_duration = self.get_circuit_break_duration()
            
            if elapsed >= circuit_duration:
                # Time to attempt recovery - reset for retry
                logger.info(
                    "Attempting circuit recovery for RPC endpoint %s after %.1f seconds",
                    self.url,
                    elapsed,
                )
                self.circuit_open = False
                self.consecutive_failures = 0
                return True
            else:
                # Circuit still open
                return False

        # Not in circuit, but marked unhealthy - check timeout
        if self.last_failure_time is not None:
            elapsed = time.time() - self.last_failure_time
            if elapsed > health_check_timeout:
                return True

        return False


class RpcManager:
    """Manage RPC endpoints with single-endpoint optimizations and reliability features."""

    # Configuration constants for single RPC operation
    MAX_CONNECTION_ATTEMPTS = 5  # Maximum retries for a single connection attempt
    MIN_HEALTH_CHECK_INTERVAL = 1.0  # Minimum seconds between health checks per endpoint
    CONNECTION_TIMEOUT = 10.0  # Timeout for initial connection in seconds
    BASE_BACKOFF_DELAY = 0.5  # Initial backoff delay in seconds
    MAX_BACKOFF_DELAY = 16.0  # Maximum backoff delay (exponential cap)

    def __init__(
        self,
        rpc_urls: List[str],
        timeout: int = 20,
        health_check_timeout: float = 30.0,
        max_retries: int = 5,
        base_backoff: float = 0.5,
    ):
        """
        Initialize RPC manager for single-endpoint reliability.
        
        Args:
            rpc_urls: List of RPC endpoint URLs (typically single URL for single-RPC design)
            timeout: Request timeout in seconds for RPC operations
            health_check_timeout: Circuit breaker timeout before retrying unhealthy endpoints
            max_retries: Maximum connection retry attempts
            base_backoff: Initial backoff delay in seconds
        """
        if not rpc_urls:
            raise ValueError("At least one RPC URL is required")

        self.endpoints = [RpcEndpoint(url=url) for url in rpc_urls]
        self.timeout = timeout
        self.health_check_timeout = health_check_timeout
        self.max_retries = max(1, min(max_retries, self.MAX_CONNECTION_ATTEMPTS))
        self.base_backoff = base_backoff
        self.current_index = 0
        self._lock = Lock()
        self._session: Optional[aiohttp.ClientSession] = None

    def get_web3(self) -> Web3:
        """
        Get a Web3 instance connected to a healthy RPC endpoint.
        
        For single-RPC design, focuses on robust connection with retries
        and exponential backoff.
        
        Returns:
            Web3 instance
            
        Raises:
            RpcConnectionError: If connection fails after all retries
        """
        # Use iterative retry instead of recursion to avoid stack overflow
        for attempt in range(1, self.max_retries + 1):
            try:
                # Try to connect with timeout enforcement
                endpoint = self._select_endpoint()
                
                w3 = self._create_web3_with_timeout(endpoint.url)
                
                # Verify connection is actually working
                if self._verify_connection(w3, endpoint):
                    with self._lock:
                        endpoint.mark_success()
                    logger.info(
                        "RPC connection successful to %s (attempt %d)",
                        endpoint.url,
                        attempt,
                    )
                    return w3
                else:
                    with self._lock:
                        endpoint.mark_failure()
                    logger.warning(
                        "RPC connection verification failed for %s (attempt %d)",
                        endpoint.url,
                        attempt,
                    )
                    
            except Exception as exc:
                with self._lock:
                    endpoint = self.endpoints[0]  # Single RPC
                    endpoint.mark_failure()
                
                error_reason = str(exc)
                logger.warning(
                    "RPC connection attempt %d failed for %s: %s",
                    attempt,
                    endpoint.url,
                    error_reason,
                )
                
                # Apply exponential backoff between retries
                if attempt < self.max_retries:
                    delay = self._get_backoff_delay(attempt)
                    logger.debug(
                        "Backing off for %.2f seconds before retry %d...",
                        delay,
                        attempt + 1,
                    )
                    time.sleep(delay)

        # All retries exhausted
        endpoint = self.endpoints[0]  # Single RPC
        raise RpcConnectionError(
            "Failed to establish RPC connection after retries",
            endpoint_url=endpoint.url,
            reason="All connection attempts failed",
            attempts=self.max_retries,
        )

    def _select_endpoint(self) -> RpcEndpoint:
        """
        Select an endpoint for connection attempt.
        
        For single-RPC design, returns the only endpoint.
        Prefers available endpoints based on circuit breaker state.
        
        Returns:
            RpcEndpoint to attempt connection to
        """
        with self._lock:
            # For single RPC, always use first endpoint
            # Circuit breaker will handle availability
            endpoint = self.endpoints[0]
            
            # Update availability based on circuit breaker
            if not endpoint.is_available(self.health_check_timeout):
                logger.debug(
                    "Endpoint %s is unavailable due to circuit breaker",
                    endpoint.url,
                )
            
            return endpoint

    def _create_web3_with_timeout(self, rpc_url: str) -> Web3:
        """
        Create Web3 instance with explicit connection timeout.
        
        Args:
            rpc_url: RPC endpoint URL
            
        Returns:
            Web3 instance
            
        Raises:
            TimeoutError: If connection takes longer than timeout
            Exception: If connection fails
        """
        try:
            # Create provider with connection timeout
            provider = HTTPProvider(
                rpc_url,
                request_kwargs={"timeout": self.timeout},
            )
            w3 = Web3(provider)
            return w3
        except Exception as exc:
            raise RpcConnectionError(
                "Failed to create Web3 instance",
                endpoint_url=rpc_url,
                reason=str(exc),
            ) from exc

    def _verify_connection(self, w3: Web3, endpoint: RpcEndpoint) -> bool:
        """
        Verify that RPC connection is actually working.
        
        Uses eth_chainId as lightweight health check that doesn't
        require state access.
        
        Args:
            w3: Web3 instance to verify
            endpoint: RpcEndpoint being tested
            
        Returns:
            True if RPC is responsive, False otherwise
        """
        try:
            # Rate limit health checks
            now = time.time()
            if endpoint.last_health_check_time is not None:
                elapsed = now - endpoint.last_health_check_time
                if elapsed < self.MIN_HEALTH_CHECK_INTERVAL:
                    logger.debug(
                        "Skipping health check for %s (checked %.2f seconds ago)",
                        endpoint.url,
                        elapsed,
                    )
                    return True
            
            # Verify connection with lightweight call
            chain_id = w3.eth.chain_id
            endpoint.mark_health_check()
            
            logger.debug("Health check successful for %s (chain_id: %d)", endpoint.url, chain_id)
            return True
            
        except Exception as exc:
            logger.warning(
                "Health check failed for %s: %s",
                endpoint.url,
                str(exc),
            )
            return False

    def _get_backoff_delay(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay for connection retries.
        
        Prevents RPC hammering by increasing delay between retries:
        - Attempt 1: 0.5s
        - Attempt 2: 1s
        - Attempt 3: 2s
        - Attempt 4: 4s
        - Attempt 5+: 8s+ (capped at 16s)
        
        Args:
            attempt: Current attempt number (1-indexed)
            
        Returns:
            Delay in seconds
        """
        # Exponential backoff: base * 2^(attempt-1), capped at max
        delay = self.base_backoff * (2 ** (attempt - 1))
        return min(delay, self.MAX_BACKOFF_DELAY)

    def reset_health(self) -> None:
        """Reset health status of all endpoints (useful for recovery)."""
        with self._lock:
            for endpoint in self.endpoints:
                endpoint.healthy = True
                endpoint.failure_count = 0
                endpoint.consecutive_failures = 0
                endpoint.last_failure_time = None
                endpoint.circuit_open = False
                endpoint.circuit_open_time = None
                logger.info("Reset health status for RPC endpoint %s", endpoint.url)

    def get_status(self) -> dict:
        """Get health status of all endpoints."""
        with self._lock:
            return {
                ep.url: {
                    "healthy": ep.healthy,
                    "success_count": ep.success_count,
                    "failure_count": ep.failure_count,
                    "consecutive_failures": ep.consecutive_failures,
                    "circuit_open": ep.circuit_open,
                    "last_failure": ep.last_failure_time,
                    "last_success": ep.last_success_time,
                }
                for ep in self.endpoints
            }

    async def get_web3_async(self) -> Web3:
        """
        Get a Web3 instance connected to a healthy RPC endpoint asynchronously.
        
        Performs health checks and retry with exponential backoff using async.
        
        Returns:
            Web3 instance
            
        Raises:
            RpcConnectionError: If connection fails after all retries
        """
        # Use iterative retry instead of recursion
        for attempt in range(1, self.max_retries + 1):
            try:
                endpoint = self._select_endpoint()
                
                # Check endpoint health asynchronously
                is_healthy = await self._verify_connection_async(endpoint)
                
                if is_healthy:
                    # Create web3 instance synchronously (web3.py doesn't support async)
                    w3 = self._create_web3_with_timeout(endpoint.url)
                    
                    with self._lock:
                        endpoint.mark_success()
                    logger.info(
                        "RPC async connection successful to %s (attempt %d)",
                        endpoint.url,
                        attempt,
                    )
                    return w3
                else:
                    with self._lock:
                        endpoint.mark_failure()
                    logger.warning(
                        "RPC async connection verification failed for %s (attempt %d)",
                        endpoint.url,
                        attempt,
                    )
                    
            except Exception as exc:
                with self._lock:
                    endpoint = self.endpoints[0]  # Single RPC
                    endpoint.mark_failure()
                
                logger.warning(
                    "RPC async connection attempt %d failed for %s: %s",
                    attempt,
                    endpoint.url,
                    str(exc),
                )
                
                # Apply exponential backoff between retries
                if attempt < self.max_retries:
                    delay = self._get_backoff_delay(attempt)
                    logger.debug(
                        "Backing off for %.2f seconds before retry %d...",
                        delay,
                        attempt + 1,
                    )
                    await asyncio.sleep(delay)

        # All retries exhausted
        endpoint = self.endpoints[0]  # Single RPC
        raise RpcConnectionError(
            "Failed to establish RPC async connection after retries",
            endpoint_url=endpoint.url,
            reason="All connection attempts failed",
            attempts=self.max_retries,
        )

    async def _verify_connection_async(self, endpoint: RpcEndpoint) -> bool:
        """
        Verify that RPC connection is actually working using async HTTP.
        
        Uses eth_chainId as lightweight health check.
        
        Args:
            endpoint: RpcEndpoint to verify
            
        Returns:
            True if RPC is responsive, False otherwise
        """
        try:
            # Rate limit health checks
            now = time.time()
            if endpoint.last_health_check_time is not None:
                elapsed = now - endpoint.last_health_check_time
                if elapsed < self.MIN_HEALTH_CHECK_INTERVAL:
                    logger.debug(
                        "Skipping async health check for %s (checked %.2f seconds ago)",
                        endpoint.url,
                        elapsed,
                    )
                    return True
            
            # Perform health check via JSON-RPC
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_chainId",
                "params": [],
                "id": 1,
            }
            
            timeout = aiohttp.ClientTimeout(total=self.CONNECTION_TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(endpoint.url, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if "result" in data and data["result"] is not None:
                            endpoint.mark_health_check()
                            logger.debug(
                                "Async health check successful for %s",
                                endpoint.url,
                            )
                            return True
            
            logger.warning(
                "Async health check returned invalid response for %s (status: %d)",
                endpoint.url,
                resp.status if 'resp' in locals() else 0,
            )
            return False
            
        except asyncio.TimeoutError:
            logger.warning(
                "Async health check timeout for %s",
                endpoint.url,
            )
            return False
        except Exception as exc:
            logger.warning(
                "Async health check failed for %s: %s",
                endpoint.url,
                str(exc),
            )
            return False
