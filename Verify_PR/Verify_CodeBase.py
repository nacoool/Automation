import os
from pathlib import Path
import yaml

# Load the expected changes from the validations.yaml file
with open('validations.yaml', 'r') as file:
    expected_changes = yaml.safe_load(file)
    expected_changes = expected_changes["expected_changes"]


def check_if_file_exists(file_path, root="/"):
    """Find file(s) matching rel_path anywhere under root using os.walk."""
    
    matches = []
    rel_parts = file_path.split(os.sep)
    # Walk through the root directory and find the file
    for dirpath, _, filenames in os.walk(root, topdown=True, followlinks=False):
        # quick exit if last component doesn't match any file in current directory
        if rel_parts[-1] not in filenames:
            continue

        for fname in filenames:
            if fname == rel_parts[-1]:
                candidate = os.path.join(dirpath, fname)
                # normalize to check if the tail path matches rel_path
                try:
                    if os.path.normpath(candidate).endswith(os.path.normpath(file_path)):
                        matches.append(candidate)
                except Exception:
                    continue
    return matches


def file_contains_changes(file_paths, expected_mapping):
    """Check if all expected 'added' and 'removed' line-specific changes exist in the given file."""
    all_verified = True  # Track overall success
    # Check if all expected 'added' and 'removed' line-specific changes exist in the given file
    for file_path in file_paths:
        try:
            with open(file_path, "r") as f:
                lines = f.readlines()
            # Check added lines
            for line_no_str, expected_text in expected_mapping.get("added", {}).items():
                line_no = int(line_no_str)
                if line_no <= len(lines):
                    actual_line = lines[line_no - 1].strip()
                    if expected_text in actual_line:
                        print(f"{file_path}: line {line_no} correctly contains ADDED text")
                    else:
                        print(f"{file_path}: mismatch at line {line_no} (ADDED check)")
                        print(f"   Expected: {expected_text}")
                        print(f"   Found:    {actual_line}\n")
                        all_verified = False
                else:
                    print(f"{file_path}: line {line_no} does not exist for ADDED check (file has {len(lines)} lines)")
                    all_verified = False

            # Check removed lines
            for line_no_str, expected_text in expected_mapping.get("removed", {}).items():
                line_no = int(line_no_str)
                if line_no <= len(lines):
                    actual_line = lines[line_no - 1].strip()
                    if expected_text != actual_line:
                        print(f"{file_path}: line {line_no} correctly does NOT contain REMOVED text")
                    else:
                        print(f"{file_path}: mismatch at line {line_no} (REMOVED check)")
                        print(f"   Expected REMOVED: {expected_text}")
                        print(f"   Still Found:      {actual_line}\n")
                        all_verified = False
                else:
                    print(f"{file_path}: line {line_no} does not exist for REMOVED check (file has {len(lines)} lines)")
                    all_verified = False

        except Exception as e:
            print(f"{file_path}: error reading file: {e}")
            all_verified = False
            continue
    # Final message
    if all_verified:
        print(f"\n✅ {file_path} is VERIFIED successfully and are reflected in the satellite codebase.")
    else:
        print(f"\n❌  {file_path} is NOT verified. Please review the mismatches above.\n")


for key in expected_changes:
    file_path = key
    file_paths = check_if_file_exists(file_path)
    if file_paths:
        file_contains_changes(file_paths, expected_changes[key])
    else:
        print(f"❌ {file_path} does not exist in the satellite codebase.")