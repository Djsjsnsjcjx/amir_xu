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
        self.csrf_token = None
        self.logged_in = False

    def _refresh_csrf(self):
        """Get fresh CSRF token"""
        try:
            resp = self.session.get(f"{self.base_url}/managepanel/", timeout=15)
            match = re.search(r'csrf-token.*?content="([^"]+)"', resp.text)
            if match:
                self.csrf_token = match.group(1)
        except Exception:
            pass

    def _headers(self):
        return {"X-CSRF-Token": self.csrf_token}

    def login(self) -> bool:
        """Login to the panel"""
        self._refresh_csrf()
        try:
            resp = self.session.post(
                f"{self.base_url}/managepanel/login",
                json={"username": self.username, "password": self.password},
                headers=self._headers(),
                timeout=15,
            )
            data = resp.json()
            if data.get("success"):
                self.logged_in = True
                self._refresh_csrf()
                logger.info(f"Logged in to {self.base_url}")
                return True
        except Exception as e:
            logger.warning(f"Login error: {e}")
        return False

    def _post(self, path: str, data: dict = None) -> dict:
        """POST to panel API"""
        try:
            resp = self.session.post(
                f"{self.base_url}/managepanel{path}",
                json=data or {},
                headers=self._headers(),
                timeout=30,
            )
            return resp.json()
        except Exception as e:
            logger.warning(f"POST {path} error: {e}")
            return {}

    def _get(self, path: str) -> dict:
        """GET from panel API"""
        try:
            resp = self.session.get(
                f"{self.base_url}/managepanel{path}",
                headers=self._headers(),
                timeout=15,
            )
            return resp.json()
        except Exception as e:
            logger.warning(f"GET {path} error: {e}")
            return {}

    def get_uuid(self) -> str:
        """Get panel UUID"""
        data = self._get("/panel/api/server/getNewUUID")
        return data.get("obj", {}).get("uuid", "")

    def create_api_token(self, name: str = "node-token") -> str:
        """Create an API token, returns the token string"""
        # First delete existing tokens
        tokens = self._get("/panel/api/setting/apiTokens")
        for t in tokens.get("obj", []):
            self._post(f"/panel/api/setting/apiTokens/delete/{t['id']}")

        # Create new token
        data = self._post("/panel/api/setting/apiTokens/create", {"name": name})
        obj = data.get("obj", {})
        return obj.get("token", "")

    def add_node(self, node_name: str, node_url: str, node_uuid: str, node_token: str) -> dict:
        """Add a remote panel as a node"""
        node_data = {
            "name": node_name,
            "address": node_url.replace("https://", "").replace("http://", ""),
            "port": 443,
            "scheme": "https",
            "serialNumber": node_uuid,
            "apiToken": node_token,
            "trafficLimit": 0,
            "weight": 100,
            "remark": f"{node_name} Node",
            "checkInterval": 60,
            "checkType": "http",
            "notify": True,
            "alertThreshold": 0,
            "enable": True,
            "allowPrivateAddress": False,
            "basePath": "/managepanel/",
            "inboundSyncMode": "all",
            "inboundTags": [],
            "outboundTag": "",
            "pinnedCertSha256": "",
            "tlsVerifyMode": "skip",
        }
        return self._post("/panel/api/nodes/add", node_data)

    def get_nodes(self) -> list:
        """Get list of nodes"""
        data = self._get("/panel/api/nodes/list")
        return data.get("obj", [])

    def is_ready(self) -> bool:
        """Check if panel is accessible"""
        try:
            resp = self.session.get(self.base_url, timeout=10, allow_redirects=True)
            return resp.status_code == 200
        except Exception:
            return False


def wait_for_panel(url: str, timeout: int = 180, interval: int = 10) -> bool:
    """Wait for a panel to become accessible"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = requests.get(url, timeout=10, allow_redirects=True)
            if resp.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(interval)
    return False
