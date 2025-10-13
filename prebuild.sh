#!/bin/bash
# Azure App Service prebuild script to fix typing_extensions
echo "Running prebuild script to fix typing_extensions..."

# Find the correct typing_extensions in virtual environment
VENV_TE=$(find /tmp -path "*/antenv/lib/python*/site-packages/typing_extensions.py" 2>/dev/null | head -1)

if [ -f "$VENV_TE" ]; then
    echo "Found correct typing_extensions at: $VENV_TE"
    
    # Backup the bad one if it exists
    if [ -f "/agents/python/typing_extensions.py" ]; then
        mv /agents/python/typing_extensions.py /agents/python/typing_extensions.py.bak 2>/dev/null || true
        echo "Backed up old typing_extensions"
    fi
    
    # Copy the good one to override
    cp "$VENV_TE" /agents/python/typing_extensions.py 2>/dev/null || true
    echo "Replaced with correct version"
else
    echo "Could not find virtual environment typing_extensions"
fi

echo "Prebuild script completed"