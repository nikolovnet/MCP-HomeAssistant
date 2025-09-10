#!/usr/bin/env python3
"""
MCP Server for Home Assistant Integration
Allows LLMs like Claude to control Home Assistant devices through the Model Context Protocol.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional

import aiohttp
from mcp import Tool
from mcp.server import Server
from mcp.types import TextContent, PromptMessage
import mcp.server.stdio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr),  # Use stderr instead of stdout
        logging.FileHandler('/app/mcp_server.log')
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
HOME_ASSISTANT_URL = os.getenv("HOME_ASSISTANT_URL", "http://192.168.200.111:8123")
HOME_ASSISTANT_TOKEN = os.getenv("HOME_ASSISTANT_TOKEN")
VERIFY_SSL = os.getenv("VERIFY_SSL", "true").lower() == "true"

logger.debug("MCP Server starting...")
logger.debug(f"Home Assistant URL: {HOME_ASSISTANT_URL}")
logger.debug(f"SSL Verification: {VERIFY_SSL}")
logger.debug(f"Token configured: {'Yes' if HOME_ASSISTANT_TOKEN else 'No'}")

class HomeAssistantMCP:
    def __init__(self):
        logger.debug("Initializing Home Assistant MCP client")
        self.session: Optional[aiohttp.ClientSession] = None
        self.headers = {
            "Authorization": f"Bearer {HOME_ASSISTANT_TOKEN}",
            "Content-Type": "application/json",
        }

    async def __aenter__(self):
        logger.debug("Creating HTTP session for Home Assistant API")
        self.session = aiohttp.ClientSession(headers=self.headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        logger.debug("Closing HTTP session")
        if self.session:
            await self.session.close()

    async def call_ha_api(self, endpoint: str, method: str = "GET", data: Optional[Dict] = None) -> Dict:
        """Call Home Assistant API endpoint"""
        url = f"{HOME_ASSISTANT_URL}/api/{endpoint}"

        logger.debug(f"Making {method} request to: {url}")
        if data:
            logger.debug(f"Request data: {json.dumps(data, indent=2)}")

        try:
            if method == "GET":
                async with self.session.get(url, verify_ssl=VERIFY_SSL) as response:
                    logger.debug(f"GET {endpoint} - Status: {response.status}")
                    result = await response.json()
                    if isinstance(result, list):
                        logger.debug(f"GET {endpoint} - Returned {len(result)} items")
                    else:
                        logger.debug(f"GET {endpoint} - Response: {result}")
                    return result
            elif method == "POST":
                async with self.session.post(url, json=data, verify_ssl=VERIFY_SSL) as response:
                    logger.debug(f"POST {endpoint} - Status: {response.status}")
                    result = await response.json()
                    logger.debug(f"POST {endpoint} - Response: {result}")
                    return result
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                raise ValueError(f"Unsupported HTTP method: {method}")
        except aiohttp.ClientError as e:
            logger.error(f"HTTP client error calling {endpoint}: {str(e)}")
            return {"error": f"HTTP client error: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error calling {endpoint}: {str(e)}")
            return {"error": str(e)}

    async def get_states(self) -> List[Dict]:
        """Get all entity states from Home Assistant"""
        logger.debug("Fetching all device states from Home Assistant")
        result = await self.call_ha_api("states")
        if isinstance(result, list):
            logger.debug(f"Retrieved {len(result)} device states")
            return result
        logger.warning(f"Unexpected response format for states: {type(result)}")
        return []

    async def get_state(self, entity_id: str) -> Dict:
        """Get state of a specific entity"""
        logger.debug(f"Fetching state for entity: {entity_id}")
        return await self.call_ha_api(f"states/{entity_id}")

    async def call_service(self, domain: str, service: str, data: Dict) -> Dict:
        """Call a Home Assistant service"""
        logger.info(f"Calling service {domain}.{service} for {data.get('entity_id', 'unknown')}")
        return await self.call_ha_api(f"services/{domain}/{service}", method="POST", data=data)

    async def get_devices_by_type(self, device_type: str) -> List[Dict]:
        """Get devices of a specific type (light, switch, etc.)"""
        logger.debug(f"Getting devices of type: {device_type}")
        states = await self.get_states()
        filtered_devices = [state for state in states if state.get("entity_id", "").startswith(f"{device_type}.")]
        logger.debug(f"Found {len(filtered_devices)} {device_type} devices")
        return filtered_devices

# MCP Server instance
server = Server("home-assistant-mcp")
ha_client = HomeAssistantMCP()

@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available tools for controlling Home Assistant"""
    logger.debug("Listing available MCP tools")
    tools = [
        Tool(
            name="get_all_devices",
            description="Get a list of all devices and their current states",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_devices_by_type",
            description="Get devices of a specific type (light, switch, climate, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "device_type": {
                        "type": "string",
                        "description": "Type of device (e.g., 'light', 'switch', 'climate')"
                    }
                },
                "required": ["device_type"]
            }
        ),
        Tool(
            name="get_device_state",
            description="Get the current state of a specific device",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "Entity ID of the device (e.g., 'light.living_room')"
                    }
                },
                "required": ["entity_id"]
            }
        ),
        Tool(
            name="control_light",
            description="Control a light device (turn on/off, adjust brightness, color)",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "Entity ID of the light"
                    },
                    "action": {
                        "type": "string",
                        "enum": ["turn_on", "turn_off", "toggle"],
                        "description": "Action to perform"
                    },
                    "brightness": {
                        "type": "number",
                        "description": "Brightness level (0-255), optional",
                        "minimum": 0,
                        "maximum": 255
                    },
                    "color_temp": {
                        "type": "number",
                        "description": "Color temperature in Kelvin, optional",
                        "minimum": 150,
                        "maximum": 500
                    }
                },
                "required": ["entity_id", "action"]
            }
        ),
        Tool(
            name="control_switch",
            description="Control a switch device (turn on/off/toggle)",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "Entity ID of the switch"
                    },
                    "action": {
                        "type": "string",
                        "enum": ["turn_on", "turn_off", "toggle"],
                        "description": "Action to perform"
                    }
                },
                "required": ["entity_id", "action"]
            }
        ),
        Tool(
            name="control_climate",
            description="Control climate devices (temperature, mode)",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "Entity ID of the climate device"
                    },
                    "action": {
                        "type": "string",
                        "enum": ["set_temperature", "set_mode"],
                        "description": "Action to perform"
                    },
                    "temperature": {
                        "type": "number",
                        "description": "Target temperature (required for set_temperature)"
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["heat", "cool", "auto", "off"],
                        "description": "Climate mode (required for set_mode)"
                    }
                },
                "required": ["entity_id", "action"]
            }
        )
    ]
    logger.debug(f"Listed {len(tools)} MCP tools")
    return tools

@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls from the LLM"""
    logger.info(f"Tool called: {name}")

    async with ha_client:
        try:
            if name == "get_all_devices":
                logger.debug("Executing get_all_devices tool")
                states = await ha_client.get_states()
                devices = []
                for state in states:
                    devices.append({
                        "entity_id": state.get("entity_id"),
                        "state": state.get("state"),
                        "attributes": state.get("attributes", {})
                    })

                logger.debug(f"get_all_devices tool completed - found {len(devices)} devices")
                return [TextContent(
                    type="text",
                    text=f"Found {len(devices)} devices:\n" + json.dumps(devices, indent=2)
                )]

            elif name == "get_devices_by_type":
                device_type = arguments.get("device_type")
                logger.debug(f"Executing get_devices_by_type tool for device type: {device_type}")
                if not device_type:
                    logger.warning("get_devices_by_type tool called without device_type parameter")
                    return [TextContent(type="text", text="Error: device_type is required")]

                devices = await ha_client.get_devices_by_type(device_type)
                device_list = []
                for device in devices:
                    device_list.append({
                        "entity_id": device.get("entity_id"),
                        "state": device.get("state"),
                        "attributes": device.get("attributes", {})
                    })

                logger.debug(f"get_devices_by_type tool completed - found {len(device_list)} {device_type} devices")
                return [TextContent(
                    type="text",
                    text=f"Found {len(device_list)} {device_type} devices:\n" + json.dumps(device_list, indent=2)
                )]

            elif name == "get_device_state":
                entity_id = arguments.get("entity_id")
                logger.debug(f"Executing get_device_state tool for entity: {entity_id}")
                if not entity_id:
                    logger.warning("get_device_state tool called without entity_id parameter")
                    return [TextContent(type="text", text="Error: entity_id is required")]

                state = await ha_client.get_state(entity_id)
                logger.debug(f"get_device_state tool completed for {entity_id}")
                return [TextContent(
                    type="text",
                    text=f"Device {entity_id} state:\n" + json.dumps(state, indent=2)
                )]

            elif name == "control_light":
                entity_id = arguments.get("entity_id")
                action = arguments.get("action")
                logger.debug(f"Executing control_light tool - entity: {entity_id}, action: {action}")

                if not entity_id or not action:
                    logger.warning("control_light tool called without required parameters")
                    return [TextContent(type="text", text="Error: entity_id and action are required")]

                data = {"entity_id": entity_id}

                if action == "turn_on":
                    logger.debug(f"Turning on light {entity_id}")
                    if "brightness" in arguments:
                        data["brightness"] = arguments["brightness"]
                        logger.debug(f"Setting brightness to {arguments['brightness']}")
                    if "color_temp" in arguments:
                        data["color_temp"] = arguments["color_temp"]
                        logger.debug(f"Setting color temperature to {arguments['color_temp']}")
                    result = await ha_client.call_service("light", "turn_on", data)
                elif action == "turn_off":
                    logger.debug(f"Turning off light {entity_id}")
                    result = await ha_client.call_service("light", "turn_off", data)
                elif action == "toggle":
                    logger.debug(f"Toggling light {entity_id}")
                    result = await ha_client.call_service("light", "toggle", data)
                else:
                    logger.warning(f"Invalid action for control_light: {action}")
                    return [TextContent(type="text", text=f"Error: Invalid action '{action}'")]

                logger.debug(f"control_light tool completed - {entity_id} {action}")
                return [TextContent(
                    type="text",
                    text=f"Light {entity_id} {action} result:\n" + json.dumps(result, indent=2)
                )]

            elif name == "control_switch":
                entity_id = arguments.get("entity_id")
                action = arguments.get("action")
                logger.debug(f"Executing control_switch tool - entity: {entity_id}, action: {action}")

                if not entity_id or not action:
                    logger.warning("control_switch tool called without required parameters")
                    return [TextContent(type="text", text="Error: entity_id and action are required")]

                data = {"entity_id": entity_id}

                if action == "turn_on":
                    logger.debug(f"Turning on switch {entity_id}")
                    result = await ha_client.call_service("switch", "turn_on", data)
                elif action == "turn_off":
                    logger.debug(f"Turning off switch {entity_id}")
                    result = await ha_client.call_service("switch", "turn_off", data)
                elif action == "toggle":
                    logger.debug(f"Toggling switch {entity_id}")
                    result = await ha_client.call_service("switch", "toggle", data)
                else:
                    logger.warning(f"Invalid action for control_switch: {action}")
                    return [TextContent(type="text", text=f"Error: Invalid action '{action}'")]

                logger.debug(f"control_switch tool completed - {entity_id} {action}")
                return [TextContent(
                    type="text",
                    text=f"Switch {entity_id} {action} result:\n" + json.dumps(result, indent=2)
                )]

            elif name == "control_climate":
                entity_id = arguments.get("entity_id")
                action = arguments.get("action")
                logger.debug(f"Executing control_climate tool - entity: {entity_id}, action: {action}")

                if not entity_id or not action:
                    logger.warning("control_climate tool called without required parameters")
                    return [TextContent(type="text", text="Error: entity_id and action are required")]

                data = {"entity_id": entity_id}

                if action == "set_temperature":
                    if "temperature" not in arguments:
                        logger.warning("set_temperature called without temperature parameter")
                        return [TextContent(type="text", text="Error: temperature is required for set_temperature")]
                    data["temperature"] = arguments["temperature"]
                    logger.debug(f"Setting temperature to {arguments['temperature']} for {entity_id}")
                    result = await ha_client.call_service("climate", "set_temperature", data)
                elif action == "set_mode":
                    if "mode" not in arguments:
                        logger.warning("set_mode called without mode parameter")
                        return [TextContent(type="text", text="Error: mode is required for set_mode")]
                    data["hvac_mode"] = arguments["mode"]
                    logger.debug(f"Setting mode to {arguments['mode']} for {entity_id}")
                    result = await ha_client.call_service("climate", "set_hvac_mode", data)
                else:
                    logger.warning(f"Invalid action for control_climate: {action}")
                    return [TextContent(type="text", text=f"Error: Invalid action '{action}'")]

                logger.debug(f"control_climate tool completed - {entity_id} {action}")
                return [TextContent(
                    type="text",
                    text=f"Climate {entity_id} {action} result:\n" + json.dumps(result, indent=2)
                )]

            else:
                logger.warning(f"Unknown tool called: {name}")
                return [TextContent(type="text", text=f"Error: Unknown tool '{name}'")]

        except Exception as e:
            logger.error(f"Unexpected error in call_tool: {str(e)}", exc_info=True)
            return [TextContent(type="text", text=f"Error: {str(e)}")]

async def main():
    """Main entry point"""
    logger.debug("Starting MCP server main function")

    if not HOME_ASSISTANT_TOKEN:
        logger.error("HOME_ASSISTANT_TOKEN environment variable is required but not set")
        print("Error: HOME_ASSISTANT_TOKEN environment variable is required", file=sys.stderr)
        sys.exit(1)

    logger.debug("Starting MCP stdio server")
    try:
        # Run the MCP server
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            logger.debug("MCP server initialized successfully")
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )
    except KeyboardInterrupt:
        logger.debug("MCP server stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"MCP server failed to start: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(main())
