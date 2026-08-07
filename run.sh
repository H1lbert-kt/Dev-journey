#!/bin/bash

# ============================================
# DevJourney - Run Script
# ============================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}    DevJourney - Study Tracker${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if Docker is available
if command -v docker &> /dev/null; then
    echo -e "${YELLOW}Docker detected. Running with Docker Compose...${NC}"
    
    # Check if docker-compose.yml exists
    if [ -f "docker-compose.yml" ]; then
        # Check if .env file exists, if not copy from .env.example
        if [ ! -f ".env" ]; then
            echo -e "${YELLOW}Creating .env file from .env.example...${NC}"
            cp .env.example .env
        fi
        
        echo -e "${GREEN}Starting services...${NC}"
        docker-compose up --build
    else
        echo -e "${RED}docker-compose.yml not found!${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}Docker not found. Running locally...${NC}"
    
    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}Creating virtual environment...${NC}"
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install dependencies
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install -r requirements.txt
    
    # Check if .env file exists
    if [ ! -f ".env" ]; then
        echo -e "${YELLOW}Creating .env file from .env.example...${NC}"
        cp .env.example .env
    fi
    
    # Run the application
    echo -e "${GREEN}Starting DevJourney...${NC}"
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
fi
