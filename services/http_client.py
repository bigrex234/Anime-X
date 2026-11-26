"""Shared resilient HTTP session for metadata providers."""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def build_session(user_agent="AnimeX/2.0"):
    retry = Retry(
        total=2,
        connect=2,
        read=1,
        status=2,
        backoff_factor=0.35,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(("GET", "POST")),
        respect_retry_after_header=True,
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=20)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": user_agent,
    })
    return session
