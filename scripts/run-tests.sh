#!/bin/bash
# ===========================================
# IOSP - Test Runner Script
# ===========================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}IOSP Test Runner${NC}"
echo -e "${GREEN}============================================${NC}"

# Default values
COVERAGE_MIN=60
PARALLEL=false
MARKERS=""
VERBOSE="-v"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --parallel|-p)
            PARALLEL=true
            shift
            ;;
        --unit)
            MARKERS="-m unit"
            shift
            ;;
        --integration)
            MARKERS="-m integration"
            shift
            ;;
        --fast)
            MARKERS="-m 'not slow'"
            shift
            ;;
        --no-cov)
            NO_COV=true
            shift
            ;;
        --quiet|-q)
            VERBOSE=""
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --parallel, -p    Run tests in parallel"
            echo "  --unit            Run only unit tests"
            echo "  --integration     Run only integration tests"
            echo "  --fast            Skip slow tests"
            echo "  --no-cov          Disable coverage reporting"
            echo "  --quiet, -q       Less verbose output"
            echo "  --help, -h        Show this help"
            exit 0
            ;;
        *)
            # Pass unknown args to pytest
            EXTRA_ARGS="$EXTRA_ARGS $1"
            shift
            ;;
    esac
done

# Build pytest command
CMD="python -m pytest"

# Add verbose flag
if [ -n "$VERBOSE" ]; then
    CMD="$CMD $VERBOSE"
fi

# Add parallel execution
if [ "$PARALLEL" = true ]; then
    CMD="$CMD -n auto"
fi

# Add markers
if [ -n "$MARKERS" ]; then
    CMD="$CMD $MARKERS"
fi

# Add coverage (unless disabled)
if [ "$NO_COV" != true ]; then
    CMD="$CMD --cov=apps --cov-report=term-missing --cov-report=html:htmlcov --cov-fail-under=$COVERAGE_MIN"
fi

# Add extra args
if [ -n "$EXTRA_ARGS" ]; then
    CMD="$CMD $EXTRA_ARGS"
fi

echo -e "${YELLOW}Running: $CMD${NC}"
echo ""

# Run tests
$CMD

# Check result
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}All tests passed!${NC}"
    echo -e "${GREEN}============================================${NC}"

    if [ "$NO_COV" != true ]; then
        echo -e "${YELLOW}Coverage report: htmlcov/index.html${NC}"
    fi
else
    echo ""
    echo -e "${RED}============================================${NC}"
    echo -e "${RED}Tests failed!${NC}"
    echo -e "${RED}============================================${NC}"
    exit 1
fi
