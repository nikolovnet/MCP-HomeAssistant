# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the MCP server code
COPY mcp_server.py .

# Copy environment file (will be mounted as volume)
# Note: .env file should be mounted as volume when running container

# Expose port if needed (MCP servers typically communicate via stdio)
# EXPOSE 8000

# Set environment variable to load .env file
ENV PYTHONUNBUFFERED=1

# Run the MCP server
CMD ["python", "mcp_server.py"]
