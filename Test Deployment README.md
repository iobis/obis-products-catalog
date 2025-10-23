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

# Verify Docker installation
docker --version
docker compose version
```

### Configure firewall

```bash
# Allow SSH (important - don't lock yourself out!)
ufw allow OpenSSH

# Allow HTTP (port 5000 for CKAN)
ufw allow 5000/tcp

# Allow HTTPS (if you set it up later)
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
# Copy example environment file
cp .env.example .env

# Generate secure secrets
SECRET_KEY=$(openssl rand -base64 32)
BEAKER_SECRET=$(openssl rand -base64 32)
JWT_ENCODE=$(openssl rand -base64 32)
JWT_DECODE=$(openssl rand -base64 32)
POSTGRES_PASSWORD=$(openssl rand -base64 16)

# Update .env file with your droplet IP
# Replace YOUR_DROPLET_IP with your actual IP address
nano .env
```

**In the `.env` file, update these critical values:**

```bash
# Site URL - IMPORTANT: Use your droplet's IP
CKAN_SITE_URL=http://YOUR_DROPLET_IP:5000

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
# Navigate to project directory
cd /root/obis-products-catalog

# Create password file
# Username: obis-tester
# Password: enter something secure when prompted (e.g., ObisTest2024!)
htpasswd -c .htpasswd obis-tester

# Verify the file was created
cat .htpasswd
```

### Update NGINX configuration

```bash
# Edit the NGINX config
nano nginx/setup/default.conf
```

**Add basic auth to the location block.** Find the section that starts with `location / {` and add the auth lines:

```nginx
location / {
    # Add these two lines for basic authentication
    auth_basic "OBIS Testing - Please Login";
    auth_basic_user_file /etc/nginx/.htpasswd;
    
    # Existing proxy configuration
    proxy_pass http://ckan:5000/;
    proxy_set_header X-Forwarded-For $remote_addr;
    proxy_set_header Host $host;
    proxy_cache cache;
    proxy_cache_bypass $cookie_auth_tkt;
    proxy_no_cache $cookie_auth_tkt;
    proxy_cache_valid 30m;
    proxy_cache_key $host$scheme$proxy_host$request_uri;
}
```

Save and exit.

### Mount htpasswd file in docker-compose

```bash
nano docker-compose.dev.yml
```

**Find the `nginx` service and add the volume mount.** It should look like this:

```yaml
  nginx:
    image: nginx:stable-alpine
    depends_on:
      - ckan-dev
    ports:
      - "0.0.0.0:${NGINX_PORT_HOST}:${NGINX_PORT}"
      - "0.0.0.0:${NGINX_SSLPORT_HOST}:${NGINX_SSLPORT}"
    volumes:
      - ./nginx/setup/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/setup/default.conf:/etc/nginx/conf.d/default.conf
      - ./nginx/setup/index.html:/usr/share/nginx/html/index.html
      - ./nginx/setup/error.html:/usr/share/nginx/html/error.html
      - ./.htpasswd:/etc/nginx/.htpasswd:ro  # ADD THIS LINE
    restart: unless-stopped
```

Save and exit.

## Step 5: Build and Start CKAN

### Build the containers

```bash
cd /root/obis-products-catalog

# Build the images (this will take 5-10 minutes)
docker compose -f docker-compose.dev.yml build
```

### Start the containers

```bash
# Start all services
docker compose -f docker-compose.dev.yml up -d

# Check that all containers are running
docker ps
```

You should see 5 containers running:
- ckan-dev
- db
- solr
- redis
- nginx (if included in dev compose)

### Initialize the database

```bash
# Wait about 30 seconds for services to be ready, then initialize
docker exec obis-products-catalog-ckan-dev-1 ckan -c /srv/app/ckan.ini db init

# If the container name is different, find it with:
docker ps | grep ckan-dev
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
# Create a script file
nano /root/create_test_users.sh
```

**Paste this script:**

```bash
#!/bin/bash

# Script to create 100 test users for OBIS CKAN testing
# Usage: ./create_test_users.sh

CONTAINER_NAME="obis-products-catalog-ckan-dev-1"
PASSWORD="test1234"
NUM_USERS=100

echo "Creating $NUM_USERS test users..."
echo "Default password for all users: $PASSWORD"
echo ""

for i in $(seq 1 $NUM_USERS); do
    USERNAME="user${i}"
    EMAIL="user${i}@test.obis.org"
    
    echo "Creating user: $USERNAME ($EMAIL)"
    
    docker exec $CONTAINER_NAME ckan -c /srv/app/ckan.ini user add \
        $USERNAME \
        email=$EMAIL \
        password=$PASSWORD 2>&1 | grep -v "WARNING"
    
    if [ $? -eq 0 ]; then
        echo "✓ Successfully created $USERNAME"
    else
        echo "✗ Failed to create $USERNAME"
    fi
    
    # Small delay to avoid overwhelming the system
    sleep 0.2
done

echo ""
echo "========================================"
echo "User creation complete!"
echo "========================================"
echo "Username format: user1, user2, ..., user100"
echo "Email format: user1@test.obis.org, etc."
echo "Password (all users): $PASSWORD"
echo ""
echo "You can also share this CSV for easy distribution:"
echo ""
echo "username,email,password" > /root/test_users.csv
for i in $(seq 1 $NUM_USERS); do
    echo "user${i},user${i}@test.obis.org,$PASSWORD" >> /root/test_users.csv
done
echo "CSV saved to: /root/test_users.csv"
```

Save and exit (Ctrl+X, Y, Enter).

### Make the script executable and run it

```bash
# Make executable
chmod +x /root/create_test_users.sh

# Run the script (takes ~1-2 minutes)
/root/create_test_users.sh
```

### Download the user list (optional)

```bash
# View the CSV file
cat /root/test_users.csv

# Or download it to your local machine
# On your LOCAL machine (not on the droplet):
scp root@YOUR_DROPLET_IP:/root/test_users.csv ~/Desktop/obis_test_users.csv
```

## Step 8: Verify Everything Works

### Check that CKAN is accessible

1. Open your browser
2. Go to: `http://YOUR_DROPLET_IP:5000`
3. You should see a login prompt:
   - Username: `obis-tester`
   - Password: `ObisTest2024!` (or whatever you set)
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

# Or view just CKAN logs
docker compose -f docker-compose.dev.yml logs -f ckan-dev

# Check container status
docker ps
```

## Step 9: Share with Testers

### Information to share with your testers

```
OBIS Products Catalog - Test Instance

🌐 URL: http://YOUR_DROPLET_IP:5000

🔐 Initial Gate Access (Browser Popup):
   Username: obis-tester
   Password: ObisTest2024!

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

Distribute specific accounts to specific testers to track who's testing what:

| Tester Name | Username | Email | Password |
|-------------|----------|-------|----------|
| Alice Smith | user1 | user1@test.obis.org | test1234 |
| Bob Jones | user2 | user2@test.obis.org | test1234 |
| ... | ... | ... | ... |

## Maintenance Commands

### Restart CKAN after making changes

```bash
cd /root/obis-products-catalog
docker compose -f docker-compose.dev.yml restart ckan-dev
```

### View logs

```bash
# All services
docker compose -f docker-compose.dev.yml logs -f

# Just CKAN
docker compose -f docker-compose.dev.yml logs -f ckan-dev
```

### Stop everything

```bash
docker compose -f docker-compose.dev.yml down
```

### Start everything

```bash
docker compose -f docker-compose.dev.yml up -d
```

### Access CKAN shell

```bash
docker exec -it obis-products-catalog-ckan-dev-1 bash
```

### Check disk space

```bash
df -h
```

### Check memory usage

```bash
free -h
htop  # (press q to quit)
```

### Monitor Docker container resources

```bash
docker stats
```

## Troubleshooting

### Issue: Can't access the site

**Check firewall:**
```bash
ufw status
# Make sure 5000/tcp is allowed
```

**Check containers are running:**
```bash
docker ps
# All containers should show "Up" status
```

**Check logs:**
```bash
docker compose -f docker-compose.dev.yml logs ckan-dev
```

### Issue: NGINX basic auth not working

**Verify htpasswd file is mounted:**
```bash
docker exec obis-products-catalog-nginx-1 cat /etc/nginx/.htpasswd
# Should show your username and encrypted password
```

**Restart NGINX:**
```bash
docker compose -f docker-compose.dev.yml restart nginx
```

### Issue: User creation fails

**Check CKAN container name:**
```bash
docker ps | grep ckan-dev
# Use the exact name in your create_test_users.sh script
```

**Try creating one user manually:**
```bash
docker exec obis-products-catalog-ckan-dev-1 ckan -c /srv/app/ckan.ini user add testuser email=test@test.com password=test123
```

### Issue: Out of memory

**Check memory usage:**
```bash
free -h
docker stats
```

**If consistently over 80% RAM usage, upgrade to 8GB droplet:**
1. Power off the droplet in Digital Ocean console
2. Click "Resize"
3. Choose 8GB plan
4. Restart droplet

### Issue: Database not initializing

**Reset and reinitialize:**
```bash
cd /root/obis-products-catalog
docker compose -f docker-compose.dev.yml down -v
docker compose -f docker-compose.dev.yml up -d
sleep 30
docker exec obis-products-catalog-ckan-dev-1 ckan -c /srv/app/ckan.ini db init
```

## Backup and Cleanup

### Backup the database

```bash
# Backup PostgreSQL database
docker exec obis-products-catalog-db-1 pg_dump -U postgres ckan > /root/ckan_backup_$(date +%Y%m%d).sql

# Download to your local machine
scp root@YOUR_DROPLET_IP:/root/ckan_backup_*.sql ~/Desktop/
```

### Clean up after testing

```bash
cd /root/obis-products-catalog

# Stop and remove containers, networks, and volumes
docker compose -f docker-compose.dev.yml down -v

# Remove Docker images (optional, saves space)
docker system prune -a
```

### Destroy the droplet

When testing is complete and you no longer need the instance:
1. Log into Digital Ocean
2. Select your droplet
3. Click "Destroy"
4. Confirm destruction

⚠️ **Make sure to backup any data you want to keep before destroying!**

## Security Notes for Production

This setup is appropriate for **testing only**. For production, you need:

- [ ] Proper SSL/TLS certificates (Let's Encrypt)
- [ ] Strong, unique passwords (not shared test passwords)
- [ ] Proper user authentication (SSO, OAuth)
- [ ] Regular backups
- [ ] Monitoring and alerting
- [ ] Security updates and patches
- [ ] Proper firewall configuration
- [ ] Rate limiting
- [ ] DDoS protection

## Estimated Costs

- Droplet: $24/month (can be prorated daily)
- Backups (optional): +$4.80/month
- Snapshots: ~$0.05/GB/month

**For a 2-week testing period: ~$12-15 total**

## Next Steps

After successful testing:
1. Gather and incorporate user feedback
2. Plan production deployment
3. Set up proper production infrastructure
4. Implement monitoring and backups
5. Configure SSL and domain name
6. Review security hardening checklist

---

## Quick Reference Commands

```bash
# SSH to droplet
ssh root@YOUR_DROPLET_IP

# Go to project directory
cd /root/obis-products-catalog

# View logs
docker compose -f docker-compose.dev.yml logs -f ckan-dev

# Restart CKAN
docker compose -f docker-compose.dev.yml restart ckan-dev

# Create admin user
docker exec obis-products-catalog-ckan-dev-1 ckan -c /srv/app/ckan.ini sysadmin add USERNAME email=EMAIL@example.com

# Access CKAN shell
docker exec -it obis-products-catalog-ckan-dev-1 bash

# Check container status
docker ps

# Check system resources
htop
free -h
df -h
```