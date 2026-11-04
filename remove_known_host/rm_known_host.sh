#!/bin/bash

if [ $# -ne 1 ]; then
    echo "Usage: $0 <fqdn>"
    exit 1
fi

if [ -z "$1" ]; then
    echo "Usage: $0 <fqdn | 167-116>"
    exit 1
fi

INPUT="$1"
BASE_DOMAIN="rhos-01.prod.psi.rdu2.redhat.com"

if [[ "$INPUT" == *.* ]]; then
    FQDN="$INPUT"
else
    FQDN="ip-10-0-${INPUT}.${BASE_DOMAIN}"
fi
echo "Final FQDN: $FQDN"

KNOWN_HOSTS="/home/napathak/.ssh/known_hosts"

# Exit if file does not exist
if [ ! -f "$KNOWN_HOSTS" ]; then
    echo "Error: $KNOWN_HOSTS does not exist. Nothing to remove."
    exit 1
fi

# Check if host exists in file (handles hashed entries too)
if ! ssh-keygen -F "$FQDN" -f "$KNOWN_HOSTS" >/dev/null; then
    echo "Host $FQDN not found in $KNOWN_HOSTS"
    exit 0
fi

# Create backup
BACKUP_FILE="${KNOWN_HOSTS}.bak_$(date +%Y%m%d_%H%M%S)"
cp "$KNOWN_HOSTS" "$BACKUP_FILE" || {
    echo "Backup failed. Aborting."
    exit 1
}

echo "Backup created: $BACKUP_FILE"

# Remove entry
ssh-keygen -R "$FQDN" -f "$KNOWN_HOSTS" >/dev/null

echo "Entries for $FQDN removed successfully."

