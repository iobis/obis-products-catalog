import requests
import json
import re
import os
from urllib.parse import urljoin

# Configuration
OBIS_API_URL = "https://api.obis.org/v3/node"
CKAN_BASE_URL = os.getenv('CKAN_URL', 'http://localhost:5000')
CKAN_TOKEN = os.getenv('CKAN_TOKEN')

if not CKAN_TOKEN:
    print("Error: Please set the CKAN_TOKEN environment variable")
    print("Usage: CKAN_TOKEN=your-token python3 obis_sync.py")
    exit(1)

# Headers for CKAN API requests (direct token format, not Bearer)
HEADERS = {
    'Authorization': CKAN_TOKEN,
    'Content-Type': 'application/json'
}

def slugify(text):
    """Convert text to URL-friendly slug"""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')

def fetch_obis_nodes():
    """Fetch all OBIS nodes from the API"""
    try:
        response = requests.get(OBIS_API_URL)
        response.raise_for_status()
        data = response.json()
        # OBIS API returns {"total": X, "results": [...]}
        return data.get('results', [])
    except requests.RequestException as e:
        print(f"Error fetching OBIS nodes: {e}")
        return []

def get_existing_organizations():
    """Get all existing CKAN organizations"""
    # First get just the list of organization names
    list_url = urljoin(CKAN_BASE_URL, "/api/3/action/organization_list")
    try:
        response = requests.get(list_url)
        response.raise_for_status()
        data = response.json()
        if not data['success']:
            return {}
        
        org_names = data['result']
        print(f"Found {len(org_names)} organization names: {org_names}")
        
        # Now get full details for each organization
        org_lookup = {}
        show_url = urljoin(CKAN_BASE_URL, "/api/3/action/organization_show")
        
        for org_name in org_names:
            try:
                response = requests.get(show_url, params={'id': org_name})
                response.raise_for_status()
                org_data = response.json()
                if org_data['success']:
                    org_lookup[org_name] = org_data['result']
            except requests.RequestException as e:
                print(f"Error fetching details for {org_name}: {e}")
        
        print(f"Successfully loaded {len(org_lookup)} organizations")
        return org_lookup
        
    except requests.RequestException as e:
        print(f"Error fetching CKAN organizations: {e}")
        return {}

def create_organization(node_data):
    """Create a new CKAN organization from OBIS node data"""
    org_name = slugify(node_data['name'])
    
    # Get the first URL from the array, handle null/empty cases
    node_url = ''
    if node_data.get('url') and len(node_data['url']) > 0:
        node_url = node_data['url'][0]
    
    # Prepare organization data
    org_data = {
        'name': org_name,
        'title': node_data['name'],
        'description': node_data.get('description', ''),
        'extras': [
            {'key': 'obis_node_id', 'value': node_data['id']},
            {'key': 'node_type', 'value': node_data.get('type', '')},
            {'key': 'node_url', 'value': node_url},
            {'key': 'longitude', 'value': str(node_data.get('lon', ''))},
            {'key': 'latitude', 'value': str(node_data.get('lat', ''))},
            {'key': 'theme', 'value': node_data.get('theme', '')},
            {'key': 'contacts', 'value': json.dumps(node_data.get('contacts', []))},
            {'key': 'feeds', 'value': json.dumps(node_data.get('feeds', []))}
        ]
    }
    
    url = urljoin(CKAN_BASE_URL, "/api/3/action/organization_create")
    
    try:
        response = requests.post(url, headers=HEADERS, data=json.dumps(org_data))
        response.raise_for_status()
        result = response.json()
        
        if result['success']:
            print(f"✓ Created organization: {node_data['name']} (URL: {node_url})")
            return True
        else:
            print(f"✗ Failed to create {node_data['name']}: {result.get('error', 'Unknown error')}")
            print(f"  Full error: {result}")
            return False
            
    except requests.RequestException as e:
        print(f"✗ Error creating organization {node_data['name']}: {e}")
        # Try to get more details from the response
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"  Detailed error: {error_detail}")
            except:
                print(f"  Response text: {e.response.text}")
        return False

def update_organization(existing_org, node_data):
    """Update an existing CKAN organization with OBIS node data"""
    org_name = existing_org['name']
    
    # Get the first URL from the array, handle null/empty cases
    node_url = ''
    if node_data.get('url') and len(node_data['url']) > 0:
        node_url = node_data['url'][0]
    
    # Always update to ensure we have the latest data from OBIS
    # Prepare updated organization data
    org_data = {
        'id': existing_org['id'],
        'name': org_name,
        'title': node_data['name'],
        'description': node_data.get('description', ''),
        'extras': [
            {'key': 'obis_node_id', 'value': node_data['id']},
            {'key': 'node_type', 'value': node_data.get('type', '')},
            {'key': 'node_url', 'value': node_url},
            {'key': 'longitude', 'value': str(node_data.get('lon', ''))},
            {'key': 'latitude', 'value': str(node_data.get('lat', ''))},
            {'key': 'theme', 'value': node_data.get('theme', '')},
            {'key': 'contacts', 'value': json.dumps(node_data.get('contacts', []))},
            {'key': 'feeds', 'value': json.dumps(node_data.get('feeds', []))}
        ]
    }
    
    url = urljoin(CKAN_BASE_URL, "/api/3/action/organization_update")
    
    try:
        response = requests.post(url, headers=HEADERS, data=json.dumps(org_data))
        response.raise_for_status()
        result = response.json()
        
        if result['success']:
            print(f"↻ Updated organization: {node_data['name']} (URL: {node_url})")
            return True
        else:
            print(f"✗ Failed to update {node_data['name']}: {result.get('error', 'Unknown error')}")
            return False
            
    except requests.RequestException as e:
        print(f"✗ Error updating organization {node_data['name']}: {e}")
        return False

def add_obis_secretariat():
    """Add OBIS Secretariat as a special organization"""
    secretariat_data = {
        'id': 'obis-secretariat',
        'name': 'OBIS Secretariat',
        'description': 'The Ocean Biodiversity Information System (OBIS) Secretariat coordinates the global OBIS network.',
        'type': 'secretariat',
        'url': ['https://obis.org'],
        'contacts': []
    }
    
    existing_orgs = get_existing_organizations()
    secretariat_slug = slugify(secretariat_data['name'])
    
    if secretariat_slug in existing_orgs:
        print("→ OBIS Secretariat already exists")
        return True
    else:
        return create_organization(secretariat_data)

def sync_obis_nodes():
    """Main function to sync OBIS nodes with CKAN organizations"""
    print("Starting OBIS node synchronization...")
    print("=" * 50)
    
    # Check configuration
    if not CKAN_TOKEN:
        print("✗ Error: Please set the CKAN_TOKEN environment variable")
        print("Usage: CKAN_TOKEN=your-token python3 obis_sync.py")
        return False
    
    # Fetch data
    print("Fetching OBIS nodes...")
    nodes = fetch_obis_nodes()
    if not nodes:
        print("✗ No nodes found or API error")
        return False
    
    print("Fetching existing CKAN organizations...")
    existing_orgs = get_existing_organizations()
    
    # Process each node
    print(f"\nProcessing {len(nodes)} OBIS nodes...")
    created = updated = failed = 0
    
    for node in nodes:
        node_slug = slugify(node['name'])
        print(f"Processing: {node['name']} → {node_slug}")
        
        if node_slug in existing_orgs:
            print(f"  Found existing org: {node_slug}")
            if update_organization(existing_orgs[node_slug], node):
                updated += 1
            else:
                failed += 1
        else:
            print(f"  Creating new org: {node_slug}")
            if create_organization(node):
                created += 1
            else:
                failed += 1
    
    # Summary
    print("\n" + "=" * 50)
    print("Synchronization complete!")
    print(f"Created: {created}")
    print(f"Updated: {updated}")
    print(f"Failed: {failed}")
    print(f"Total processed: {len(nodes)}")
    
    return failed == 0

if __name__ == "__main__":
    success = sync_obis_nodes()
    exit(0 if success else 1)
