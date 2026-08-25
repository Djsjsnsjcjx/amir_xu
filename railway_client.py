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

            if resp.status_code == 401:
                raise Exception("توکن API نامعتبر است.")
            if resp.status_code != 200:
                raise Exception(f"HTTP {resp.status_code}: {resp.text[:300]}")

            data = resp.json()
            if "errors" in data:
                msgs = [e.get("message", str(e)) for e in data["errors"]]
                raise Exception(f"API Error: {'; '.join(msgs)}")

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

    def create_project(self, name: str, workspace_id: str) -> dict:
        """Create a new project"""
        query = """
        mutation projectCreate($input: ProjectCreateInput!) {
            projectCreate(input: $input) {
                id
                name
            }
        }
        """
        data = self._query(query, {"input": {"name": name, "workspaceId": workspace_id}})
        project = data.get("projectCreate")
        if not project or not project.get("id"):
            raise Exception("خطا در ایجاد پروژه")
        return project

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

    def create_service_from_repo(
        self, name: str, project_id: str, repo: str, branch: str = "main"
    ) -> dict:
        """Create a service from a GitHub repository"""
        query = """
        mutation serviceCreate($input: ServiceCreateInput!) {
            serviceCreate(input: $input) {
                id
                name
            }
        }
        """
        input_data = {
            "projectId": project_id,
            "name": name,
            "source": {"repo": repo},
            "branch": branch,
        }
        data = self._query(query, {"input": input_data})
        service = data.get("serviceCreate")
        if not service or not service.get("id"):
            raise Exception(f"خطا در ایجاد سرویس {name}")
        return service

    def create_service_from_image(
        self, name: str, project_id: str, image: str
    ) -> dict:
        """Create a service from a Docker image"""
        query = """
        mutation serviceCreate($input: ServiceCreateInput!) {
            serviceCreate(input: $input) {
                id
                name
            }
        }
        """
        input_data = {
            "projectId": project_id,
            "name": name,
            "source": {"image": image},
        }
        data = self._query(query, {"input": input_data})
        service = data.get("serviceCreate")
        if not service or not service.get("id"):
            raise Exception(f"خطا در ایجاد سرویس {name}")
        return service

    def deploy_service(self, service_id: str, environment_id: str) -> dict:
        """Deploy a service"""
        query = """
        mutation serviceInstanceDeploy($serviceId: String!, $environmentId: String!) {
            serviceInstanceDeploy(serviceId: $serviceId, environmentId: $environmentId)
        }
        """
        data = self._query(query, {"serviceId": service_id, "environmentId": environment_id})
        result = data.get("serviceInstanceDeploy")
        if not result:
            raise Exception("خطا در شروع دپلوی")
        return {"success": result}

    def create_service_domain(self, service_id: str, environment_id: str, target_port: int = 3000) -> dict:
        """Create a public domain for a service"""
        query = """
        mutation serviceDomainCreate($input: ServiceDomainCreateInput!) {
            serviceDomainCreate(input: $input) {
                id
                domain
            }
        }
        """
        input_data = {
            "serviceId": service_id,
            "environmentId": environment_id,
            "targetPort": target_port,
        }
        data = self._query(query, {"input": input_data})
        result = data.get("serviceDomainCreate")
        if not result:
            raise Exception("خطا در ایجاد دامین")
        return result

    def get_service_domains(self, project_id: str, environment_id: str, service_id: str) -> list:
        """Get domains for a service"""
        query = """
        query domains($projectId: String!, $environmentId: String!, $serviceId: String!) {
            domains(projectId: $projectId, environmentId: $environmentId, serviceId: $serviceId) {
                serviceDomains {
                    id
                    domain
                }
            }
        }
        """
        data = self._query(query, {
            "projectId": project_id,
            "environmentId": environment_id,
            "serviceId": service_id,
        })
        return data.get("domains", {}).get("serviceDomains", [])
