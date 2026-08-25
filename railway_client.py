"""
Railway GraphQL API Client
Handles all interactions with Railway's API v2
"""

import requests
import json
import logging

logger = logging.getLogger(__name__)

RAILWAY_API_URL = "https://api.railway.app/graphql/v2"


class RailwayClient:
    def __init__(self, api_token: str):
        self.api_token = api_token
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }

    def _query(self, query: str, variables: dict = None) -> dict:
        """Execute a GraphQL query/mutation"""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        try:
            resp = requests.post(
                RAILWAY_API_URL,
                json=payload,
                headers=self.headers,
                timeout=30,
            )
            
            logger.info(f"Response status: {resp.status_code}")

            if resp.status_code == 401:
                raise Exception("توکن API نامعتبر است.")
            
            if resp.status_code != 200:
                raise Exception(f"HTTP {resp.status_code}: {resp.text[:300]}")

            data = resp.json()

            if "errors" in data:
                error_messages = [e.get("message", str(e)) for e in data["errors"]]
                raise Exception(f"API Error: {'; '.join(error_messages)}")

            return data.get("data", {})
        except requests.exceptions.ConnectionError:
            raise Exception("خطا در اتصال به اینترنت.")

    def get_me(self) -> dict:
        """Get current user info and workspaces"""
        query = """
        query {
            me {
                id
                name
                email
                username
                workspaces {
                    id
                    name
                }
            }
        }
        """
        data = self._query(query)
        user = data.get("me")
        if not user:
            raise Exception("نتوانست اطلاعات کاربر را دریافت کند")
        return user

    def create_project(self, name: str, workspace_id: str = None) -> dict:
        """Create a new project"""
        input_data = {"name": name}
        if workspace_id:
            input_data["workspaceId"] = workspace_id

        query = """
        mutation projectCreate($input: ProjectCreateInput!) {
            projectCreate(input: $input) {
                id
                name
            }
        }
        """
        data = self._query(query, {"input": input_data})
        project = data.get("projectCreate")
        if not project or not project.get("id"):
            raise Exception("خطا در ایجاد پروژه")
        return project

    def create_service_from_image(
        self, name: str, project_id: str, image: str, environment_id: str = None
    ) -> dict:
        """Create a service from a Docker image"""
        input_data = {
            "projectId": project_id,
            "name": name,
            "source": {"image": image},
        }
        if environment_id:
            input_data["environmentId"] = environment_id

        query = """
        mutation serviceCreate($input: ServiceCreateInput!) {
            serviceCreate(input: $input) {
                id
                name
            }
        }
        """
        data = self._query(query, {"input": input_data})
        service = data.get("serviceCreate")
        if not service or not service.get("id"):
            raise Exception(f"خطا در ایجاد سرویس {name}")
        return service

    def deploy_service(self, service_id: str, environment_id: str) -> dict:
        """Deploy a service"""
        query = """
        mutation serviceInstanceDeploy($serviceId: String!, $environmentId: String!) {
            serviceInstanceDeploy(serviceId: $serviceId, environmentId: $environmentId) {
                id
                status
            }
        }
        """
        data = self._query(query, {"serviceId": service_id, "environmentId": environment_id})
        deployment = data.get("serviceInstanceDeploy")
        if not deployment:
            raise Exception("خطا در شروع دپلوی")
        return deployment

    def get_environments(self, project_id: str) -> list:
        """Get environments for a project"""
        query = """
        query environments($projectId: String!) {
            environments(projectId: $projectId) {
                edges {
                    node {
                        id
                        name
                    }
                }
            }
        }
        """
        data = self._query(query, {"projectId": project_id})
        return data.get("environments", {}).get("edges", [])

    def get_deployment_status(self, service_id: str, environment_id: str) -> dict:
        """Get latest deployment status for a service"""
        query = """
        query deployments($serviceId: String!, $environmentId: String!) {
            deployments(input: { serviceId: $serviceId, environmentId: $environmentId, limit: 1 }) {
                edges {
                    node {
                        id
                        status
                    }
                }
            }
        }
        """
        data = self._query(query, {"serviceId": service_id, "environmentId": environment_id})
        deployments = data.get("deployments", {}).get("edges", [])
        if deployments:
            return deployments[0].get("node", {})
        return {}
