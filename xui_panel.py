"""
3x-ui Panel API Client
Handles interactions with 3x-ui panels for node management
"""

import requests
import re
import logging
import time

logger = logging.getLogger(__name__)


class XUIPanel:
    def __init__(self, base_url: str, username: str = "admin", password: str = "admin"):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.token = None
        self.csrf_token = None

    def _get_csrf_token(self) -> str:
        """Get CSRF token from the login page"""
        try:
            resp = self.session.get(f"{self.base_url}/managepanel/", timeout=15)
            match = re.search(r'csrf-token.*?content="([^"]+)"', resp.text)
            if match:
                return match.group(1)
        except Exception as e:
            logger.warning(f"Get CSRF error: {e}")
        return ""

    def login(self) -> bool:
        """Login to the panel and get session token"""
        # Get CSRF token first
        self.csrf_token = self._get_csrf_token()
        
        url = f"{self.base_url}/managepanel/login"
        try:
            resp = self.session.post(
                url,
                json={"username": self.username, "password": self.password},
                headers={"X-CSRF-Token": self.csrf_token},
                timeout=15,
            )
            data = resp.json()
            if data.get("success"):
                self.token = data.get("obj", "")
                logger.info(f"Logged in to {self.base_url}")
                return True
            else:
                logger.warning(f"Login failed for {self.base_url}: {data}")
                return False
        except Exception as e:
            logger.warning(f"Login error for {self.base_url}: {e}")
            return False

    def get_settings(self) -> dict:
        """Get panel settings"""
        url = f"{self.base_url}/managepanel/api/panel/getSettings"
        try:
            resp = self.session.post(url, timeout=15)
            data = resp.json()
            if data.get("success"):
                return data.get("obj", {})
            return {}
        except Exception as e:
            logger.warning(f"Get settings error: {e}")
            return {}

    def get_inbounds(self) -> list:
        """Get list of inbounds"""
        url = f"{self.base_url}/managepanel/api/panel/inbounds"
        try:
            resp = self.session.post(url, timeout=15)
            data = resp.json()
            if data.get("success"):
                return data.get("obj", [])
            return []
        except Exception as e:
            logger.warning(f"Get inbounds error: {e}")
            return []

    def get_panel_uuid(self) -> str:
        """Get panel's unique identifier"""
        settings = self.get_settings()
        return settings.get("subKey", "") or settings.get("uuid", "")

    def is_ready(self) -> bool:
        """Check if panel is accessible and responding"""
        try:
            resp = self.session.get(self.base_url, timeout=10, allow_redirects=True)
            return resp.status_code == 200
        except Exception:
            return False


def wait_for_panel(url: str, timeout: int = 180, interval: int = 10) -> bool:
    """Wait for a panel to become accessible"""
    start = time.time()
    panel = XUIPanel(url)
    while time.time() - start < timeout:
        if panel.is_ready():
            logger.info(f"Panel ready: {url}")
            return True
        logger.info(f"Waiting for panel: {url}...")
        time.sleep(interval)
    logger.warning(f"Panel timeout: {url}")
    return False
