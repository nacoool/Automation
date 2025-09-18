import sys
import os
import subprocess
import requests
import yaml
import re
from pathlib import Path


def get_satellite_pr_info(issue_name, token=None):
    """Get the PR URL from the JIRA card"""
    JIRA_URL = "https://issues.redhat.com"   # Or server Jira URL
    if token is None:
        API_TOKEN = os.getenv("JIRA_TOKEN")
    else:
        API_TOKEN = token
    API_TOKEN = os.getenv("JIRA_TOKEN")
    if API_TOKEN is None:
        # Prompt the user to set the JIRA_TOKEN
        print("JIRA_TOKEN is not set")
        print("Do you want to set the JIRA_TOKEN? (y/n)")
        if input() == "y":
            API_TOKEN = input("Enter the JIRA_TOKEN: ")
            export_jira_token(API_TOKEN)
        else:
            raise ValueError("JIRA_TOKEN is not set")
    # Search the JIRA card for the PR URL
    Search_URL=f"{JIRA_URL}/rest/api/latest/search/"
    params = {"jql": f"id = {issue_name}", "fields": "customfield_12316846"}
    response = requests.get(Search_URL,headers={"Authorization": f"Bearer {API_TOKEN}"},params=params)
    if response.status_code == 200:
        issue = response.json()
        pr_url = issue["issues"][0]["fields"]["customfield_12316846"]
        if not pr_url:
            raise ValueError("No PR URL found for the JIRA card")
        print(f"GITHUB PR: {pr_url}")
        return pr_url
    else:
        print(f"Error: {response.status_code}")
        print(response.text)


def print_usage():
    """Print usage instructions for the script."""
    usage = (
        "Usage:\n"
        "  python3 verify_pr.py <GitHub-PR-URL> <Remote-Host>\n"
        "  or\n"
        "  python3 verify_pr.py <SAT-number> <Remote-Host>\n"
        "  or\n"
        "  python3 verify_pr.py <GitHub-PR-URL>\n"
        "  or\n"
        "  python3 verify_pr.py <SAT-number>\n"
        "  or\n"
        "  python3 verify_pr.py"
    )
    print(usage)


def fetch_pr_changes(pr_url: str):
    """Fetch the changes from the PR"""

    match = re.match(r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)", pr_url)
    if not match:
        raise ValueError("Invalid PR URL format. Example: https://github.com/org/repo/pull/123")

    owner, repo, pr_number = match.groups()

    # GitHub API endpoint for PR files
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
    response = requests.get(url)

    if response.status_code != 200:
        raise Exception(f"Failed to fetch PR files: {response.status_code}, {response.text}")

    files = response.json()
    expected_changes = {}
    # Walk through the files and get the changes
    for file in files:
        filename = file["filename"]
        patch = file.get("patch", "")

        changes = {"added": {}, "removed": {}}
        current_added_line = None
        current_removed_line = None
        # Skip test files
        if filename.endswith("_test.rb") and filename.startswith("test/"):
            print(f"Skipping test file: {filename}")
            continue

        # Walk through the lines and get the changes
        for line in patch.split("\n"):
            if line.startswith("@@"):
                # Extract both old and new line numbers from hunk header
                # Format: @@ -old_start,old_count +new_start,new_count @@
                old_match = re.search(r"-(\d+)", line)
                new_match = re.search(r"\+(\d+)", line)
                
                if old_match:
                    current_removed_line = int(old_match.group(1))
                if new_match:
                    current_added_line = int(new_match.group(1))
                    
            elif line.startswith("+") and not line.startswith("+++"):
                # Added line - use new line number
                if current_added_line is not None:
                    changes["added"][str(current_added_line)] = line[1:].strip()
                    current_added_line += 1
                    
            elif line.startswith("-") and not line.startswith("---"):
                # Removed line - use old line number
                if current_removed_line is not None:
                    changes["removed"][str(current_removed_line)] = line[1:].strip()
                    current_removed_line += 1
                    
            else:
                # Context line (unchanged) - increment both counters
                if current_added_line is not None:
                    current_added_line += 1
                if current_removed_line is not None:
                    current_removed_line += 1

        if changes["added"] or changes["removed"]:
            expected_changes[filename] = changes

    return expected_changes

def export_jira_token(API_TOKEN):
    """Export the JIRA_TOKEN to the .bashrc file"""
    bashrc = Path.home() / ".bashrc"
    export_line = f'export JIRA_TOKEN="{API_TOKEN}"\n'
    with open(bashrc, "a") as f:
        f.write(f"\n{export_line}")
    print("  JIRA_TOKEN added to ~/.bashrc")
    print("⚠️ To use it in your current session, run this command manually:")
    print("⚠️ source ~/.bashrc")



if __name__ == "__main__":
    if len(sys.argv) <= 3:
        try:
            with open("validations.yaml", "r") as f:
                data = yaml.safe_load(f)
                hostname=data["Remote_Details"]["host"]

        except FileNotFoundError:
            print("validations.yaml file not found")
            sys.exit(1)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
        # If only one argument is provided, get the PR URL from the JIRA card or GitHub PR URL
        if len(sys.argv) == 2:
            if sys.argv[1][:3] == "SAT":
                github_pr = get_satellite_pr_info(sys.argv[1], data["Jira_Token"])
            elif "github.com" in sys.argv[1]:
                github_pr = sys.argv[1]
        # If two arguments are provided, get the PR URL from the JIRA card or GitHub PR URL
        elif len(sys.argv) == 3:
            if sys.argv[1][:3] == "SAT":
                github_pr = get_satellite_pr_info(sys.argv[1], data["Jira_Token"])
            elif "github.com" in sys.argv[1]:
                github_pr = sys.argv[1]
            hostname=sys.argv[2]
        else:
            # If no arguments are provided, get the PR URL from the JIRA card or GitHub PR URL
            if data["Jira_Card"] and not data["GitHub_PR"]:
                github_pr = get_satellite_pr_info(data["Jira_Card"], data["Jira_Token"])
            elif data["GitHub_PR"] and not data["Jira_Card"]:
                github_pr = data["GitHub_PR"]
            else:
                raise KeyError("No Jira_Card or GitHub_PR or both found in validations.yaml")

        result = fetch_pr_changes(github_pr)
        print("expected_changes:")
        for f, lines in result.items():
            print(f"{f}:")
            for num, content in lines.items():
                print(f'"{num}": ')
                print(f'  {content}')
                print()
        data["expected_changes"] = result
        with open("validations.yaml", "w") as f:
            yaml.dump(data, f)
        # If no hostname is provided, get the hostname from the validations.yaml file
        if not hostname:
            hostname = data["Remote_Details"]["host"]
        password = data["Remote_Details"]["pass"]
        if not password:
            password = input("Enter Satellite password: ")
        user = data["Remote_Details"]["user"]
        dir = data["Remote_Details"]["dir"]
        # Run the ssh2machine.sh script
        result = subprocess.run(
            ["bash", "ssh2machine.sh", hostname, user, password, dir],
            capture_output=True,
            text=True,
            check=True
        )
        print(result.stdout)
        if result.stderr:
            print(result.stderr)

    else:
        print_usage()
        sys.exit(1)
