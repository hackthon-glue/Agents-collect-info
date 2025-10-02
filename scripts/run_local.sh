#!/bin/bash
# Local execution script for Strands Data Pipeline Agent

set -e

echo "Starting Strands Data Pipeline Agent (Local Mode)..."

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Run agent in interactive mode
cd src
python agent.py --interactive
