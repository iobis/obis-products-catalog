#!/usr/bin/env python3
"""
OBIS Zenodo Harvest Script using API
"""

import os
import requests
from datetime import datetime

def load_doi_registry():
    """Load DOIs from the extension's config directory"""
    # Get the script's directory and navigate to config
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    registry_file = os.path.join(script_dir, '../config/zenodo_dois.txt')
    
    # Or use the absolute container path
    # registry_file = '/srv/app/src_extensions/ckanext-zenodo/ckanext/zenodo/config/zenodo_dois.txt'
    
    dois = []
    
    if not os.path.exists(registry_file):
        print(f"Warning: DOI registry not found at {registry_file}")
        return dois
    
    with open(registry_file, 'r') as f:
        for line in f:
            doi = line.strip()
            # Skip empty lines and comments
            if doi and not doi.startswith('#'):
                # Normalize zenodo.org/record URLs to DOI format
                if 'zenodo.org/record/' in doi:
                    record_id = doi.split('/')[-1]
                    doi = f"https://doi.org/10.5281/zenodo.{record_id}"
                dois.append(doi)
    return dois

def find_dataset_via_api(doi):
    """Search for existing dataset by DOI or Zenodo URL."""
    try:
        base_url = "http://ckan-dev:5000"  # Use container name instead
        
        # Try searching by the identifier field
        doi_value = doi.replace('https://doi.org/', '').replace('http://doi.org/', '')
        url = f"{base_url}/api/action/package_search"
        
        # Search in the identifier field or url field
        params = {
            'fq': f'identifier:*{doi_value}* OR url:"{doi}"',
            'rows': 1
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data.get('success') and data['result']['count'] > 0:
            return data['result']['results'][0]
        return None
    except Exception as e:
        print(f"    Search error: {e}")
        return None

def get_zenodo_last_modified(doi):
    """Get last modified date from Zenodo record."""
    try:
        # Extract Zenodo ID from DOI
        if 'zenodo' in doi.lower():
            zenodo_id = doi.split('/')[-1]
            if zenodo_id.startswith('zenodo.'):
                zenodo_id = zenodo_id.replace('zenodo.', '')
            
            # Remove any non-numeric characters
            zenodo_id = ''.join(filter(str.isdigit, zenodo_id))
            
            if zenodo_id:
                url = f"https://zenodo.org/api/records/{zenodo_id}"
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                data = response.json()
                return data.get('updated')
    except Exception as e:
        print(f"    Zenodo API error: {e}")
    return None

def should_update_dataset(ckan_modified, zenodo_modified):
    """Check if dataset should be updated based on modification dates."""
    if not zenodo_modified:
        return False
    
    try:
        from datetime import timezone
        
        # Parse CKAN datetime - make it timezone-aware if it isn't
        ckan_dt = datetime.fromisoformat(ckan_modified.replace('Z', '+00:00'))
        if ckan_dt.tzinfo is None:
            ckan_dt = ckan_dt.replace(tzinfo=timezone.utc)
        
        # Parse Zenodo datetime
        zenodo_dt = datetime.fromisoformat(zenodo_modified.replace('Z', '+00:00'))
        if zenodo_dt.tzinfo is None:
            zenodo_dt = zenodo_dt.replace(tzinfo=timezone.utc)
        
        return zenodo_dt > ckan_dt
    except Exception as e:
        print(f"    Date comparison error: {e}")
        return False

def update_dataset_via_api(dataset_id, doi, token):
    """Update existing dataset with fresh DOI metadata."""
    try:
        base_url = "http://ckan-dev:5000"
        headers = {
            'Authorization': f'Bearer {token}',  # Changed: Added Bearer prefix
            'Content-Type': 'application/json'
        }
        
        # First, fetch fresh metadata from Zenodo
        data = {'doi_url': doi}
        
        # Use the same harvest endpoint, which will update if dataset exists
        response = requests.post(
            f'{base_url}/api/harvest-doi',
            json=data,
            headers=headers,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"    ✓ Updated: {result.get('dataset', {}).get('title', 'Unknown')}")
            return True
        else:
            try:
                error_msg = response.json().get('error', 'Unknown error')
            except:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            print(f"    ✗ Update failed: {error_msg}")
            return False
            
    except Exception as e:
        print(f"    Update error: {e}")
        return False

def import_new_dataset_via_api(doi, token):
    """Import new dataset using the harvest API endpoint."""
    try:
        base_url = "http://ckan-dev:5000"
        headers = {
            'Authorization': f'Bearer {token}',  # Changed: Added Bearer prefix
            'Content-Type': 'application/json'
        }
        
        data = {'doi_url': doi}
        
        response = requests.post(
            f'{base_url}/api/harvest-doi',
            json=data,
            headers=headers,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"    ✓ Imported: {result.get('dataset', {}).get('title', 'Unknown')}")
            return True
        else:
            try:
                error_msg = response.json().get('error', 'Unknown error')
            except:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            print(f"    ✗ Import failed: {error_msg}")
            return False
            
    except Exception as e:
        print(f"    Import error: {e}")
        return False

def main():
    import sys
    
    print("=== Zenodo DOI Harvest ===\n")
    
    # Check for --force flag
    force_update = '--force' in sys.argv
    if force_update:
        print("FORCE UPDATE MODE: All datasets will be updated regardless of modification date\n")
    
    # Get API token from environment
    token = os.getenv('CKAN_API_TOKEN')
    if not token:
        print("ERROR: CKAN_API_TOKEN environment variable not set")
        print("Please set it to your ckan_admin API token")
        print("\nTo get your token:")
        print("1. Log in to CKAN as ckan_admin")
        print("2. Go to your user profile")
        print("3. Click 'API Tokens' tab")
        print("4. Create a new token or copy existing one")
        print("\nThen run:")
        print("  export CKAN_API_TOKEN='your-token-here'")
        print("  python harvest_zenodo.py")
        return
    
    # Load DOI registry
    dois = load_doi_registry()
    if not dois:
        print("No DOIs found in registry")
        return
        
    print(f"Found {len(dois)} DOIs to process\n")
    
    found_count = 0
    imported_count = 0
    updated_count = 0
    failed_count = 0
    
    for i, doi in enumerate(dois, 1):
        print(f"[{i}/{len(dois)}] Processing: {doi}")
        
        # Find in CKAN
        dataset = find_dataset_via_api(doi)
        
        if dataset:
            # Existing dataset - check for updates
            print(f"  ✓ Found in CKAN: {dataset['title']}")
            print(f"    CKAN modified: {dataset.get('metadata_modified', 'Unknown')}")
            
            if force_update:
                print(f"    → Force updating...")
                if update_dataset_via_api(dataset['id'], doi, token):
                    updated_count += 1
                else:
                    failed_count += 1
            else:
                # Check if Zenodo has updates
                zenodo_modified = get_zenodo_last_modified(doi)
                if zenodo_modified:
                    print(f"    Zenodo updated: {zenodo_modified}")
                    if should_update_dataset(dataset.get('metadata_modified'), zenodo_modified):
                        print(f"    → Updating with latest Zenodo data...")
                        if update_dataset_via_api(dataset['id'], doi, token):
                            updated_count += 1
                        else:
                            failed_count += 1
                    else:
                        print(f"    → No update needed (CKAN is current)")
            found_count += 1
        else:
            # New dataset - import it
            print(f"  → Not in CKAN, importing...")
            if import_new_dataset_via_api(doi, token):
                imported_count += 1
            else:
                failed_count += 1
        
        print()  # Blank line between entries
    
    print("=" * 50)
    print(f"Summary:")
    print(f"  Total DOIs processed: {len(dois)}")
    print(f"  Already in CKAN: {found_count}")
    print(f"  Newly imported: {imported_count}")
    print(f"  Updated: {updated_count}")
    print(f"  Failed: {failed_count}")
    print("=" * 50)


if __name__ == '__main__':
    main()