from testrail import TestRailApi
import os
import yaml
from pathlib import Path
from docopt import docopt


suite_dirs = ["suites/squid"]

doc = """
Utility to update testrail ids in test suite files

    Usage:
       cephci/testrail_utils/update_testrail_ids.py (--config <FILE>)
                            (--test-suite <FILE/DIR>)

       cephci/testrail_utils/update_testrail_ids.py --help

    Options:
       -h --help                    Help
       -c --config <FILE>           Configuration details of testrail
       -t --test-suite <FILE/DIR>   Test suite file or suite directory
"""


def update_testsuites(filename, polarian_testrail_map):
    """
    Update test cases in a YAML file by mapping Polarion IDs to TestRail IDs.
    Args:
        filename (str or Path): Path to the YAML file to update.
        polarian_testrail_map (list of dict): A list of mappings where each dictionary contains:
            - "polarion_id" (str): The ID used in Polarion.
            - "testrail_id" (str or int): The corresponding ID used in TestRail.
    """
    with open(filename, 'r') as f:
        data = yaml.safe_load(f)

    updated = 0
    for test_entry in data.get("tests", []):
        test_block = test_entry.get("test", {})
        polarion_id = test_block.get("polarion-id")

        if polarion_id:
            for mapping in polarian_testrail_map:
                if polarion_id == mapping.get("polarion_id"):
                    test_block["testrail-id"] = mapping.get("testrail_id")
                    updated += 1
                    break  # Stop after first match

    with open(filename, 'w') as f:
        yaml.dump(data, f, sort_keys=False)

    print(f"Updated {updated} test(s) in {filename}")


def get_all_yaml_files(directory):
    """
    Recursively collect all .yaml and .yml files in a given directory.

    Args:
        directory (str or Path): The directory to search.

    Returns:
        list of Path: A sorted list of YAML file paths.
    """
    directory = Path(directory)
    yaml_files = set(directory.rglob("*.yaml")) | set(directory.rglob("*.yml"))
    return sorted(yaml_files)


if __name__ == "__main__":

    args = docopt(doc)

    # Get testrail config file and test suite file or directory
    config = args.get("--config")
    suite = args.get("--test-suite")

    if not config or not suite:
        print("Error: Both --config and --test-suite arguments are required.")
        exit(1)

    if os.path.isfile(config):
        try:
            with open(config, "r") as file:
                data = yaml.safe_load(file)
        except Exception as e:
            print(f"Error reading the file: {e}")
            exit(1)
    else:
        print(f"Config file not found: {config}")
        exit(1)

    required_keys = ["username", "password"]
    if not all(k in data for k in required_keys):
        print(f"Error: Missing required keys in config file: {required_keys}")
        exit(1)

    base_url = "https://ibmsandbox.testrail.io/"
    username = data["username"]
    password = data["password"]
    project_name = "Ceph"
    tr_api = TestRailApi(base_url, username, password)
    project_id = tr_api.get_project_id(project_name)
    polarian_testrail_map = tr_api.retrieve_testrail_ids(project_id)
    filenames = []
    if os.path.isfile(suite):
        filenames.append(suite)
    elif os.path.isdir(suite):
        filenames.extend(get_all_yaml_files(suite))
    if polarian_testrail_map and filenames:
        for filename in filenames:
            update_testsuites(filename, polarian_testrail_map)
