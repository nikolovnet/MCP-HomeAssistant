# MCP Home Assistant Server

A Model Context Protocol (MCP) server that allows Large Language Models (LLMs) like Claude to control your Home Assistant devices and smart home setup.

## Features

- **Device Control**: Control lights, switches, climate devices, and more
- **Device Discovery**: Get lists of all devices or filter by type
- **State Monitoring**: Check current device states
- **Docker Containerized**: Runs in isolated Docker containers with auto-cleanup
- **Secure Configuration**: All credentials stored in environment variables
- **Clean Integration**: Optimized logging prevents error messages in Claude Desktop
- **On-Demand Architecture**: Containers spawn only when needed, auto-remove when done

## Prerequisites

- Docker and Docker Compose installed
- Home Assistant instance running (yours is at `192.168.200.111:8123`)
- Long-Lived Access Token from Home Assistant

## Setup

### 1. Get Home Assistant Access Token

1. Go to your Home Assistant instance: `http://192.168.200.111:8123`
2. Navigate to **Profile** (bottom left menu)
3. Scroll down to **Long-Lived Access Tokens**
4. Click **Create Token**
5. Give it a name like "MCP Server"
6. Copy the generated token

### 2. Configure Environment Variables

1. Copy the example environment file:
   ```bash
   cp env_example.txt .env
   ```

2. Edit the `.env` file and replace `your_long_lived_access_token_here` with your actual token:
   ```bash
   HOME_ASSISTANT_TOKEN=your_actual_token_here
   ```

3. Verify other settings:
   - `HOME_ASSISTANT_URL` should already be set to your instance
   - `VERIFY_SSL` should be `true` unless you're using self-signed certificates

### 3. Build the Docker Image

```bash
# Build the Docker image
docker-compose build

# Test the image (optional)
echo '{"jsonrpc": "2.0", "method": "initialize", "id": 1}' | docker run --rm -i --env-file .env mcp-homeassistant-mcp-homeassistant
```

**Note**: You don't need to run containers manually - Claude Desktop will manage them automatically!

## Available Tools

The MCP server provides the following tools that LLMs can use:

### Device Discovery
- **`get_all_devices`**: Get a list of all devices and their current states
- **`get_devices_by_type`**: Get devices of a specific type (light, switch, climate, etc.)
- **`get_device_state`**: Get the current state of a specific device

### Device Control
- **`control_light`**: Control lights (turn on/off, adjust brightness, color temperature)
- **`control_switch`**: Control switches (turn on/off/toggle)
- **`control_climate`**: Control climate devices (temperature, mode)

## Usage with Claude

To use this MCP server with Claude Desktop:

1. **Install Claude Desktop** from https://claude.ai/download

2. **Configure MCP** in Claude Desktop:
   - Open Claude Desktop settings
   - Go to the MCP section  
   - Add a new MCP server with these settings:
     ```json
     {
       "mcpServers": {
         "home-assistant": {
           "command": "docker",
           "args": [
             "run",
             "--rm", 
             "-i",
             "--stop-timeout=5",
             "--env-file",
             "/path/to/your/MCP-HomeAssistant/.env",
             "mcp-homeassistant-mcp-homeassistant"
           ]
         }
       }
     }
     ```
   - Replace `/path/to/your/MCP-HomeAssistant/.env` with the full path to your `.env` file

3. **Restart Claude Desktop**

4. **Test the integration** by asking Claude to control your devices:
   - "Turn on the living room lights"
   - "What's the current temperature in the bedroom?"
   - "List all my smart switches"

## Example Interactions

Here are some example conversations you can have with Claude:

```
User: Can you turn on the living room lights?
Claude: I'll help you turn on the living room lights. Let me check what lights are available first.

[Claude uses the get_devices_by_type tool to find lights]
[Claude uses the control_light tool to turn on the lights]

The living room lights have been turned on successfully!
```

```
User: What's the temperature in my house?
Claude: Let me check your climate devices to see the current temperatures.

[Claude uses the get_devices_by_type tool to find climate devices]

Based on your climate devices, here's the current status:
- Living Room: 72°F
- Bedroom: 70°F
- Kitchen: 74°F
```

## Troubleshooting

### Connection Issues
- Verify your Home Assistant URL is correct: `http://192.168.200.111:8123`
- Check that your access token is valid and not expired
- Ensure your Docker container can reach your Home Assistant instance

### SSL Issues
If you're using self-signed certificates, set `VERIFY_SSL=false` in your `.env` file.

### Docker Issues
- Make sure Docker is running: `docker --version`
- Test the image manually: `docker run --rm -i --env-file .env mcp-homeassistant-mcp-homeassistant`
- Rebuild if needed: `docker-compose build --no-cache`

### MCP Integration Issues
- Verify the path to your `.env` file in the Claude Desktop configuration
- Restart Claude Desktop after configuration changes
- Check Docker Desktop for running containers (multiple containers during use is normal)

### Multiple Container Issue
If you see many containers running:
- This is **normal behavior** - Claude Desktop spawns containers on-demand
- Containers auto-remove when conversations end (thanks to `--rm` flag)
- Use the cleanup script if needed: `./cleanup-containers.sh`

### JSON-RPC Errors
If you see error messages in Claude Desktop:
- Make sure you're using the latest version of the Docker image
- The logging has been optimized to prevent stdout interference
- Restart Claude Desktop to clear any cached issues

## Security Notes

- Your `.env` file contains sensitive credentials - keep it secure
- The MCP server only has access to the Home Assistant API token you provide
- Consider restricting the token's permissions in Home Assistant if possible
- Never commit the `.env` file to version control

## Container Management

### Normal Operation
- **Multiple containers during use is expected** - Claude Desktop spawns containers on-demand
- **Containers auto-cleanup** when conversations end (via `--rm` flag)
- **No manual management needed** - the system handles container lifecycle

### Manual Cleanup (if needed)
```bash
# Stop all MCP containers
./cleanup-containers.sh

# Or manually:
docker stop $(docker ps -q --filter "ancestor=mcp-homeassistant-mcp-homeassistant")
docker container prune -f
```

### Viewing Logs
```bash
# View logs from running containers
docker logs <container-name>

# Or check the log file inside container
docker exec <container-name> cat /app/mcp_server.log
```

## Development

To modify the MCP server:

1. Edit `mcp_server.py`
2. Rebuild the container: `docker-compose build`
3. Test: `docker run --rm -i --env-file .env mcp-homeassistant-mcp-homeassistant`
4. Restart Claude Desktop to use the new image

## License

This project is open source. Feel free to modify and distribute.
