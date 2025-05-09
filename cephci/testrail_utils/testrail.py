import base64
import configparser
import yaml
import json
import os
import requests

custom_fields = ["test_case_id", "title", "description", "component",
                 "tier", "ceph_mptc", "ceph_mrtc", "subcomponent", "release",
                 "tags", "status", "priority", "testtype",
                 "type", "assignee", "customerscenario", "categories",
                 "caseautomation", "automation_script", "author", "upstream"]

components = ["RADOS", "RBD", "Ceph-Ansible", "Ceph-Mgr", "Ceph-Volume", "CephFS",
              "iSCSI", "RBD-Mirror", "RGW-Multisite", "Web-UI", "CephAdm", "NVMe", "NFS-Ganesha",
              "Call-Home-Agent", "SMB", "vSphere-Plugin"]


class ApiError(Exception):
    """Custom exception for TestRail API errors."""
    pass


class TestRailApi:
    def __init__(self, base_url, user, api_key):
        """
        Initializes the TestRail API client with authentication details.

        Args:
            base_url (str): The base URL of the TestRail instance (e.g., "https://yourcompany.testrail.io").
            user (str): The username or email address used to authenticate with the TestRail API.
            api_key (str): The API key or password for the TestRail user.
        Notes:
            The method constructs the base API endpoint by appending the necessary path
            to the provided base URL.
        """
        self.user = user
        self.api_key = api_key
        self.base_url = base_url.rstrip("/") + "/index.php?/api/v2/"

    def _get_headers(self):
        """
        Generates HTTP headers for authenticating with the TestRail API using Basic Auth.
        Returns:
            dict: A dictionary of headers required for TestRail API requests:
                - 'Authorization': Basic authentication header.
                - 'Content-Type': JSON content type.
        """
        auth = base64.b64encode(f"{self.user}:{self.api_key}".encode()).decode()
        return {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/json"
        }

    def _request(self, method, uri, data=None):
        """
        Sends an HTTP request to the TestRail API with proper authentication and error handling.

        Args:
            method (str): The HTTP method to use (e.g., 'GET', 'POST', 'PUT').
            uri (str): The API endpoint path relative to the base URL.
            data (dict, optional): JSON-serializable payload to include in the request body (for POST/PUT).
        Returns:
            dict: The parsed JSON response from the API.
        Raises:
            ApiError: If the response status code is not 200, with error details included.
        """
        url = self.base_url + uri
        response = requests.request(method, url, headers=self._get_headers(), json=data)
        if response.status_code != 200:
            raise ApiError(f"TestRail API error {response.status_code}: {response.text}")
        return response.json()

    def get_projects(self):
        """
        Retrieves a list of all projects from the TestRail API.
        Returns:
            dict: A dictionary containing project data, typically under the 'projects' key.
        """
        return self._request("GET", "get_projects")

    def get_project_id(self, name):
        """
        Retrieves the TestRail project ID that matches the given project name.

        Args:
            name (str): The name of the project to look for.
        Returns:
            int or str: The ID of the matching project if found, otherwise an empty string.
        """
        return next((p["id"] for p in self.get_projects()["projects"] if p["name"] == name), "")

    def get_templates(self, project_id):
        """
        Retrieves a list of test case templates for a specific project.

        Args:
            project_id (int or str): The ID of the TestRail project.
        Returns:
            list[dict]: A list of template dictionaries associated with the given project.
        """
        return self._request("GET", f"get_templates/{project_id}")

    def get_template_id(self, project_id, name):
        """
        Retrieves the ID of a test case template by name for a specific project.

        Args:
            project_id (int or str): The ID of the TestRail project.
            name (str): The name of the template to look for.

        Returns:
            int or str: The template ID if found, otherwise an empty string.
        """
        return next((t["id"] for t in self.get_templates(project_id) if t["name"] == name), "")

    def get_case_fields(self):
        """
        Retrieves the list of custom and default case fields available in TestRail.

        Returns:
            list[dict]: A list of dictionaries representing case fields.
        """
        return self._request("GET", "get_case_fields")

    def add_case_field(self, body):
        """
        Adds a new custom case field to TestRail.

        Args:
            body (dict): A dictionary containing the parameters and configuration
                    for the new case field (e.g., name, type, system_name, etc.).
        Returns:
            dict: The API response confirming creation of the case field.
        """
        return self._request("POST", "add_case_field", body)

    def get_sections(self, project_id):
        """
        Retrieves all sections for a given TestRail project.

        Args:
            project_id (int or str): The ID of the TestRail project.
        Returns:
            dict: The API response containing sections, typically under the 'sections' key.
        """
        return self._request("GET", f"get_sections/{project_id}")

    def get_section_id(self, project_id, name):
        """
        Retrieves the section ID for a given section name in a TestRail project.

        Args:
            project_id (int or str): The ID of the TestRail project.
            name (str): The name of the section to find.
        Returns:
            int or str: The ID of the matching section, or an empty string if not found.
        """
        return next((s["id"] for s in self.get_sections(project_id)["sections"] if s["name"] == name), "")

    def add_section(self, project_id, name, description):
        """
        Adds a new section to a TestRail project.

        Args:
            project_id (int or str): The ID of the TestRail project.
            name (str): The name of the new section.
            description (str): The description for the new section.
        Returns:
            dict: The API response containing details of the created section.
        """
        return self._request("POST", f"add_section/{project_id}", {"name": name, "description": description})

    def add_case(self, section_id, body):
        """
        Add a test case to the specified section.

        Args:
            section_id (int or str): The ID of the section to add the case to.
            body (dict): A dictionary containing the test case details.

        Returns:
            dict: The API response.
        """
        return self._request("POST", f"add_case/{section_id}", body)

    def get_cases(self, project_id):
        """
        Retrieve all test cases for the specified project.

        Args:
            project_id (int or str): The ID of the project.
        Returns:
            dict or list: The API response containing the test cases.
        """
        return self._request("GET", f"get_cases/{project_id}")

    def retrieve_testrail_ids(self, project_id):
        """
        Retrieves all test cases for the specified project from TestRail,
        mapping Polarion references to TestRail IDs and titles.
        Uses pagination to fetch all cases in batches of `limit` size.

        Args:
            project_id (int or str): The ID of the TestRail project.
        Returns:
            list of dict: A list of dictionaries, each containing:
                - 'polarion_id': The Polarion reference(s) for the test case.
                - 'testrail_id': The TestRail case ID.
                - 'title': The test case title.
        """
        offset = 0
        limit = 250
        pol_tr_map = []
        while True:
            response = self._request("GET", f"get_cases/{project_id}&limit={limit}&offset={offset}")
            cases = response.get("cases", [])
            if not cases:
                break
            for case in cases:
                pol_tr_map.append({
                    "polarion_id": case["refs"],
                    "testrail_id": case["id"],
                    "title": case["title"]
                })
            if len(cases) < limit:
                break
            offset += limit
        return pol_tr_map
