"""
Configuration for NotebookLM Skill
Centralizes constants, selectors, and paths
"""

import re
from pathlib import Path
from urllib.parse import urlparse

# Paths
SKILL_DIR = Path(__file__).parent.parent
DATA_DIR = SKILL_DIR / "data"
BROWSER_STATE_DIR = DATA_DIR / "browser_state"
BROWSER_PROFILE_DIR = BROWSER_STATE_DIR / "browser_profile"
STATE_FILE = BROWSER_STATE_DIR / "state.json"
AUTH_INFO_FILE = DATA_DIR / "auth_info.json"
LIBRARY_FILE = DATA_DIR / "library.json"

# Domain Configuration
NOTEBOOK_HOSTS = {"notebooklm.google.com", "notebook.google.com"}
DEFAULT_NOTEBOOK_HOST = "notebook.google.com"
DEFAULT_NOTEBOOK_URL = f"https://{DEFAULT_NOTEBOOK_HOST}"

NOTEBOOK_URL_PATTERN = re.compile(
    r"^https://(?:notebooklm|notebook)\.google\.com(?:/|$)"
)


def is_notebook_url(url: str) -> bool:
    """Check if a URL belongs to NotebookLM / Gemini Notebook.

    Ensures the URL is an HTTPS scheme, matches one of the accepted hosts,
    and is not a login/auth redirection route or external spoofing attempt.
    """
    if not url:
        return False
    try:
        parsed = urlparse(url)
        return (
            parsed.scheme == "https"
            and parsed.netloc in NOTEBOOK_HOSTS
            and not parsed.path.startswith("/login")
        )
    except Exception:
        return False


# NotebookLM Selectors
QUERY_INPUT_SELECTORS = [
    "textarea.query-box-input",  # Primary textarea
    'textarea[aria-label="Query box"]',  # English aria-label
    'textarea[aria-label="Feld für Anfragen"]',  # German aria-label
    'textarea[aria-label="Input for queries"]',  # Alt English aria-label
    'div[role="textbox"][contenteditable="true"]',  # Generic contenteditable fallback
]

RESPONSE_SELECTORS = [
    ".to-user-container .message-text-content",  # Primary container
    "[data-message-author='bot']",  # Data attribute fallback
    "[data-message-author='assistant']",  # Alt data attribute fallback
    ".response-container .message-content",  # Additional potential container
]

THINKING_SELECTORS = [
    "div.thinking-message",
    ".loading-indicator",
]

# Browser Configuration
BROWSER_ARGS = [
    '--disable-blink-features=AutomationControlled',  # Patches navigator.webdriver
    '--disable-dev-shm-usage',
    '--no-sandbox',
    '--no-first-run',
    '--no-default-browser-check',
]

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

# Timeouts & Lifecycles
LOGIN_TIMEOUT_MINUTES = 10
QUERY_TIMEOUT_SECONDS = 120
PAGE_LOAD_TIMEOUT = 30000
STALE_WARN_DAYS = 7
STALE_FAIL_DAYS = 14

