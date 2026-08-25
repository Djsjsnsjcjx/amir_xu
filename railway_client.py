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

        logger.info(f"GraphQL Request: {query[:200]}...")
        logger.info(f"Variables: {json.dumps(variables, default=str)[:200]}")

        try:
            resp = requests.post(
                RAILWAY_API_URL,
                json=payload,
                headers=self.headers,
                timeout=30,
            )
            
            logger.info(f"Response status: {resp.status_code}")
            logger.info(f"Response body: {resp.text[:500]}")

            if resp.status_code != 200:
                raise Exception(f"HTTP {resp.status_code}: {resp.text[:200]}")

            data = resp.json()

            if "errors" in data:
                error_messages = [e.get("message", str(e)) for e in data["errors"]]
                raise Exception(f"GraphQL errors: {'; '.join(error_messages)}")

            return data.get("data", {})
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise Exception("توکن API نامعتبر است. لطفاً توکن صحیح را وارد کنید.")
            raise Exception(f"خطا در اتصال به Railway API: {e}")
        except requests.exceptions.ConnectionError:
            raise Exception("خطا در اتصال به اینترنت. لطفاً اتصال خود را بررسی کنید.")

    def get_me(self) -> dict:
        """Get current user info and teams"""
        query = """
        query {
            me {
                id
                name
                email
                teams {
                    edges {
                        node {
                            id
                            name
                        }
                    }
                }
            }
        }
        """
        data = self._query(query)
        user = data.get("me")
        if not user:
            raise Exception("نتوانست اطلاعات کاربر را دریافت کند")
        return user

    def create_project(self, name: str, team_id: str = None) -> dict:
        """Create a new project"""
        input_data = {"name": name}
        if team_id:
            input_data["teamId"] = team_id

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
            "name": name,
            "projectId": project_id,
            "source": {"image": image},
        }
        data = self._query(query, {"input": input_data})
        service = data.get("serviceCreate")
        if not service or not service.get("id"):
            raise Exception(f"خطا در ایجاد سرویس {name}")
        return service

    def trigger_deployment(self, service_id: str) -> dict:
        """Trigger a new deployment for a service"""
        query = """
        mutation deploymentTrigger($input: DeploymentTriggerInput!) {
            deploymentTrigger(input: $input) {
                id
                status
            }
        }
        """
        input_data = {"serviceId": service_id}
        data = self._query(query, {"input": input_data})
        deployment = data.get("deploymentTrigger")
        if not deployment:
            raise Exception("خطا در شروع دپلوی")
        return deployment

    def get_deployment_status(self, service_id: str) -> dict:
        """Get latest deployment status for a service"""
        query = """
        query deployments($serviceId: String!) {
            deployments(input: { serviceId: $serviceId, limit: 1 }) {
                edges {
                    node {
                        id
                        status
                        createdAt
                    }
                }
            }
        }
        """
        data = self._query(query, {"serviceId": service_id})
        deployments = data.get("deployments", {}).get("edges", [])
        if deployments:
            return deployments[0].get("node", {})
        return {}

    def introspect(self) -> dict:
        """Introspect the GraphQL schema (for debugging)"""
        query = """
        query {
            __schema {
                mutationType {
                    fields {
                        name
                        args {
                            name
                            type {
                                name
                            }
                        }
                    }
                }
                queryType {
                    fields {
                        name
                    }
                }
            }
        }
        """
        return self._query(query)
