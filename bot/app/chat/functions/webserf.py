from typing import Any

import requests


def http_get(url: str, timeout: float = 10.0) -> dict[str, Any]:
    """HTTP GET request.

    Args:
      url: target URL
      timeout: seconds
    Returns:
      dict: {status, headers, text_len}
    """
    r = requests.get(url, timeout=timeout)
    return {
        "status": r.status_code,
        "headers": dict(r.headers),
        "text_len": len(r.text),
    }


def http_post(url: str, data: dict[str, Any], timeout: float = 10.0) -> dict[str, Any]:
    """HTTP POST request.

    Args:
      url: target URL
      data: JSON-serializable dict to send as body
      timeout: seconds
    Returns:
      dict: {status, headers, text_len}
    """
    r = requests.post(url, json=data, timeout=timeout)
    return {
        "status": r.status_code,
        "headers": dict(r.headers),
        "text_len": len(r.text),
    }


def get_from_webserf(url: str) -> str:
    """Fetch content from a URL using webserf tool.

    Args:
      url: target URL
    Returns:
      str: result message
    """
    response = http_get(url)
    if response["status"] == 200:
        return f"Content fetched successfully with length {response['text_len']}."
    else:
        return f"Failed to fetch content. Status code: {response['status']}."


tools = [get_from_webserf, http_get, http_post]
