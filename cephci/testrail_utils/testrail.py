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
    pass


class TestRailApi:
    def __init__(self, base_url, user, api_key):
        self.user = user
        self.api_key = api_key
        self.base_url = base_url.rstrip("/") + "/index.php?/api/v2/"

    def _get_headers(self):
        auth = base64.b64encode(f"{self.user}:{self.api_key}".encode()).decode()
        return {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}

    def _request(self, method, uri, data=None):
        url = self.base_url + uri
        response = requests.request(method, url, headers=self._get_headers(), json=data)
        if response.status_code != 200:
            raise ApiError(f"TestRail API error {response.status_code}: {response.text}")
        return response.json()

    def get_projects(self):
        return self._request("GET", "get_projects")

    def get_project_id(self, name):
        return next((p["id"] for p in self.get_projects()["projects"] if p["name"] == name), "")

    def get_templates(self, project_id):
        return self._request("GET", f"get_templates/{project_id}")

    def get_template_id(self, project_id, name):
        return next((t["id"] for t in self.get_templates(project_id) if t["name"] == name), "")

    def get_case_fields(self):
        return self._request("GET", "get_case_fields")

    def add_case_field(self, body):
        return self._request("POST", "add_case_field", body)

    def get_sections(self, project_id):
        return self._request("GET", f"get_sections/{project_id}")

    def get_section_id(self, project_id, name):
        return next((s["id"] for s in self.get_sections(project_id)["sections"] if s["name"] == name), "")

    def add_section(self, project_id, name, description):
        return self._request("POST", f"add_section/{project_id}", {"name": name, "description": description})

    def add_case(self, section_id, body):
        return self._request("POST", f"add_case/{section_id}", body)

    def get_cases(self, project_id):
        return self._request("GET", f"get_cases/{project_id}")

    def retrieve_testrail_ids(self, project_id):
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
                    "polarian_id": case["refs"],
                    "testrail_id": case["id"],
                    "title": case["title"]
                })
            if len(cases) < limit:
                break
            offset += limit
        file_path = os.path.join(os.path.dirname(os.getcwd()), "testrail_data.json")
        with open(file_path, 'w') as f:
            json.dump(pol_tr_map, f, indent=4)
