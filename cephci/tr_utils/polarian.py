import os
import json
from bs4 import BeautifulSoup
from pylero.work_item import TestCase

COMPONENTS = [
    "RADOS", "RBD", "RGW", "Ceph-Ansible", "Ceph-Mgr", "Ceph-Volume", "CephFS",
    "iSCSI", "RBD-Mirror", "RGW-Multisite", "Web-UI", "CephAdm", "NVMe", "NFS-Ganesha",
    "Call-Home-Agent", "SMB", "vSphere-Plugin"
]

TESTCASE_QUERY = "type:testcase AND casecomponent:{} AND status:approved"
FIELDS = [
    "work_item_id", "title", "description", "casecomponent", "tier", "mptc", "mrtc",
    "subcomponent", "release", "severity", "tags", "status", "priority", "testtype",
    "type", "hyperlinks", "location", "assignee", "attachments", "work_records", "upstream",
    "resolution", "project_id", "linked_work_items", "day2operation", "customerscenario",
    "comments", "categories", "caseimportance", "caseautomation", "automation_script", "author"
]


def extract_text(html_content):
    """Extract plain text from HTML."""
    return BeautifulSoup(html_content, 'html.parser').get_text() if html_content else ""


def process_test_steps(test_steps):
    """Convert test steps into a structured list."""
    return [
        {
            "content": extract_text(step.values[0].content),
            "expected": extract_text(step.values[1].content) if len(step.values) > 1 else ""
        }
        for step in test_steps.steps
    ]


def fetch_testcases(component):
    """Retrieve test cases for a specific component."""
    return TestCase.query(TESTCASE_QUERY.format(component), FIELDS)


def serialize_testcase(test):
    """Convert a test case into a structured dictionary."""
    # print(type(test.release), test.release)
    # val = getattr(test, "release")
    # print(val)
    return {
        "test_case_id": test.work_item_id,
        "title": test.title,
        "description": extract_text(test.description),
        "component": test.casecomponent,
        "tier": test.tier,
        "mptc": test.mptc,
        "mrtc": test.mrtc,
        "subcomponent": test.subcomponent,
        "release": test.release,
        "severity": test.severity,
        "tags": test.tags,
        "status": test.status,
        "test_steps": process_test_steps(test.get_test_steps()),
        "priority": test.priority,
        "testtype": test.testtype,
        "type": test.type,
        "hyperlinks": next((link.uri for link in test.hyperlinks if link.uri), ""),
        "location": test.location,
        "assignee": next((assignee.name for assignee in test.assignee if assignee.name), ""),
        "attachments": next((attachment.file_name for attachment in test.attachments if attachment.file_name), ""),
        "work_records": test.work_records,
        "resolution": test.resolution,
        "project_id": test.project_id,
        "linked_work_items": [item.work_item_id for item in test.linked_work_items],
        "day2operation": test.day2operation,
        "customerscenario": test.customerscenario,
        "comments": [comment.text for comment in test.comments] if test.comments else [],
        "categories": test.categories,
        "caseimportance": test.caseimportance,
        "caseautomation": test.caseautomation,
        "upstream": test.upstream,
        "automation_script": extract_text(test.automation_script),
        "author": test.author
    }


def save_testcases(components):
    """Fetch and save test cases for each component."""
    for component in components:
        testcases = fetch_testcases(component)
        data = [serialize_testcase(tc) for tc in testcases]
        # file_path = os.path.join(os.path.dirname(os.getcwd()), f"{component}.json")

        # with open(file_path, 'w') as f:
        #     json.dump(data, f, indent=4)

        print(f"Saved {len(data)} test cases for {component}.")


save_testcases(COMPONENTS)
