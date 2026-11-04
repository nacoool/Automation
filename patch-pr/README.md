# Patch PR Skill

Automates applying GitHub PRs from Foreman/Hammer repositories to containerized Satellite servers.

## Quick Start

```bash
# Simple positional syntax (recommended)
/patch-pr ip-10-0-221-233 https://github.com/theforeman/foreman/pull/11358

# Or with flags
/patch-pr --sat ip-10-0-221-233 --pr foreman:11358
```

This will:
1. Fetch PR #11358 from theforeman/foreman
2. Build a custom container image with the patch
3. Deploy to ip-10-0-221-233
4. Verify the patch was applied

## Examples

### Single PR, Single Satellite

Positional syntax (GitHub URL):
```bash
/patch-pr ip-10-0-221-233 https://github.com/theforeman/foreman/pull/11358
```

Short format:
```bash
/patch-pr ip-10-0-221-233 foreman:11358
```

Flag-based syntax:
```bash
/patch-pr --sat ip-10-0-221-233 --pr foreman:11358
```

### Multiple PRs, Multiple Satellites

Using GitHub URLs (clearest):
```bash
/patch-pr \
  ip-10-0-221-233.rhos-01.prod.psi.rdu2.redhat.com \
  ip-10-0-221-228.rhos-01.prod.psi.rdu2.redhat.com \
  https://github.com/theforeman/foreman/pull/11358 \
  https://github.com/theforeman/foreman/pull/11359 \
  --keep-old-patch
```

Using short format:
```bash
/patch-pr \
  ip-10-0-221-233 ip-10-0-221-234 \
  foreman_google:100 hammer_cli_foreman_google:19 hammer_cli_foreman_google:20
```

Mixed syntax (all formats work together):
```bash
/patch-pr \
  --sat ip-10-0-221-233 \
  foreman:11358 \
  https://github.com/theforeman/foreman_google/pull/100 \
  --keep-old-patch
```

### Build on Top of Existing Patches
```bash
# First apply PR #100
/patch-pr ip-10-0-221-233 foreman_google:100

# Later, add PR #11358 on top (keeps PR #100)
/patch-pr ip-10-0-221-233 foreman:11358 --keep-old-patch
```

## Argument Formats

The skill supports flexible argument parsing - you can use flags or positional arguments:

### PR Specifications (3 formats)

1. **GitHub URL** (recommended for clarity):
   ```
   https://github.com/theforeman/foreman/pull/11358
   ```

2. **Short format** (repo:pr#):
   ```
   foreman:11358
   foreman_google:100
   ```

3. **Flag-based**:
   ```
   --pr foreman:11358
   --pr https://github.com/theforeman/foreman/pull/11358
   ```

### Satellite Hostnames (2 formats)

1. **Positional** (recommended):
   ```
   ip-10-0-221-233
   ip-10-0-221-233.rhos-01.prod.psi.rdu2.redhat.com
   ```

2. **Flag-based**:
   ```
   --sat ip-10-0-221-233
   ```

### Parsing Logic

The skill automatically detects argument types:
- Contains `github.com/theforeman/*/pull/*` → GitHub PR URL
- Contains `:` but not `.` → Short format (repo:pr#)
- Contains `.` or starts with `ip-` → Hostname
- `--keep-old-patch` → Flag

All formats can be mixed in a single command!

## Supported Repositories

### Foreman (Container Patches)
- `foreman` - Core Foreman
- `foreman_google` - GCE compute resource
- `foreman_azure_rm` - Azure compute resource
- `foreman_openstack` - OpenStack compute resource
- Any `foreman_*` plugin

### Hammer (Host Patches)
- `hammer_cli_foreman` - Hammer CLI core
- `hammer_cli_foreman_google` - Hammer GCE plugin
- `hammer_cli_foreman_azure_rm` - Hammer Azure plugin
- Any `hammer_cli_*` plugin

## How It Works

1. **Fetch PR files** from GitHub using `gh` CLI
2. **Categorize patches** (Foreman container vs Hammer host)
3. **Build custom image** with Foreman patches baked in
4. **Deploy** image to each satellite
5. **Apply Hammer patches** directly on host filesystem
6. **Restart services** (systemctl + podman)
7. **Verify** patches by reading patched files

## Prerequisites

- `gh` CLI installed and authenticated (`gh auth login`)
- SSH access to satellite servers (root)
- `podman` on local machine (for building images)
- `scp` and `ssh` tools

## Image Naming Convention

Images are named based on applied PRs:
- Single PR: `localhost/foreman-pr11358:latest`
- Multiple PRs: `localhost/foreman-pr100-pr11358:latest`

When using `--keep-old-patch`, the new image builds on top of the previous custom image.

## Common Use Cases

### Test a Product Bug Fix
```bash
# PR #11358 fixes SSH key flushing issue
/patch-pr --sat ip-10-0-221-233 --pr foreman:11358
```

### Test a New Feature
```bash
# PR #100 adds key_content support for GCE
/patch-pr --sat ip-10-0-221-233 --pr foreman_google:100
```

### Stack Multiple Patches
```bash
# First patch
/patch-pr --sat ip-10-0-221-233 --pr foreman_google:100

# Add another on top
/patch-pr --sat ip-10-0-221-233 --pr foreman:11358 --keep-old-patch
```

### Patch Multiple Satellites for Testing
```bash
# Patch entire test farm
/patch-pr \
  --sat sat1.example.com sat2.example.com sat3.example.com \
  --pr foreman:11358
```

## Troubleshooting

### GitHub API Rate Limit
```bash
gh auth status
gh auth login
```

### SSH Connection Issues
Check that you can SSH to the satellite:
```bash
ssh root@ip-10-0-221-233 hostname
```

### Podman Build Failures
The skill saves the Containerfile to `/tmp/pr-patches/Containerfile` - you can debug locally:
```bash
cd /tmp/pr-patches
podman build -f Containerfile -t test .
```

### Service Won't Start
Check systemd logs on the satellite:
```bash
ssh root@ip-10-0-221-233 "journalctl -u foreman -n 50"
```

## Files Created

- `/tmp/pr-patches/` - Temporary directory for PR files and Containerfile
- `/tmp/pr-patches/{repo}-{pr}/` - Individual PR patch files
- `/tmp/pr-patches/Containerfile` - Generated Containerfile
- `/tmp/foreman-patched.tar.gz` - Compressed image for transfer

## Architecture

```
┌─────────────────┐
│  GitHub PR      │
│  theforeman/*   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Fetch PR Files  │
│ (gh CLI)        │
└────────┬────────┘
         │
         ▼
    ┌────┴────┐
    │         │
    ▼         ▼
┌──────┐  ┌──────┐
│Foreman│  │Hammer│
│Patch  │  │Patch │
└───┬───┘  └───┬──┘
    │          │
    ▼          │
┌──────────┐   │
│Build Image│   │
│(podman)   │   │
└─────┬─────┘   │
      │         │
      ▼         ▼
  ┌────────────────┐
  │ Deploy to Sats │
  │ (ssh/scp)      │
  └────────┬───────┘
           │
           ▼
    ┌──────────────┐
    │Restart Service│
    │(systemctl)   │
    └──────┬───────┘
           │
           ▼
    ┌─────────────┐
    │   Verify    │
    └─────────────┘
```
