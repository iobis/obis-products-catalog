#!/bin/bash

# CKAN Load Test Script
# Tests catalog performance under concurrent load

# Configuration
CKAN_URL="http://134.199.199.216"  # Change this to your droplet IP
TEST_ENDPOINT="/dataset"           # The page to test

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "CKAN Load Test"
echo "=========================================="
echo ""
echo "Testing: $CKAN_URL$TEST_ENDPOINT"
echo ""

# Check if Apache Bench is installed
if ! command -v ab &> /dev/null; then
    echo -e "${RED}ERROR: Apache Bench (ab) is not installed.${NC}"
    echo ""
    echo "Install it with:"
    echo "  Ubuntu/Debian: sudo apt-get install apache2-utils"
    echo "  Mac: brew install httpd"
    echo "  Or use the Docker version below"
    exit 1
fi

# Test 1: Baseline (10 requests, 1 at a time)
echo -e "${YELLOW}Test 1: Baseline (10 requests, 1 concurrent)${NC}"
echo "--------------------------------------------"
ab -n 10 -c 1 -q "$CKAN_URL$TEST_ENDPOINT" | grep -E "Requests per second|Time per request|Failed requests"
echo ""

# Test 2: Light load (50 requests, 10 concurrent)
echo -e "${YELLOW}Test 2: Light Load (50 requests, 10 concurrent)${NC}"
echo "--------------------------------------------"
ab -n 50 -c 10 -q "$CKAN_URL$TEST_ENDPOINT" | grep -E "Requests per second|Time per request|Failed requests"
echo ""

# Test 3: Medium load (100 requests, 20 concurrent)
echo -e "${YELLOW}Test 3: Medium Load (100 requests, 20 concurrent)${NC}"
echo "--------------------------------------------"
ab -n 100 -c 20 -q "$CKAN_URL$TEST_ENDPOINT" | grep -E "Requests per second|Time per request|Failed requests"
echo ""

# Test 4: Heavy load (200 requests, 40 concurrent) - The problematic scenario
echo -e "${YELLOW}Test 4: Heavy Load (200 requests, 40 concurrent)${NC}"
echo "--------------------------------------------"
ab -n 200 -c 40 -q "$CKAN_URL$TEST_ENDPOINT" > /tmp/ab_test.txt 2>&1

# Parse results
FAILED=$(grep "Failed requests" /tmp/ab_test.txt | awk '{print $3}')
RPS=$(grep "Requests per second" /tmp/ab_test.txt | awk '{print $4}')
TIME=$(grep "Time per request.*mean" /tmp/ab_test.txt | head -1 | awk '{print $4}')

echo "Requests per second:    $RPS [#/sec]"
echo "Time per request:       $TIME [ms] (mean)"
echo "Failed requests:        $FAILED"
echo ""

# Check for success
if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}✓ SUCCESS: All requests completed without failures!${NC}"
    echo -e "${GREEN}✓ Catalog can handle 40+ concurrent users.${NC}"
else
    echo -e "${RED}✗ FAILURE: $FAILED requests failed${NC}"
    echo -e "${RED}✗ Catalog may still have concurrency issues.${NC}"
fi

echo ""
echo "=========================================="
echo "Test Complete"
echo "=========================================="
echo ""
echo "Full results saved to: /tmp/ab_test.txt"
echo "View with: cat /tmp/ab_test.txt"
