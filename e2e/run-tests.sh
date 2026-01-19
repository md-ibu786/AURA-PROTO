#!/bin/bash

# AURA-PROTO E2E Test Runner
# Usage: ./run-tests.sh [api|ui|audio|all|debug]

set -e

echo "=========================================="
echo "AURA-PROTO E2E Test Runner"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if backend is running
check_backend() {
    echo -e "${YELLOW}Checking backend...${NC}"
    if curl -s http://127.0.0.1:8001/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend is running${NC}"
        return 0
    else
        echo -e "${RED}✗ Backend is not running on port 8001${NC}"
        echo "Please start the backend: cd api && python -m uvicorn main:app --host 0.0.0.0 --port 8001"
        return 1
    fi
}

# Check if frontend is running
check_frontend() {
    echo -e "${YELLOW}Checking frontend...${NC}"
    if curl -s http://127.0.0.1:5173 > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Frontend is running${NC}"
        return 0
    else
        echo -e "${RED}✗ Frontend is not running on port 5173${NC}"
        echo "Please start the frontend: cd frontend && npm run dev"
        return 1
    fi
}

# Run tests
run_tests() {
    local test_type=$1

    echo -e "${YELLOW}Running tests: ${test_type}${NC}"
    echo ""

    case $test_type in
        "api")
            npx playwright test tests/api.spec.ts --reporter=html,list
            ;;
        "ui")
            npx playwright test tests/explorer.spec.ts --reporter=html,list
            ;;
        "audio")
            npx playwright test tests/audio.spec.ts --reporter=html,list
            ;;
        "all")
            npx playwright test --reporter=html,list
            ;;
        "debug")
            npx playwright test --debug
            ;;
        *)
            echo -e "${RED}Unknown test type: ${test_type}${NC}"
            echo "Usage: ./run-tests.sh [api|ui|audio|all|debug]"
            exit 1
            ;;
    esac
}

# Main execution
main() {
    local test_type=${1:-all}

    # Skip checks for debug mode
    if [ "$test_type" != "debug" ]; then
        echo "Step 1: Validating environment..."
        if ! check_backend; then
            echo -e "${RED}Please start backend before running tests${NC}"
            exit 1
        fi

        if [ "$test_type" != "api" ]; then
            if ! check_frontend; then
                echo -e "${RED}Please start frontend before running UI tests${NC}"
                exit 1
            fi
        fi
        echo ""
    fi

    echo "Step 2: Running tests..."
    run_tests "$test_type"

    local exit_code=$?

    echo ""
    echo "=========================================="
    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✓ All tests passed!${NC}"
        echo "View report: npm run show-report"
    else
        echo -e "${RED}✗ Some tests failed${NC}"
        echo "View report: npm run show-report"
    fi
    echo "=========================================="

    exit $exit_code
}

# Check if in e2e directory
if [ ! -f "package.json" ]; then
    echo -e "${RED}Error: Please run this script from the e2e directory${NC}"
    exit 1
fi

main "$@"
