#!/bin/bash

# CKAN Authenticated Load Test
# Simulates real users logging in and browsing

# Configuration
CKAN_URL="http://134.199.199.216"
USERNAME_PREFIX="user"
PASSWORD="test1234"
NUM_USERS=40

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo "CKAN Authenticated Load Test"
echo "=========================================="
echo ""
echo "Testing: $CKAN_URL"
echo "Simulating: $NUM_USERS concurrent user logins"
echo ""

# Create a temporary directory for cookies
TEMP_DIR=$(mktemp -d)
echo "Cookie directory: $TEMP_DIR"
echo ""

# Function to simulate a user session
test_user_login() {
    local user_num=$1
    local username="${USERNAME_PREFIX}${user_num}"
    local cookie_file="${TEMP_DIR}/cookie_${user_num}.txt"
    local log_file="${TEMP_DIR}/user_${user_num}.log"
    
    # Step 1: Get login page (and CSRF token)
    curl -s -c "$cookie_file" \
        "${CKAN_URL}/user/login" \
        > /dev/null 2>&1
    
    # Step 2: Extract CSRF token
    local csrf_token=$(curl -s -b "$cookie_file" "${CKAN_URL}/user/login" | \
        grep -o 'name="_csrf_token" value="[^"]*"' | \
        sed 's/name="_csrf_token" value="//;s/"//')
    
    # Step 3: POST login
    local start_time=$(date +%s.%N)
    local response=$(curl -s -b "$cookie_file" -c "$cookie_file" \
        -X POST \
        -d "login=${username}" \
        -d "password=${PASSWORD}" \
        -d "_csrf_token=${csrf_token}" \
        -w "\nHTTP_CODE:%{http_code}\nTIME_TOTAL:%{time_total}\n" \
        "${CKAN_URL}/user/login" 2>&1)
    local end_time=$(date +%s.%N)
    
    # Parse response
    local http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d: -f2)
    local time_total=$(echo "$response" | grep "TIME_TOTAL:" | cut -d: -f2)
    
    # Check if login was successful (302 redirect or 200)
    if [[ "$http_code" == "302" ]] || [[ "$http_code" == "200" ]]; then
       # Step 4: Access an authenticated page to verify login worked
        # Using /dataset/new-choice which requires being logged in
        local verify=$(curl -s -b "$cookie_file" "${CKAN_URL}/user/${username}" -w "%{http_code}")
        local verify_code="${verify: -3}"
        
        # Success if we get 200 (page loads) or 302 (redirect but authenticated)
        # Failure if we get 403 (forbidden) or 302 back to login
        if [[ "$verify_code" == "200" ]] || [[ "$verify_code" == "302" ]]; then
            # Double-check it's not redirecting back to login
        if echo "$verify" | grep -q "logout"; then
                echo "success|${username}|${time_total}" >> "${TEMP_DIR}/results.txt"
            else
                echo "failed|${username}|auth_failed|no_session" >> "${TEMP_DIR}/results.txt"
            fi
        else
            echo "failed|${username}|auth_failed|${verify_code}" >> "${TEMP_DIR}/results.txt"
        fi
    else
        echo "failed|${username}|login_failed|${http_code}" >> "${TEMP_DIR}/results.txt"
    fi 
}

# Export function so subshells can use it
export -f test_user_login
export CKAN_URL USERNAME_PREFIX PASSWORD TEMP_DIR

echo -e "${YELLOW}Starting concurrent login test...${NC}"
echo "This will take 30-60 seconds..."
echo ""

# Start timer
TEST_START=$(date +%s)

# Launch all user sessions in parallel
for i in $(seq 1 $NUM_USERS); do
    test_user_login $i &
done

# Wait for all background jobs to complete
wait

# End timer
TEST_END=$(date +%s)
TEST_DURATION=$((TEST_END - TEST_START))

echo ""
echo "=========================================="
echo "Results"
echo "=========================================="
echo ""

# Parse results
if [ -f "${TEMP_DIR}/results.txt" ]; then
    TOTAL=$(wc -l < "${TEMP_DIR}/results.txt")
    SUCCESS=$(grep -c "^success" "${TEMP_DIR}/results.txt" || echo "0")
    FAILED=$(grep -c "^failed" "${TEMP_DIR}/results.txt" || echo "0")
    
    # Calculate average login time for successful logins
    if [ "$SUCCESS" -gt 0 ]; then
        AVG_TIME=$(grep "^success" "${TEMP_DIR}/results.txt" | \
            cut -d'|' -f3 | \
            awk '{sum+=$1} END {printf "%.3f", sum/NR}')
    else
        AVG_TIME="N/A"
    fi
    
    echo "Total test duration:    ${TEST_DURATION} seconds"
    echo "Users tested:           $TOTAL"
    echo "Successful logins:      $SUCCESS"
    echo "Failed logins:          $FAILED"
    echo "Average login time:     ${AVG_TIME} seconds"
    echo ""
    
    # Show failures if any
    if [ "$FAILED" -gt 0 ]; then
        echo -e "${RED}Failed logins:${NC}"
        grep "^failed" "${TEMP_DIR}/results.txt" | while read line; do
            username=$(echo "$line" | cut -d'|' -f2)
            reason=$(echo "$line" | cut -d'|' -f3)
            code=$(echo "$line" | cut -d'|' -f4)
            echo "  - $username: $reason (HTTP $code)"
        done
        echo ""
    fi
    
    # Final verdict
    if [ "$FAILED" -eq 0 ]; then
        echo -e "${GREEN}✓ SUCCESS: All $NUM_USERS users logged in successfully!${NC}"
        echo -e "${GREEN}✓ No freezing or timeouts detected.${NC}"
        
        if (( $(echo "$AVG_TIME < 5" | bc -l) )); then
            echo -e "${GREEN}✓ Login times are excellent (< 5 seconds average).${NC}"
        elif (( $(echo "$AVG_TIME < 10" | bc -l) )); then
            echo -e "${YELLOW}⚠ Login times are acceptable (5-10 seconds average).${NC}"
        else
            echo -e "${YELLOW}⚠ Login times are slow (> 10 seconds average).${NC}"
        fi
    else
        echo -e "${RED}✗ FAILURE: $FAILED out of $NUM_USERS logins failed.${NC}"
        echo -e "${RED}✗ System may still have concurrency issues.${NC}"
    fi
else
    echo -e "${RED}✗ ERROR: No results file generated.${NC}"
fi

echo ""
echo "=========================================="
echo ""
echo "Detailed logs saved in: $TEMP_DIR"
echo "Keep directory? (y/n)"
read -t 5 -n 1 keep_logs
echo ""

if [[ ! "$keep_logs" =~ ^[Yy]$ ]]; then
    rm -rf "$TEMP_DIR"
    echo "Temporary files cleaned up."
else
    echo "Logs preserved at: $TEMP_DIR"
    echo "View results: cat ${TEMP_DIR}/results.txt"
fi
