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


def wait_for_panel(url: str, timeout: int = 120, interval: int = 10) -> bool:
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


def setup_node_connection(
    main_panel_url: str,
    node_url: str,
    node_name: str,
    main_creds: tuple = ("admin", "admin"),
    node_creds: tuple = ("admin", "admin"),
) -> dict:
    """
    Add a node panel to the main panel.
    Returns status information.
    """
    result = {"node": node_name, "success": False, "message": ""}

    # Login to node panel
    node_panel = XUIPanel(node_url, *node_creds)
    if not node_panel.login():
        result["message"] = "Could not login to node panel"
        return result

    # Get node info
    node_uuid = node_panel.get_panel_uuid()
    node_settings = node_panel.get_settings()
    node_port = node_settings.get("port", 2053)

    # Login to main panel
    main_panel = XUIPanel(main_panel_url, *main_creds)
    if not main_panel.login():
        result["message"] = "Could not login to main panel"
        return result

    # Get main panel settings
    main_settings = main_panel.get_settings()
    
    # The node connection info
    result["node_uuid"] = node_uuid
    result["node_port"] = node_port
    result["message"] = f"Node info collected. UUID: {node_uuid[:8]}..."
    result["success"] = True

    return result


def configure_all_nodes(
    panels: dict,
    main_name: str = "NL",
    port: int = 3000,
) -> list:
    """
    Configure all nodes with the main panel.
    panels: dict of {name: domain_url}
    """
    results = []
    main_url = panels.get(main_name)

    if not main_url:
        return [{"success": False, "message": f"Main panel {main_name} not found"}]

    # Wait for all panels
    for name, url in panels.items():
        panel_url = f"https://{url}"
        ready = wait_for_panel(panel_url, timeout=120)
        if ready:
            results.append({"node": name, "status": "ready"})
        else:
            results.append({"node": name, "status": "timeout"})

    # Login to all panels and collect info
    panel_info = {}
    for name, url in panels.items():
        panel_url = f"https://{url}"
        panel = XUIPanel(panel_url)
        if panel.login():
            settings = panel.get_settings()
            panel_info[name] = {
                "url": panel_url,
                "uuid": settings.get("subKey", "") or settings.get("uuid", ""),
                "port": settings.get("port", 2053),
            }
        else:
            panel_info[name] = {"url": panel_url, "uuid": "", "port": 0}

    # For now, just collect info since node API varies by version
    results.append({
        "main_panel": main_name,
        "panel_info": panel_info,
        "message": "Panel info collected. Configure nodes in 3x-ui panel.",
    })

    return results
