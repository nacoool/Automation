# PR Verification Script

This script automates the verification of GitHub PR changes against a remote Satellite codebase.

## Overview

The verification process involves:
1. Fetching PR changes from GitHub API which can also be fetched through Jira Card
2. Connecting to a remote Satellite server
3. Validating that expected changes are present in the codebase in remote Satellite server
4. Generating a verification report

## Files

- `Verify_PR.py` - Main script that fetches PR changes and orchestrates verification
- `ssh2machine.sh` - Bash script for remote server operations
- `Verify_CodeBase.py` - Script that runs on remote server to validate changes
- `validations.yaml` - Configuration file with PR details and expected changes
- `validations_template.yaml` - Template for creating new validation files

## Usage

### Basic Usage
```bash
python3 Verify_PR.py
```

### With GitHub PR URL
```bash
python3 Verify_PR.py <GitHub-PR-URL>
```

### With SAT number
```bash
python3 Verify_PR.py <SAT-number>
```

### With custom hostname
```bash
python3 Verify_PR.py <PR-URL-or-SAT> <hostname>
```

## Configuration

Edit `validations.yaml` to configure:
- Remote server details (host, user, password, directory)
- JIRA token for JIRA account login
- Expected changes from PR

### JIRA Token Setup
The script handles JIRA token authentication in the following order:
1. **validations.yaml configuration**: JIRA token specified in validations.yaml takes precedence.
2. **Environment variable**: If token is not provided in validations.yaml, checks for `JIRA_TOKEN` environment variable.
3. **Interactive prompt**: If neither is found, the script will ask if you want to set it:
   ```
   JIRA_TOKEN is not set
   Do you want to set the JIRA_TOKEN? (y/n)
   ```
   - If you choose "y", it will prompt for the token and add it to `~/.bashrc`
   - You will be directed to run: `source ~/.bashrc`, after the script ends.
4. **Manual setup**: Alternatively, you can manually set up the JIRA token by adding the following to ~/.bashrc:
   ```
   export JIRA_TOKEN="YOUR_TOKEN_HERE"
   ```
   Then run: `source ~/.bashrc`'

### Configuration Precedence Rules

**Important**: You cannot have both `Jira_Card` and `GitHub_PR` in `validations.yaml` at the same time.

The script follows this precedence order:
1. **Command line arguments** always take precedence over `validations.yaml`
2. If you provide a SAT number or GitHub PR URL as command line argument, it will override any values in `validations.yaml`
3. If no command line arguments are provided, the script uses values from `validations.yaml`


## Requirements
- Python 3.x
- Required packages (see `requirements.txt`):
  - PyGithub
  - paramiko
- `sshpass` utility for SSH automation
- Access to remote Satellite server


## Example

```bash
# Verify changes from SAT-12345
python3 Verify_PR.py SAT-12345

# Verify changes from GitHub PR
python3 Verify_PR.py https://github.com/org/repo/pull/123

# Verify changes from SAT-12345 into Satellite server
python3 Verify_PR.py SAT-12345 abc.example.com

# Verify changes from GitHub PR into Satellite server
python3 Verify_PR.py https://github.com/org/repo/pull/123 abc.example.com
```
