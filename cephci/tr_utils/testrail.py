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


if __name__ == "__main__":

    # config_path = os.path.expanduser("~/.testrail_config.ini")
    # config = configparser.ConfigParser()
    # config.read(config_path)

    # base_url = config["ibm_sandbox"]["base_url"]
    # user = config["ibm_sandbox"]["user"]
    # api_key = config["ibm_sandbox"]["api_key"]
    # tr_api = TestRailApi(base_url, user, api_key)

    with open('/Users/tintumathew/tr_conf.yml', 'r') as file:
        data = yaml.safe_load(file)

    print(data)
    base_url = "https://ibmsandbox.testrail.io/"
    username = data["username"]
    password = data["password"]
    tr_api = TestRailApi(base_url, username, password)

    project_id = tr_api.get_project_id("Ceph")

    template_id = tr_api.get_template_id(project_id, "CephTemplate")
    print(template_id)
    # case_field_names = {f["name"] for f in tr_api.get_case_fields()}

    # field_configs = {
    #     "test_steps": {
    #         "type": "Steps",
    #         "options": {"format": "plain", "rows": "5", "has_expected": True}
    #     },
    #     "ceph_mrtc": {
    #         "type": "Dropdown",
    #         "options": {"format": "markdown", "items": "1, x\n2, y\n3, z"}
    #     },
    #     "ceph_mptc": {
    #         "type": "Dropdown",
    #         "options": {"format": "markdown", "items": "1, yes\n2, no"}
    #     },
    #     "upstream": {
    #         "type": "Dropdown",
    #         "options": {"format": "markdown", "items": "1, yes\n2, no"}
    #     }
    # }

    # for field in custom_fields:
    #     if field not in case_field_names:
    #         config = field_configs.get(field, {"type": "Text",
    #                                            "options": {"format": "plain", "rows": "5", "default_value": ""}})
    #         tr_api.add_case_field({
    #             "type": config["type"],
    #             "name": field,
    #             "label": field,
    #             "description": field,
    #             "configs": [{
    #                 "context": {"is_global": False, "project_ids": [project_id]},
    #                 "options": {"is_required": False, **config["options"]}
    #             }],
    #             "include_all": False,
    #             "template_ids": [template_id]
    #         })

    # for component in components:
    #     section_id = tr_api.get_section_id(project_id, component)
    #     if not section_id:
    #         section_id = tr_api.add_section(project_id, component, f"{component} test cases")["id"]

    #     file_path = os.path.join(os.path.dirname(os.getcwd()), f"{component}.json")
    #     if os.path.exists(file_path):
    #         with open(file_path, 'r') as f:
    #             cases = json.load(f)
    #             for case in cases:
    #                 tr_api.add_case(section_id, {
    #                     "title": case["title"][:250],
    #                     "template_id": template_id,
    #                     "custom_steps_separated": case["test_steps"],
    #                     "custom_status": case["status"],
    #                     "custom_ceph_automation_type": {"automated": 1, "manual": 2, "notautomated": 3}.get(
    #                         case.get("caseautomation"), ""),
    #                     "refs": case["test_case_id"],
    #                     "custom_description": case["description"][:250],
    #                     "custom_case_component": case["component"],
    #                     "custom_tier": case["tier"],
    #                     "custom_subcomponent": case["subcomponent"],
    #                     "custom_tags": case["tags"],
    #                     "custom_release": case["release"],
    #                     "custom_ceph_mptc": {"yes": 1, "no": 2}.get(case.get("mptc"), ""),
    #                     "custom_ceph_mrtc": {"x": 1, "y": 2, "z": 3}.get(case.get("mrtc"), ""),
    #                     "custom_priority": case["priority"],
    #                     "custom_testtype": case["testtype"],
    #                     "custom_assignee": case["assignee"],
    #                     "custom_customerscenario": f'{case["customerscenario"]}',
    #                     "custom_caseautomation": case["caseautomation"],
    #                     "custom_upstream": {"yes": 1, "no": 2}.get(case.get("upstream"), ""),
    #                     "custom_author": case["author"]
    #                 })

    # # Method to create polarion, testrail mapping json file
    # tr_api.retrieve_testrail_ids(project_id)
