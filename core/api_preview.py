"""
API utilities for testing and previewing data sources.

Provides functionality to test API endpoints and explore their structure
before creating a source instance.
"""

from typing import Any, Optional

import httpx


class APIPreviewResult:
    """Result of an API preview/test call."""
    
    def __init__(
        self,
        success: bool,
        data: Optional[Any] = None,
        error: Optional[str] = None,
        content_type: Optional[str] = None,
        status_code: Optional[int] = None,
        response_time_ms: Optional[float] = None
    ):
        self.success = success
        self.data = data
        self.error = error
        self.content_type = content_type
        self.status_code = status_code
        self.response_time_ms = response_time_ms
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "content_type": self.content_type,
            "status_code": self.status_code,
            "response_time_ms": self.response_time_ms
        }


async def preview_api_endpoint(
    url: str,
    timeout: int = 10,
    method: str = "GET",
    headers: Optional[dict] = None
) -> APIPreviewResult:
    """
    Test an API endpoint and return its structure.
    
    Args:
        url: URL to test
        timeout: Request timeout in seconds
        method: HTTP method (GET, POST, etc.)
        headers: Optional HTTP headers
        
    Returns:
        APIPreviewResult with the response data or error
    """
    from datetime import datetime
    
    start_time = datetime.utcnow()
    
    try:
        async with httpx.AsyncClient() as client:
            if method.upper() == "GET":
                response = await client.get(url, timeout=timeout, headers=headers or {})
            elif method.upper() == "POST":
                response = await client.post(url, timeout=timeout, headers=headers or {})
            else:
                return APIPreviewResult(
                    success=False,
                    error=f"Unsupported HTTP method: {method}"
                )
            
            end_time = datetime.utcnow()
            response_time_ms = (end_time - start_time).total_seconds() * 1000
            
            content_type = response.headers.get("content-type", "unknown")
            
            # Try to parse as JSON first
            try:
                data = response.json()
                return APIPreviewResult(
                    success=True,
                    data=data,
                    content_type=content_type,
                    status_code=response.status_code,
                    response_time_ms=response_time_ms
                )
            except Exception:
                # Not JSON, return as text
                text = response.text
                
                # Try to parse as a number
                try:
                    number = float(text.strip())
                    return APIPreviewResult(
                        success=True,
                        data={"value": number, "_raw_text": text},
                        content_type=content_type,
                        status_code=response.status_code,
                        response_time_ms=response_time_ms
                    )
                except ValueError:
                    # Just return as text
                    return APIPreviewResult(
                        success=True,
                        data={"_raw_text": text},
                        content_type=content_type,
                        status_code=response.status_code,
                        response_time_ms=response_time_ms
                    )
    
    except httpx.TimeoutException:
        return APIPreviewResult(
            success=False,
            error=f"Request timed out after {timeout}s"
        )
    except httpx.HTTPError as e:
        return APIPreviewResult(
            success=False,
            error=f"HTTP error: {str(e)}"
        )
    except Exception as e:
        return APIPreviewResult(
            success=False,
            error=f"Unexpected error: {str(e)}"
        )


def extract_all_paths(data: Any, prefix: str = "") -> list[tuple[str, Any, str]]:
    """
    Extract all possible JSON paths from data structure.
    
    Args:
        data: Data to extract paths from
        prefix: Current path prefix
        
    Returns:
        List of (path, value, type) tuples
    """
    paths = []
    
    if isinstance(data, dict):
        for key, value in data.items():
            current_path = f"{prefix}.{key}" if prefix else key
            
            # Add this path
            value_type = type(value).__name__
            if isinstance(value, (int, float)):
                value_type = "number"
            elif isinstance(value, str):
                value_type = "string"
            elif isinstance(value, bool):
                value_type = "boolean"
            elif isinstance(value, (dict, list)):
                value_type = f"{value_type} (nested)"
            
            paths.append((current_path, value, value_type))
            
            # Recurse if nested
            if isinstance(value, (dict, list)):
                paths.extend(extract_all_paths(value, current_path))
    
    elif isinstance(data, list) and len(data) > 0:
        # For arrays, show the first item's structure
        current_path = f"{prefix}[0]"
        first_item = data[0]
        
        paths.append((current_path, first_item, type(first_item).__name__))
        
        if isinstance(first_item, (dict, list)):
            paths.extend(extract_all_paths(first_item, current_path))
    
    return paths
