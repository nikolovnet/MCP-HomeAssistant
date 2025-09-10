#!/bin/bash
# Cleanup script for MCP Home Assistant containers

echo "Stopping MCP Home Assistant containers..."
docker stop $(docker ps -q --filter "ancestor=mcp-homeassistant-mcp-homeassistant") 2>/dev/null || echo "No containers to stop"

echo "Removing stopped containers..."
docker container prune -f

echo "Cleanup complete!"
