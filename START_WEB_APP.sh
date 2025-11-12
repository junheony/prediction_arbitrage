#!/bin/bash

# 🚀 Prediction Arbitrage Web App Startup Script

echo "🎉 Starting Prediction Arbitrage Web Application..."
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from .env.production...${NC}"
    cp .env.production .env
    echo -e "${RED}❗ Please edit .env file with your API credentials before continuing!${NC}"
    echo ""
    echo "Required credentials:"
    echo "  - SECRET_KEY (generate with: openssl rand -hex 32)"
    echo "  - KALSHI_EMAIL and KALSHI_PASSWORD"
    echo ""
    read -p "Press Enter after editing .env file..."
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed. Please install Docker Compose first.${NC}"
    exit 1
fi

echo -e "${BLUE}🐳 Building Docker containers...${NC}"
docker-compose -f docker-compose.web.yml build

echo ""
echo -e "${BLUE}🚀 Starting services...${NC}"
docker-compose -f docker-compose.web.yml up -d

echo ""
echo -e "${GREEN}✅ Web application started successfully!${NC}"
echo ""
echo "Access the application at:"
echo -e "  ${BLUE}Frontend:${NC} http://localhost:3000"
echo -e "  ${BLUE}Backend API:${NC} http://localhost:8000"
echo -e "  ${BLUE}API Docs:${NC} http://localhost:8000/docs"
echo ""
echo "To view logs:"
echo "  docker-compose -f docker-compose.web.yml logs -f"
echo ""
echo "To stop the application:"
echo "  docker-compose -f docker-compose.web.yml down"
echo ""
echo -e "${GREEN}Happy Trading! 🚀📈💰${NC}"
