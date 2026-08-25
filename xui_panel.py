"""
3x-ui Panel API Client
Handles interactions with 3x-ui panels for node management
"""

import requests
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

    def login(self) -> bool:
        """Login to the panel and get session token"""
        url = f"{self.base_url}/api/panel/login"
        try:
            resp = self.session.post(
                url,
                json={"username": self.username, "password": self.password},
                timeout=15,
            )
            data = resp.json()
            if data.get("success"):
                self.token = data.get("obj", "")
                self.session.headers["Authorization"] = self.token
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
        url = f"{self.base_url}/api/panel/getSettings"
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
        url = f"{self.base_url}/api/panel/inbounds"
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

    def get_nodes(self) -> list:
        """Get list of configured nodes"""
        url = f"{self.base_url}/api/panel/getClients"
        try:
            resp = self.session.post(url, timeout=15)
            data = resp.json()
            if data.get("success"):
                return data.get("obj", [])
            return []
        except Exception as e:
            logger.warning(f"Get nodes error: {e}")
            return []

    def add_node(self, node_url: str, node_port: int, node_user: str, node_pass: str) -> bool:
        """Add a node to this panel"""
        url = f"{self.base_url}/api/panel/addClient"
        try:
            resp = self.session.post(
                url,
                json={
                    "settings": f'[{{"up":"{node_user}","down":"{node_pass}","total":0,"expired":0,"enable":true,"id":"","remark":"Node {node_url}"}}]'
                },
                timeout=15,
            )
            data = resp.json()
            return data.get("success", False)
        except Exception as e:
            logger.warning(f"Add node error: {e}")
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


def setup_all_nodes(
    main_url: str,
    node_urls: dict,
    main_creds: tuple = ("admin", "admin"),
    node_creds: tuple = ("admin", "admin"),
) -> dict:
    """
    Configure all nodes with the main panel.
    main_url: URL of the main panel (NL)
    node_urls: dict of {name: url} for other panels
    Returns status dict.
    """
    results = {"main": main_url, "nodes": {}, "success": False}

    # Wait for main panel
    if not wait_for_panel(main_url, timeout=120):
        results["error"] = "Main panel not ready"
        return results

    # Login to main panel
    main_panel = XUIPanel(main_url, *main_creds)
    if not main_panel.login():
        results["error"] = "Could not login to main panel"
        return results

    # Get main panel info
    main_uuid = main_panel.get_panel_uuid()
    main_settings = main_panel.get_settings()
    results["main_uuid"] = main_uuid
    results["main_port"] = main_settings.get("port", 2053)

    # Process each node
    for name, url in node_urls.items():
        node_result = {"name": name, "url": url, "success": False}

        # Wait for node panel
        if not wait_for_panel(url, timeout=120):
            node_result["error"] = "Node panel not ready"
            results["nodes"][name] = node_result
            continue

        # Login to node panel
        node_panel = XUIPanel(url, *node_creds)
        if not node_panel.login():
            node_result["error"] = "Could not login to node panel"
            results["nodes"][name] = node_result
            continue

        # Get node info
        node_uuid = node_panel.get_panel_uuid()
        node_settings = node_panel.get_settings()
        node_port = node_settings.get("port", 2053)

        node_result["uuid"] = node_uuid
        node_result["port"] = node_port
        node_result["success"] = True
        results["nodes"][name] = node_result

        logger.info(f"Node {name}: UUID={node_uuid[:8]}..., Port={node_port}")

    results["success"] = True
    return results
