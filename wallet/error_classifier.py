"""Error classification for transaction reliability and retry decisions."""

from __future__ import annotations

from enum import Enum
from typing import Optional


class ErrorType(Enum):
    """Classification of errors for retry strategy."""

    TRANSIENT = "transient"  # Safe to retry
    PERMANENT = "permanent"  # Do not retry
    UNKNOWN = "unknown"  # Retry cautiously


class ErrorClassifier:
    """Classify errors to determine retry strategy."""

    # Patterns that indicate transient errors (safe to retry)
    TRANSIENT_PATTERNS = {
        "timeout",
        "connection refused",
        "connection reset",
        "connection aborted",
        "broken pipe",
        "nonce too low",
        "pending",
        "underpriced",
        "replaceable",
        "insufficient funds for replacement",
        "insufficient balance for gas",
        "temporarily unavailable",
        "service unavailable",
        "gateway timeout",
        "bad gateway",
        "temporarily blocked",
        "rate limited",
        "request time-out",
        "peer disconnect",
        "network unreachable",
        "no route to host",
        "reset by peer",
        "i/o timeout",
        "deadline exceeded",
    }

    # Patterns that indicate permanent errors (do not retry)
    PERMANENT_PATTERNS = {
        "invalid chainid",
        "chain mismatch",
        "invalid address",
        "bad request",
        "invalid json",
        "parse error",
        "invalid method",
        "method not found",
        "invalid params",
        "forbidden",
        "unauthorized",
        "access denied",
        "permission denied",
        "insufficient funds",
        "insufficient allowance",
        "nonce too high",
        "transaction fee too high",
        "gas price too low",
        "intrinsic gas too low",
        "out of gas",
        "invalid transaction",
        "invalid transaction type",
        "cannot estimate gas",
        "revert",
        "reverted",
        "execution reverted",
        "contract creation code storage out of gas",
        "invalid opcode",
        "invalid jump destination",
        "stack overflow",
        "stack underflow",
        "bad jump destination",
        "authentication failed",
        "api key invalid",
        "request body too large",
    }

    @classmethod
    def classify(cls, error: Exception) -> ErrorType:
        """
        Classify an error as transient, permanent, or unknown.
        
        Args:
            error: The exception to classify
            
        Returns:
            ErrorType classification
        """
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()

        # Check permanent patterns first (more specific)
        for pattern in cls.PERMANENT_PATTERNS:
            if pattern in error_str or pattern in error_type:
                return ErrorType.PERMANENT

        # Check transient patterns
        for pattern in cls.TRANSIENT_PATTERNS:
            if pattern in error_str or pattern in error_type:
                return ErrorType.TRANSIENT

        # Default to unknown
        return ErrorType.UNKNOWN

    @classmethod
    def is_retryable(cls, error: Exception) -> bool:
        """
        Determine if an error should trigger a retry.
        
        Args:
            error: The exception to evaluate
            
        Returns:
            True if the error is retryable
        """
        classification = cls.classify(error)
        return classification in (ErrorType.TRANSIENT, ErrorType.UNKNOWN)

    @classmethod
    def get_backoff_factor(cls, error: Exception, attempt: int) -> float:
        """
        Calculate backoff delay based on error type and attempt number.
        Transient errors get longer backoff (may need time to recover).
        Unknown errors get moderate backoff (cautious).
        
        Args:
            error: The exception
            attempt: Current attempt number (1-indexed)
            
        Returns:
            Backoff delay in seconds
        """
        classification = cls.classify(error)
        
        # Exponential backoff: 2^(attempt-1) seconds, capped at 60s
        base_backoff = 2 ** min(attempt - 1, 5)  # Cap at 32 seconds
        
        # Adjust by error type
        if classification == ErrorType.TRANSIENT:
            # Give transient errors more time to recover
            return min(base_backoff * 1.0, 60.0)
        elif classification == ErrorType.UNKNOWN:
            # Be cautious with unknown errors
            return min(base_backoff * 0.5, 30.0)
        else:
            # Permanent errors don't need backoff (won't retry anyway)
            return 0.0
