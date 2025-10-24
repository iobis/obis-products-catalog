# OBIS Products Catalog - Digital Ocean Test Deployment Guide

This guide will walk you through deploying the CKAN dev environment to Digital Ocean for user testing, complete with NGINX basic authentication and 100 test user accounts.

## Prerequisites

- Digital Ocean account
- SSH key configured in Digital Ocean
- Domain name (optional, can use IP address)

## Step 1: Create Digital Ocean Droplet

### Create the Droplet

1. Log into Digital Ocean
2. Click "Create" → "Droplets"
3. **Choose configuration:**
   - **Image:** Ubuntu 24.04 (LTS) x64
   - **Droplet Type:** Basic
   - **CPU Options:** Regular (Disk type: SSD)
   - **Size:** $24/month - 2 vCPUs, 4GB RAM, 80GB SSD
   - **Datacenter:** Choose closest to your users
   - **Authentication:** SSH Key (recommended)
   - **Hostname:** obis-test-catalog

4. Click "Create Droplet"
5. Wait ~60 seconds for droplet to be created
6. Note the IP address (e.g., `164.90.XXX.XXX`)

## Step 2: Initial Server Setup

### Connect to your droplet

```bash
ssh root@YOUR_DROPLET_IP
```

### Reboot if kernel update recommended

If you see a message about restarting the kernel:

```bash
reboot
# Wait 30 seconds, then reconnect
ssh root@YOUR_DROPLET_IP
```

### Update system and install dependencies

```bash
# Update package list
apt-get update

# Upgrade existing packages
apt-get upgrade -y

# Install required packages
apt-get install -y \
    git \
    apache2-utils \
    curl \
    ca-certificates \
    gnupg \
    lsb-release
```

### Install Docker

```bash
# Add Docker's official GPG key
mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Set up the repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Start Docker
systemctl start docker
systemctl enable docker

# Verify Docker installation
docker --version
docker compose version
```

### Configure firewall

```bash
# Allow SSH (important - don't lock yourself out!)
ufw allow OpenSSH

# Allow HTTP (port 80 for NGINX)
ufw allow 80/tcp

# Allow HTTPS (port 443 for NGINX)
ufw allow 443/tcp

# Enable firewall
ufw --force enable

# Check status
ufw status
```

## Step 3: Clone and Configure the Repository

### Clone your repository

```bash
cd /root
git clone https://github.com/iobis/obis-products-catalog.git
cd obis-products-catalog
```

### Create and configure .env file

```bash
# Generate secure secrets
SECRET_KEY=$(openssl rand -base64 32)
BEAKER_SECRET=$(openssl rand -base64 32)
JWT_ENCODE=$(openssl rand -base64 32)
JWT_DECODE=$(openssl rand -base64 32)
POSTGRES_PASSWORD=$(openssl rand -base64 16)

# Display them (copy these values)
echo "SECRET_KEY=$SECRET_KEY"
echo "BEAKER_SECRET=$BEAKER_SECRET"
echo "JWT_ENCODE=$JWT_ENCODE"
echo "JWT_DECODE=$JWT_DECODE"
echo "POSTGRES_PASSWORD=$POSTGRES_PASSWORD"

# Edit .env file
nano .env
```

**In the `.env` file, update these critical values:**

```bash
# Site URL - IMPORTANT: Use your droplet's IP
CKAN_SITE_URL=http://YOUR_DROPLET_IP

# Security - Use the generated secrets above
CKAN___SECRET_KEY=<paste SECRET_KEY here>
CKAN___BEAKER__SESSION__SECRET=<paste BEAKER_SECRET here>
CKAN___API_TOKEN__JWT__ENCODE__SECRET=string:<paste JWT_ENCODE here>
CKAN___API_TOKEN__JWT__DECODE__SECRET=string:<paste JWT_DECODE here>

# Database
POSTGRES_PASSWORD=<paste POSTGRES_PASSWORD here>

# Allow user registration for testing
CKAN__AUTH__CREATE_USER_VIA_WEB=true
CKAN__AUTH__PUBLIC_USER_REGISTRATION=true

# Optional: Set catalog name
CKAN___ODIS__CATALOG_NAME=OBIS Products Catalog (TEST)
CKAN___ODIS__CATALOG_LEGAL_NAME=Ocean Biodiversity Information System (OBIS) Products Catalog - Test Instance
```

Save and exit (Ctrl+X, Y, Enter in nano).

## Step 4: Set Up NGINX Basic Authentication

### Create htpasswd file

```bash
cd /root/obis-products-catalog

# Create password file with your desired username/password
htpasswd -c .htpasswd YOUR_USERNAME
# Enter password when prompted (e.g., obis / obis-pc-test)

# Verify the file was created
cat .htpasswd
```

### Create self-signed SSL certificates

```bash
cd /root/obis-products-catalog/nginx/setup/

openssl req -new -newkey rsa:4096 -days 365 -nodes -x509 \
  -subj "/C=US/ST=State/L=City/O=OBIS/CN=localhost" \
  -keyout ckan-local.key -out ckan-local.crt

# Verify certificates were created
ls -la ckan-local.*
```

### Update NGINX configuration

```bash
nano nginx/setup/default.conf
```

**Make these changes:**

1. **Enable HTTP (port 80)** - Uncomment these lines at the top of the server block:
```nginx
server {
    listen       80;           # UNCOMMENT THIS
    listen  [::]:80;           # UNCOMMENT THIS
    listen       443 ssl;
    listen  [::]:443 ssl;
```

2. **Change server_name** - Find and change:
```nginx
server_name  localhost;
```
To:
```nginx
server_name  _;
```

3. **Fix proxy_pass** - Find and change:
```nginx
proxy_pass http://ckan:5000/;
```
To:
```nginx
proxy_pass http://ckan-dev:5000/;
```

4. **Add basic authentication** - In the `location /` block, add:
```nginx
location / {
    # Add basic authentication
    auth_basic "OBIS Testing - Please Login";
    auth_basic_user_file /etc/nginx/.htpasswd;
    
    # Existing proxy configuration
    proxy_pass http://ckan-dev:5000/;
    proxy_set_header X-Forwarded-For $remote_addr;
    proxy_set_header Host $host;
    proxy_cache cache;
    proxy_cache_bypass $cookie_auth_tkt;
    proxy_no_cache $cookie_auth_tkt;
    proxy_cache_valid 30m;
    proxy_cache_key $host$scheme$proxy_host$request_uri;
}
```

5. **Remove 401 from error_page** - Find the error_page line and remove `401`:
```nginx
# BEFORE:
error_page 400 401 402 403 404 ... /error.html;

# AFTER (remove 401):
error_page 400 402 403 404 405 406 407 408 409 410 411 412 413 414 415 416 417 418 421 422 423 424 425 426 428 429 431 451 500 501 502 503 504 505 506 507 508 510 511 /error.html;
```

Save and exit.

### Add NGINX to docker-compose.dev.yml

```bash
nano docker-compose.dev.yml
```

**Add this NGINX service at the end of the services section:**

```yaml
  nginx:
    image: nginx:stable-alpine
    depends_on:
      - ckan-dev
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/setup/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/setup/default.conf:/etc/nginx/conf.d/default.conf
      - ./nginx/setup/ckan-local.crt:/etc/nginx/certs/ckan-local.crt:ro
      - ./nginx/setup/ckan-local.key:/etc/nginx/certs/ckan-local.key:ro
      - ./.htpasswd:/etc/nginx/.htpasswd:ro
    restart: unless-stopped
```

Save and exit.

## Step 5: Build and Start CKAN

### Fix source folder permissions

```bash
cd /root/obis-products-catalog
chmod -R 777 src/
```

### Build and start containers

```bash
# Build the images (this will take 5-10 minutes)
docker compose -f docker-compose.dev.yml build

# Start all services (watch the output, don't use -d yet)
docker compose -f docker-compose.dev.yml up ckan-dev
```

**Watch the logs**. When you see the extensions installing and CKAN starting up successfully (look for "Running on http://0.0.0.0:5000"), press **Ctrl+C** and start in detached mode:

```bash
# Start in background
docker compose -f docker-compose.dev.yml up -d

# Check all containers are running
docker ps
```

You should see 6 containers running:
- ckan-dev
- db
- solr
- redis
- datapusher
- nginx

### Install extensions manually (if needed)

If the extensions fail to install automatically, install them manually:

```bash
docker exec -u 0 obis-products-catalog-ckan-dev-1 chown -R ckan-sys:ckan-sys /srv/app/src_extensions

docker exec -u 0 obis-products-catalog-ckan-dev-1 pip install -e /srv/app/src_extensions/ckanext-doi-import
docker exec -u 0 obis-products-catalog-ckan-dev-1 pip install -e /srv/app/src_extensions/ckanext-obis_theme
docker exec -u 0 obis-products-catalog-ckan-dev-1 pip install -e /srv/app/src_extensions/ckanext-odis
docker exec -u 0 obis-products-catalog-ckan-dev-1 pip install -e /srv/app/src_extensions/ckanext-zenodo

# Restart CKAN
docker compose -f docker-compose.dev.yml restart ckan-dev
```

### Initialize the database

```bash
# Wait about 30 seconds for services to be ready
sleep 30

# Initialize database
docker exec obis-products-catalog-ckan-dev-1 ckan -c /srv/app/ckan.ini db init
```

## Step 6: Create Admin Account

```bash
# Create your admin account
docker exec obis-products-catalog-ckan-dev-1 ckan -c /srv/app/ckan.ini sysadmin add admin email=admin@obis.org

# Enter a secure password when prompted
```

## Step 7: Create 100 Test User Accounts

### Create the user creation script

```bash
nano /root/create_test_users.sh
```

**Paste this script:**

```bash
#!/bin/bash

# Script to create 100 test users for OBIS CKAN testing
# Usage: ./create_test_users.sh [number_of_users] [password]

CONTAINER_NAME="obis-products-catalog-ckan-dev-1"
DEFAULT_PASSWORD="test1234"
DEFAULT_NUM_USERS=100

NUM_USERS="${1:-$DEFAULT_NUM_USERS}"
PASSWORD="${2:-$DEFAULT_PASSWORD}"

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "========================================"
echo "OBIS CKAN Test User Creation Script"
echo "========================================"
echo ""
echo "Creating $NUM_USERS test users with password: $PASSWORD"
echo ""

SUCCESS_COUNT=0
FAIL_COUNT=0

for i in $(seq 1 $NUM_USERS); do
    USERNAME="user${i}"
    EMAIL="user${i}@test.obis.org"
    
    if [ $((i % 10)) -eq 0 ]; then
        echo "Progress: $i/$NUM_USERS users processed..."
    fi
    
    OUTPUT=$(docker exec $CONTAINER_NAME ckan -c /srv/app/ckan.ini user add \
        $USERNAME \
        email=$EMAIL \
        password=$PASSWORD 2>&1)
    
    if [ $? -eq 0 ]; then
        ((SUCCESS_COUNT++))
    else
        echo -e "${RED}✗ Failed to create $USERNAME${NC}"
        ((FAIL_COUNT++))
    fi
    
    sleep 0.1
done

echo ""
echo "========================================"
echo "User Creation Complete!"
echo "========================================"
echo -e "${GREEN}✓ Successfully created: $SUCCESS_COUNT users${NC}"
if [ $FAIL_COUNT -gt 0 ]; then
    echo -e "${RED}✗ Failed: $FAIL_COUNT users${NC}"
fi
echo ""

# Generate CSV
CSV_FILE="/root/test_users.csv"
echo "username,email,password" > $CSV_FILE
for i in $(seq 1 $NUM_USERS); do
    echo "user${i},user${i}@test.obis.org,$PASSWORD" >> $CSV_FILE
done
echo "CSV saved to: $CSV_FILE"
```

Save and exit (Ctrl+X, Y, Enter).

### Make the script executable and run it

```bash
chmod +x /root/create_test_users.sh
/root/create_test_users.sh
```

## Step 8: Verify Everything Works

### Check that CKAN is accessible via NGINX

1. Open your browser
2. Go to: `http://YOUR_DROPLET_IP` (no port number)
3. You should see a browser authentication prompt:
   - Username: `obis` (or whatever you set)
   - Password: `obis-pc-test` (or whatever you set)
4. After basic auth, you should see the CKAN homepage

### Test a user account

1. Click "Log in" in the top right
2. Try logging in with:
   - Username: `user1`
   - Password: `test1234`
3. Try creating a test dataset

### Check logs if there are issues

```bash
# View all logs
docker compose -f docker-compose.dev.yml logs -f

# View CKAN logs
docker compose -f docker-compose.dev.yml logs -f ckan-dev

# View NGINX logs
docker compose -f docker-compose.dev.yml logs -f nginx

# Check container status
docker ps
```

## Step 9: Share with Testers

### Information to share with your testers

```
OBIS Products Catalog - Test Instance

🌐 URL: http://YOUR_DROPLET_IP

🔐 Initial Gate Access (Browser Popup):
   Username: obis
   Password: obis-pc-test

👤 Your CKAN Test Account:
   Username: user1 (through user100)
   Password: test1234
   Email: user1@test.obis.org

📝 Instructions:
1. Visit the URL above
2. Enter the gate credentials when prompted by your browser
3. Once on the site, click "Log in" in the top right
4. Use your assigned CKAN username (userX) and password
5. Test creating, editing, and searching for datasets

⚠️ Note: This is a TEST instance. Data may be reset at any time.
```

### Create an assignment spreadsheet

Distribute specific accounts to specific testers:

| Tester Name | Username | Email | Password |
|-------------|----------|-------|----------|
| Alice Smith | user1 | user1@test.obis.org | test1234 |
| Bob Jones | user2 | user2@test.obis.org | test1234 |

## Maintenance Commands

### Change NGINX username/password

```bash
cd /root/obis-products-catalog

# Remove old password file
rm .htpasswd

# Create new one
htpasswd -c .htpasswd NEW_USERNAME
# Enter new password when prompted

# Restart NGINX
docker compose -f docker-compose.dev.yml restart nginx
```

### Restart CKAN after making changes

```bash
docker compose -f docker-compose.dev.yml restart ckan-dev
```

### View logs

```bash
# All services
docker compose -f docker-compose.dev.yml logs -f

# Just CKAN
docker compose -f docker-compose.dev.yml logs -f ckan-dev

# Just NGINX
docker compose -f docker-compose.dev.yml logs -f nginx
```

### Stop everything

```bash
docker compose -f docker-compose.dev.yml down
```

### Start everything

```bash
docker compose -f docker-compose.dev.yml up -d
```

### Check system resources

```bash
# Disk space
df -h

# Memory usage
free -h

# Container resources
docker stats
```

## Troubleshooting

### Issue: Can't access the site

**Check firewall:**
```bash
ufw status
# Make sure 80/tcp and 443/tcp are allowed
```

**Check containers are running:**
```bash
docker ps
# All containers should show "Up" status
```

**Check NGINX logs:**
```bash
docker compose -f docker-compose.dev.yml logs nginx
```

### Issue: NGINX showing 404

This usually means the config isn't correct. Verify:

```bash
# Check active NGINX config
docker exec obis-products-catalog-nginx-1 nginx -T | grep -A 10 "location /"

# Should show proxy_pass to ckan-dev, not ckan
# Should show auth_basic lines
# Server_name should be _ not localhost
```

**Fix and restart:**
```bash
nano nginx/setup/default.conf
# Make corrections
docker compose -f docker-compose.dev.yml restart nginx
```

### Issue: NGINX password prompt not working

This happens if 401 is in the error_page directive.

```bash
nano nginx/setup/default.conf
# Remove 401 from error_page line
docker compose -f docker-compose.dev.yml restart nginx
```

### Issue: CKAN container keeps restarting

**Check if extensions are installed:**
```bash
docker exec obis-products-catalog-ckan-dev-1 pip list | grep ckanext
```

**If extensions are missing, install manually** (see Step 5).

**Check permissions:**
```bash
ls -la /root/obis-products-catalog/src/
# Should show 92 92 or 777 permissions
```

### Issue: Out of memory

```bash
# Check memory
free -h
docker stats

# If consistently over 80%, upgrade droplet to 8GB
```

### Issue: Database not initializing

```bash
# Reset and reinitialize
docker compose -f docker-compose.dev.yml down -v
docker compose -f docker-compose.dev.yml up -d
sleep 60
docker exec obis-products-catalog-ckan-dev-1 ckan -c /srv/app/ckan.ini db init
```

## Backup and Cleanup

### Backup the database

```bash
# Backup PostgreSQL
docker exec obis-products-catalog-db-1 pg_dump -U postgres ckan > /root/ckan_backup_$(date +%Y%m%d).sql

# Download to local machine
scp root@YOUR_DROPLET_IP:/root/ckan_backup_*.sql ~/Desktop/
```

### Clean up after testing

```bash
cd /root/obis-products-catalog
docker compose -f docker-compose.dev.yml down -v
docker system prune -a
```

### Destroy the droplet

1. Log into Digital Ocean console
2. Select your droplet
3. Click "Destroy"
4. Confirm

⚠️ **Backup data before destroying!**

## Security Notes

This setup is for **testing only**. For production:

- [ ] Use Let's Encrypt SSL certificates
- [ ] Strong, unique passwords
- [ ] Proper user authentication (SSO/OAuth)
- [ ] Regular backups
- [ ] Monitoring and alerting
- [ ] Security updates
- [ ] Rate limiting
- [ ] DDoS protection

## Estimated Costs

- Droplet: $24/month (prorated daily ~$0.80/day)
- **For 2-week testing: ~$12-15 total**

## Quick Reference

```bash
# SSH to droplet
ssh root@YOUR_DROPLET_IP

# Go to project
cd /root/obis-products-catalog

# View logs
docker compose -f docker-compose.dev.yml logs -f ckan-dev

# Restart services
docker compose -f docker-compose.dev.yml restart ckan-dev
docker compose -f docker-compose.dev.yml restart nginx

# Check status
docker ps

# Check resources
free -h
df -h
```

---

**Last Updated:** October 2025