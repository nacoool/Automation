#!/bin/bash

# Usage: ./ssh2machine.sh <remote_host> <remote_user> <remote_pass> <remote_dir>
REMOTE_HOST="$1"
REMOTE_USER="$2"
REMOTE_PASS="$3"
REMOTE_DIR="$4"

LOCAL_FILES=("Verify_CodeBase.py" "validations.yaml")

#check if sshpass is installed
if ! command -v sshpass &> /dev/null; then
    echo "sshpass could not be found"
    echo "Installing sshpass..."
    sudo yum install -y sshpass
fi

echo " Connecting to $REMOTE_HOST..."

# Create remote directory
sshpass -p "$REMOTE_PASS" ssh -o StrictHostKeyChecking=no ${REMOTE_USER}@${REMOTE_HOST} "mkdir -p ${REMOTE_DIR}"

# Copy files
echo "  Copying files..."
for file in "${LOCAL_FILES[@]}"; do
    if [[ -f "$file" ]]; then
        sshpass -p "$REMOTE_PASS" scp -o StrictHostKeyChecking=no "$file" ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/
        echo "  Copied $file"
    else
        echo "  File $file not found locally"
        exit 1
    fi
done

# Run the script
echo "  Validating codebase with expected changes on hostname: $REMOTE_HOST..."
sshpass -p "$REMOTE_PASS" ssh -o StrictHostKeyChecking=no ${REMOTE_USER}@${REMOTE_HOST} "cd ${REMOTE_DIR} && python3 Verify_CodeBase.py"

# Cleanup
echo "  Cleaning up..."
sshpass -p "$REMOTE_PASS" ssh -o StrictHostKeyChecking=no ${REMOTE_USER}@${REMOTE_HOST} "rm -rf ${REMOTE_DIR}"

echo "  Script execution completed successfully!"
