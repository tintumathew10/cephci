import glob
import json
import logging
import os
import shutil
import sys
import xml.etree.ElementTree as ET


def _get_testsuite_summary(attrib):
    # Get test suite details
    name, time = attrib.get("name"), float(attrib.get("time")) / 60

    # Get test suite count
    total, failed, skipped = (
        int(attrib.get("tests")),
        int(attrib.get("failures")),
        int(attrib.get("skipped")),
    )

    # Set test suite status
    status = "FAIL" if failed > 0 else "PASS"

    # Get passed test cases
    passed = total - (failed + skipped)

    # Create dict with details
    return dict(
        name=name,
        status=status,
        total=total,
        passed=passed,
        failed=failed,
        skipped=skipped,
        time=round(time),
    )


def _update_testcase_property(testcase):
    # Update testrail ids
    for prop in testcase:
        if not (prop.tag == "failure" and prop.attrib.get("type") == "error"):
            continue
    pass


def generate_results():
    result = None

    # Check for xUnit file
    source = "/Users/tintumathew/ceph/cephci/cephci/tr_utils/sample.xml"

    # Create xUnit specific to test suite file
    root = ET.parse(source).getroot()
    for child in root:
        # Check for test suite tag
        if not child.tag == "testsuite":
            continue

        # Get test suite results summary
        result = _get_testsuite_summary(child.attrib)
        print("results = %s ", result)

        for testcase in child:
            # Check for test case details
            if not testcase.tag == "testcase":
                continue

            # Update test case failure
            print(testcase.get("name"))
            props_tag = testcase.find('properties')
            if props_tag:
                for props in props_tag.findall('property'):
                    print(props.get("name"))

    # Update testsuite to result
    # xunit = os.path.join(results, f"{os.path.basename(suite)}.xml")
    # print(f"Updating xunit results for '{xunit}'")

    # with open(xunit, "wb") as _f:
    #     _f.write(ET.tostring(root))

    # return result


if __name__ == "__main__":
    generate_results()
