# Patch PR

Apply GitHub PRs from Foreman/Hammer repositories to containerized Satellite servers.

## Usage

```
/patch-pr [--sat] <hostname1> [hostname2...] [--pr] <pr-spec1> [pr-spec2...] [--keep-old-patch]
```

**Arguments:**
- Hostnames: One or more Satellite hostnames (can be prefixed with `--sat` or provided directly)
  - Examples: `ip-10-0-221-233`, `ip-10-0-221-233.rhos-01.prod.psi.rdu2.redhat.com`
- PR specifications: One or more PRs in either format (can be prefixed with `--pr` or provided directly):
  - `repo:pr#` format: `foreman:11358`, `foreman_google:100`
  - GitHub URL format: `https://github.com/theforeman/foreman/pull/11358`
- `--keep-old-patch` (optional): Build on top of existing patched images instead of starting fresh (default: false)

**Examples:**
```
# Flag-based syntax (original)
/patch-pr --sat ip-10-0-221-233 --pr foreman:11358

# Positional syntax (new)
/patch-pr ip-10-0-221-233 https://github.com/theforeman/foreman/pull/11358

# Mixed syntax
/patch-pr ip-10-0-221-233 ip-10-0-221-234 foreman_google:100 hammer_cli_foreman_google:19

# GitHub URLs with multiple satellites
/patch-pr \
  ip-10-0-221-233.rhos-01.prod.psi.rdu2.redhat.com \
  ip-10-0-221-228.rhos-01.prod.psi.rdu2.redhat.com \
  https://github.com/theforeman/foreman/pull/11358 \
  https://github.com/theforeman/foreman/pull/11359 \
  --keep-old-patch

# All formats work together
/patch-pr --sat ip-10-0-221-233 --pr foreman:11358 https://github.com/theforeman/foreman_google/pull/100 --keep-old-patch
```

---

## Instructions

### Step 1: Parse Arguments

Parse all arguments into three categories:

**1. Identify argument types:**

For each argument:
- If it's `--keep-old-patch`: Set `keep_old_patch = true`
- If it's `--sat` or `--pr`: Skip (flag markers, next args are the values)
- If it matches `https://github.com/theforeman/*/pull/*`: Extract as PR URL
- If it matches `*:*` (contains colon): Parse as `repo:pr#`
- Otherwise: Treat as hostname

**2. Parse PR specifications:**

For GitHub URLs (`https://github.com/theforeman/{repo}/pull/{pr_number}`):
```python
# Extract repo and PR number from URL
# Example: https://github.com/theforeman/foreman/pull/11358
# → repo = "foreman", pr_number = 11358

import re
url_pattern = r'https://github\.com/theforeman/([^/]+)/pull/(\d+)'
match = re.match(url_pattern, url)
if match:
    repo = match.group(1)
    pr_number = int(match.group(2))
```

For `repo:pr#` format:
```python
# Example: foreman:11358 → repo = "foreman", pr_number = 11358
repo, pr_str = arg.split(':')
pr_number = int(pr_str)
```

**3. Extract final values:**
- `sat_hosts`: List of satellite hostnames
- `prs`: List of `(repo, pr_number)` tuples
- `keep_old_patch`: Boolean flag

**4. Validate:**
- At least one satellite hostname must be provided
- At least one PR specification must be provided
- All PR numbers must be valid integers
- All GitHub URLs must match theforeman organization

**Example parsing:**

Input:
```
ip-10-0-221-233.rhos-01.prod.psi.rdu2.redhat.com \
ip-10-0-221-228.rhos-01.prod.psi.rdu2.redhat.com \
https://github.com/theforeman/foreman/pull/11358 \
foreman_google:100 \
--keep-old-patch
```

Parsed:
```python
sat_hosts = [
    "ip-10-0-221-233.rhos-01.prod.psi.rdu2.redhat.com",
    "ip-10-0-221-228.rhos-01.prod.psi.rdu2.redhat.com"
]
prs = [
    ("foreman", 11358),
    ("foreman_google", 100)
]
keep_old_patch = True
```

### Step 2: Categorize PRs by Type

For each PR, determine the patch target:

**Foreman container patches** (patch inside container):
- `foreman` - core Foreman repository
- `foreman_google` - GCE compute resource plugin
- `foreman_azure_rm` - Azure compute resource plugin
- `foreman_openstack` - OpenStack compute resource plugin
- Any other `foreman_*` plugin

**Hammer host patches** (patch on host system):
- `hammer_cli_foreman` - Hammer CLI core
- `hammer_cli_foreman_google` - Hammer GCE plugin
- `hammer_cli_foreman_azure_rm` - Hammer Azure plugin
- Any other `hammer_cli_*` plugin

### Step 3: Fetch PR Files from GitHub

For each PR:

1. Construct GitHub API URL:
   ```
   https://api.github.com/repos/theforeman/{repo}/pulls/{pr_number}/files
   ```

2. Fetch changed files using `curl` or `gh api`:
   ```bash
   gh api repos/theforeman/{repo}/pulls/{pr_number}/files --jq '.[] | {filename: .filename, status: .status, patch: .patch}'
   ```

3. For each changed file, download the patched version:
   ```bash
   gh api repos/theforeman/{repo}/contents/{filepath}?ref=refs/pull/{pr_number}/head --jq '.content' | base64 -d > /tmp/{basename}
   ```

4. Store files in `/tmp/pr-patches/{repo}-{pr_number}/`

### Step 4: Build Containerfile for Foreman Patches

If there are Foreman patches, create a Containerfile:

**Base image selection:**
- If `--keep-old-patch`: Use the most recent custom image from the satellite
  ```bash
  ssh root@{hostname} "podman images --format '{{.Repository}}:{{.Tag}}' | grep '^localhost/foreman-pr' | head -1"
  ```
  If found, use that as FROM. Otherwise, fall back to `quay.io/foreman/foreman:nightly`.
  
- If NOT `--keep-old-patch`: Use `quay.io/foreman/foreman:nightly`

**Containerfile structure:**

```dockerfile
FROM {base_image}

USER 0

# Copy all patch files
{for each file}
COPY {filename} /tmp/pr{pr_number}/{filename}
{end for}

# Apply patches for each PR
{for each PR}
RUN set -e && \
    echo "Applying PR #{pr_number} ({description})..." && \
    {if foreman_google or similar plugin}
    for VERSION in $(find /usr/share/gems/gems/ -maxdepth 1 -type d -name '{gem_name}-*' | sort); do \
        echo "Patching $VERSION..." && \
        {for each file in PR}
        mkdir -p "$VERSION/{directory}" && \
        cp /tmp/pr{pr_number}/{filename} "$VERSION/{full_path}" && \
        {end for}
        {if model file needs sed changes}
        sed -i '{sed_pattern}' "$VERSION/{model_file}" && \
        {end if}
        echo "  ✓ Patched $VERSION"; \
    done && \
    {else if core foreman}
    {for each file in PR}
    mkdir -p /usr/share/foreman/{directory} && \
    cp /tmp/pr{pr_number}/{filename} /usr/share/foreman/{full_path} && \
    {end for}
    {end if}
    rm -rf /tmp/pr{pr_number} && \
    echo "✅ PR #{pr_number} applied successfully"
{end for}

USER foreman
```

**Image naming:**
```
localhost/foreman-pr{pr1}-pr{pr2}-...:latest
```

Example: `localhost/foreman-pr100-pr11358:latest`

**Build locally:**
```bash
cd /tmp/pr-patches
podman build -f Containerfile -t {image_name} .
```

### Step 5: Deploy to Satellite Servers

For each satellite hostname:

**5.1: Transfer custom image (if Foreman patches exist)**

```bash
# Save and compress
podman save {image_name} | gzip > /tmp/foreman-patched.tar.gz

# Copy to satellite
scp /tmp/foreman-patched.tar.gz root@{hostname}:/tmp/

# Load on satellite
ssh root@{hostname} "podman load < /tmp/foreman-patched.tar.gz"
```

**5.2: Apply Hammer patches (if any)**

For each Hammer PR:
```bash
# Copy patch files to satellite
scp /tmp/pr-patches/{repo}-{pr_number}/* root@{hostname}:/tmp/

# Apply on host
ssh root@{hostname} "
  for VERSION in /usr/share/gems/gems/{gem_name}-*; do
    echo \"Patching \$VERSION...\"
    {for each file}
    mkdir -p \$VERSION/{directory}
    cp /tmp/{filename} \$VERSION/{full_path}
    {end for}
    echo \"  ✓ Patched \$VERSION\"
  done
  rm -f /tmp/{files}
"
```

**5.3: Update Quadlet configuration (if Foreman image changed)**

```bash
ssh root@{hostname} "
cat > /etc/containers/systemd/foreman.image.d/90-user.conf << 'EOF'
[Image]
Image={image_name}

[Service]
Environment=REGISTRY_AUTH_FILE=/etc/registry-auth.json
EOF
"
```

**5.4: Restart Foreman service**

```bash
ssh root@{hostname} "
systemctl daemon-reload
systemctl stop foreman
podman rm -f foreman
systemctl start foreman
"
```

### Step 6: Verify Patches Applied

For each satellite:

**Foreman patches:**
```bash
ssh root@{hostname} "
podman exec foreman bash -c '
  {for each patched file}
  echo \"Checking {filepath}...\"
  cat {filepath} | head -20
  {end for}
'
"
```

**Hammer patches:**
```bash
ssh root@{hostname} "
  {for each patched file}
  echo \"Checking {filepath}...\"
  cat /usr/share/gems/gems/{gem_name}-*/{filepath} | head -20
  {end for}
"
```

### Step 7: Report Summary

Print a summary table:

```
✅ PR Patching Complete

PRs Applied:
  - theforeman/{repo}#{pr_number}: {pr_title}
  - theforeman/{repo}#{pr_number}: {pr_title}

Satellites Updated:
  - {hostname1}
  - {hostname2}

Container Image: {image_name}

Verification:
  ✓ Foreman patches verified in container
  ✓ Hammer patches verified on host
  ✓ Services restarted successfully
```

---

## Common Patterns

### Pattern 1: Foreman Core File Patch

For PRs to `theforeman/foreman` that change files in `app/`:

```dockerfile
RUN set -e && \
    echo "Applying PR #11358 (Flush SSH key to disk)..." && \
    cp /tmp/pr11358/ssh.rb /usr/share/foreman/app/services/foreman/provision/ssh.rb && \
    echo "  ✓ Patched ssh.rb" && \
    grep -A 2 "f.write" /usr/share/foreman/app/services/foreman/provision/ssh.rb && \
    echo "✅ PR #11358 patch applied successfully"
```

### Pattern 2: Foreman Plugin Patch (Multiple Gem Versions)

For PRs to `theforeman/foreman_google` or similar plugins:

```dockerfile
RUN set -e && \
    for VERSION in $(find /usr/share/gems/gems/ -maxdepth 1 -type d -name 'foreman_google-*' | sort); do \
        echo "Patching $VERSION..." && \
        mkdir -p "$VERSION/app/controllers/foreman_google/api/v2" && \
        cp /tmp/pr100/compute_resources_extensions.rb "$VERSION/app/controllers/foreman_google/api/v2/" && \
        # Model validation changes
        sed -i 's/validates :password, :zone, presence: true/validates :zone, presence: true/' \
          "$VERSION/app/models/foreman_google/gce.rb" && \
        echo "  ✓ Patched $VERSION"; \
    done
```

### Pattern 3: Hammer CLI Patch (Host Filesystem)

For PRs to `theforeman/hammer_cli_foreman_google`:

```bash
ssh root@{hostname} "
  for VERSION in /usr/share/gems/gems/hammer_cli_foreman_google-*; do
    echo \"Patching \$VERSION...\"
    cp /tmp/google.rb \$VERSION/lib/hammer_cli_foreman_google/compute_resources/google.rb
    echo \"  ✓ Patched \$VERSION\"
  done
"
```

---

## SSH Password Handling

When connecting to satellites, use the password stored in memory if available, otherwise prompt:

```bash
# Check if password in memory (from previous /gather-failures or similar)
# Otherwise use sshpass if needed:
sshpass -p "{password}" ssh root@{hostname} "command"

# Or use SSH keys if configured
```

---

## Error Handling

- If GitHub API fails: Report error and suggest using `gh auth login`
- If SSH connection fails: Report error and verify hostname/credentials
- If podman build fails: Show build logs and stop
- If service restart fails: Show systemd logs
- If verification fails: Show what files are missing and suggest manual check

---

## Notes

- Always work in `/tmp/pr-patches/` for temporary files
- Clean up `/tmp/pr-patches/` after successful deployment
- Save Containerfile for reference at `/tmp/pr-patches/Containerfile`
- If multiple PRs touch the same file, apply in order (later PRs override earlier ones)
- For `--keep-old-patch`, verify the base image exists before building
