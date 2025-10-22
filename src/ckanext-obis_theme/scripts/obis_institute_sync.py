#!/usr/bin/env python3
"""
OBIS Institutions to CKAN Groups Sync with Ocean Expert Integration

This script builds on the successful OBIS node sync approach, but for institutions.
It fetches OBIS institutions, enriches them with Ocean Expert data, and creates CKAN groups.

Usage: CKAN_TOKEN=your-token python3 obis_institutions_sync.py
"""

import requests
import json
import re
import os
import time
import unicodedata
from urllib.parse import urljoin

# Configuration
OBIS_API_URL = "https://api.obis.org/v3/institute"
OCEAN_EXPERT_API_BASE = "https://oceanexpert.org/api/v1"
CKAN_BASE_URL = os.getenv('CKAN_URL', 'http://localhost:5000')
CKAN_TOKEN = os.getenv('CKAN_API_TOKEN')

if not CKAN_TOKEN:
    print("Error: Please set the CKAN_TOKEN environment variable")
    print("Usage: CKAN_TOKEN=your-token python3 obis_institutions_sync.py")
    exit(1)

# Headers for CKAN API requests - handle both JWT and UUID tokens
if CKAN_TOKEN and CKAN_TOKEN.startswith('eyJ'):  # JWT tokens start with 'eyJ'
    HEADERS = {
        'Authorization': CKAN_TOKEN,  # Direct JWT format works, Bearer doesn't
        'Content-Type': 'application/json'
    }
    print("Using JWT token format (Direct)")
else:
    # Traditional CKAN UUID token format
    HEADERS = {
        'Authorization': CKAN_TOKEN,
        'Content-Type': 'application/json'
    }
    print("Using UUID token format")

def slugify(text):
    """Convert text to URL-friendly slug (same as your working version)"""
    if not text:
        return "unknown-institution"
    
    # Normalize unicode characters 
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', 'ignore').decode('ascii')
    
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    text = text.strip('-')
    
    # Ensure reasonable length (CKAN groups have limits)
    if len(text) > 100:
        parts = text.split('-')
        text = parts[0]
        for part in parts[1:]:
            if len(text + '-' + part) <= 100:
                text = text + '-' + part
            else:
                break
    
    return text or "unknown-institution"

def fetch_obis_institutions():
    """Fetch all OBIS institutions, handling the pagination issue you discovered"""
    print("Fetching OBIS institutions...")
    
    # First, try the single large request approach to bypass pagination issues
    try:
        print("  Attempting single large request...")
        response = requests.get(OBIS_API_URL, params={'size': 10000}, timeout=120)
        response.raise_for_status()
        data = response.json()
        
        institutions = data.get('results', [])
        total = data.get('total', 0)
        
        print(f"  Fetched {len(institutions)} institutions (API reports {total} total)")
        
        # Filter for institutions with Ocean Expert IDs (non-null 'id' field)
        institutions_with_oe_id = []
        for inst in institutions:
            if inst.get('id') is not None:
                institutions_with_oe_id.append(inst)
        
        print(f"  Found {len(institutions_with_oe_id)} institutions with Ocean Expert IDs")
        
        # Save for debugging/future use
        with open('obis_institutions_debug.json', 'w') as f:
            json.dump({
                'total_fetched': len(institutions),
                'with_ocean_expert_id': len(institutions_with_oe_id),
                'institutions': institutions_with_oe_id
            }, f, indent=2)
        
        return institutions_with_oe_id
        
    except Exception as e:
        print(f"  Single request failed: {e}")
        print("  This confirms the pagination issue you observed")
        return []

def fetch_ocean_expert_institution(oe_id):
    """Fetch detailed institution data from Ocean Expert API"""
    try:
        url = f"{OCEAN_EXPERT_API_BASE}/institute/{oe_id}.json"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Always return data if we get a valid response - don't judge completeness here
        if data and isinstance(data, dict):
            return data
        else:
            return None
            
    except Exception as e:
        print(f"    Warning: Could not fetch Ocean Expert data for ID {oe_id}: {e}")
        return None

def get_existing_groups():
    """Get all existing CKAN groups (same pattern as your organizations function)"""
    list_url = urljoin(CKAN_BASE_URL, "/api/3/action/group_list")
    try:
        response = requests.get(list_url)
        response.raise_for_status()
        data = response.json()
        if not data['success']:
            return {}
        
        group_names = data['result']
        print(f"Found {len(group_names)} existing groups: {group_names[:10]}{'...' if len(group_names) > 10 else ''}")
        
        # Get full details for each group
        group_lookup = {}
        show_url = urljoin(CKAN_BASE_URL, "/api/3/action/group_show")
        
        for group_name in group_names:
            try:
                response = requests.get(show_url, params={'id': group_name})
                response.raise_for_status()
                group_data = response.json()
                if group_data['success']:
                    group_lookup[group_name] = group_data['result']
            except requests.RequestException as e:
                print(f"Error fetching details for {group_name}: {e}")
        
        print(f"Successfully loaded {len(group_lookup)} groups")
        return group_lookup
        
    except requests.RequestException as e:
        print(f"Error fetching CKAN groups: {e}")
        return {}

def create_group(institution_data, ocean_expert_data=None):
    """Create a new CKAN group from institution data"""
    group_data = create_ckan_group_data(institution_data, ocean_expert_data)
    
    if not group_data:
        return False
    
    url = urljoin(CKAN_BASE_URL, "/api/3/action/group_create")
    
    try:
        response = requests.post(url, headers=HEADERS, data=json.dumps(group_data))
        response.raise_for_status()
        result = response.json()
        
        if result['success']:
            data_quality = next((extra['value'] for extra in group_data.get('extras', []) 
                               if extra['key'] == 'data_quality'), 'unknown')
            print(f"✓ Created group: {group_data['title']} ({data_quality})")
            return True
        else:
            error_msg = result.get('error', {})
            if isinstance(error_msg, dict) and 'name' in error_msg:
                print(f"✗ Group name conflict for {group_data['title']}: {error_msg['name']}")
            else:
                print(f"✗ Failed to create {group_data['title']}: {result.get('error', 'Unknown error')}")
            return False
            
    except requests.RequestException as e:
        print(f"✗ Error creating group {group_data['title']}: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                if 'error' in error_detail and 'name' in error_detail['error']:
                    print(f"  Name conflict: {error_detail['error']['name']}")
            except:
                print(f"  Response text: {e.response.text}")
        return False

def update_group(existing_group, institution_data, ocean_expert_data=None):
    """Update an existing CKAN group with institution data"""
    group_data = create_ckan_group_data(institution_data, ocean_expert_data)
    
    if not group_data:
        return False
    
    # Preserve existing group ID and name
    group_data['id'] = existing_group['id']
    group_data['name'] = existing_group['name']
    
    url = urljoin(CKAN_BASE_URL, "/api/3/action/group_update")
    
    try:
        response = requests.post(url, headers=HEADERS, data=json.dumps(group_data))
        response.raise_for_status()
        result = response.json()
        
        if result['success']:
            data_quality = next((extra['value'] for extra in group_data.get('extras', []) 
                               if extra['key'] == 'data_quality'), 'unknown')
            print(f"↻ Updated group: {group_data['title']} ({data_quality})")
            return True
        else:
            print(f"✗ Failed to update {group_data['title']}: {result.get('error', 'Unknown error')}")
            return False
            
    except requests.RequestException as e:
        print(f"✗ Error updating group {group_data['title']}: {e}")
        return False

def create_ckan_group_data(institution_data, ocean_expert_data=None):
    """
    Create CKAN group data structure from OBIS and Ocean Expert data.
    Now properly maps Ocean Expert's nested data structure.
    """
    # Extract Ocean Expert institute data if available
    oe_institute = None
    if ocean_expert_data and 'institute' in ocean_expert_data:
        oe_institute = ocean_expert_data['institute']
    
    # Use Ocean Expert data when available and valid, fall back to OBIS data
    if oe_institute and oe_institute.get('instName'):
        title = oe_institute['instName'].strip()
        data_source_detail = "Ocean Expert data"
    elif oe_institute and oe_institute.get('instNameEng'):
        title = oe_institute['instNameEng'].strip()
        data_source_detail = "Ocean Expert data (English name)"
    else:
        title = institution_data.get('name', 'Unknown Institution').strip()
        data_source_detail = "OBIS data only"
    
    group_name = slugify(title)
    
    # Validate the group name isn't empty or too short
    if len(group_name) < 3:
        print(f"  ! Skipping institution with invalid name: '{title}' -> '{group_name}'")
        return None
    
    # Build rich description from Ocean Expert data
    description_parts = []
    
    if oe_institute:
        # Add full address information
        address_parts = []
        if oe_institute.get('instAddress'):
            address_parts.append(oe_institute['instAddress'])
        if oe_institute.get('addr2'):
            address_parts.append(oe_institute['addr2'])
        if oe_institute.get('city'):
            address_parts.append(oe_institute['city'])
        if oe_institute.get('state'):
            address_parts.append(oe_institute['state'])
        if oe_institute.get('postcode'):
            address_parts.append(oe_institute['postcode'])
        if oe_institute.get('country'):
            address_parts.append(oe_institute['country'])
        
        if address_parts:
            description_parts.append("Address: " + ", ".join(address_parts))
        
        # Add acronym if available
        if oe_institute.get('acronym'):
            description_parts.append(f"Acronym: {oe_institute['acronym']}")
        
        # Add activities if available
        if oe_institute.get('activities'):
            description_parts.append(f"Activities: {oe_institute['activities']}")
        
        # Add member count from Ocean Expert
        if ocean_expert_data.get('members', {}).get('count'):
            member_count = ocean_expert_data['members']['count']
            description_parts.append(f"Ocean Expert Members: {member_count}")
    
    # Fallback to OBIS data if no Ocean Expert description
    elif institution_data.get('country'):
        description_parts.append(f"Country: {institution_data['country']}")
    
    description = '\n'.join(description_parts) if description_parts else ''
    
    # Prepare group data
    group_data = {
        'name': group_name,
        'title': title,
        'description': description,
        'type': 'group',
        'state': 'active',
        'extras': []
    }
    
    # Add OBIS metadata
    if institution_data.get('id'):
        group_data['extras'].append({'key': 'ocean_expert_id', 'value': str(institution_data['id'])})
    if institution_data.get('code'):
        group_data['extras'].append({'key': 'obis_institution_code', 'value': institution_data['code']})
    if institution_data.get('edmo_code'):
        group_data['extras'].append({'key': 'edmo_code', 'value': str(institution_data['edmo_code'])})
    
    # Add rich Ocean Expert metadata
    if oe_institute:
        # Contact information
        if oe_institute.get('instUrl'):
            group_data['extras'].append({'key': 'website', 'value': oe_institute['instUrl']})
        if oe_institute.get('instEmail'):
            group_data['extras'].append({'key': 'email', 'value': oe_institute['instEmail']})
        if oe_institute.get('instTel'):
            group_data['extras'].append({'key': 'phone', 'value': oe_institute['instTel']})
        if oe_institute.get('instFax'):
            group_data['extras'].append({'key': 'fax', 'value': oe_institute['instFax']})
        
        # Geographic information
        if oe_institute.get('country'):
            group_data['extras'].append({'key': 'country', 'value': oe_institute['country']})
        if oe_institute.get('countryCode'):
            group_data['extras'].append({'key': 'country_code', 'value': oe_institute['countryCode']})
        if oe_institute.get('instRegion'):
            group_data['extras'].append({'key': 'region', 'value': oe_institute['instRegion']})
        
        # Institution details
        if oe_institute.get('acronym'):
            group_data['extras'].append({'key': 'acronym', 'value': oe_institute['acronym']})
        if oe_institute.get('insttypeName'):
            group_data['extras'].append({'key': 'institution_type', 'value': oe_institute['insttypeName']})
        if oe_institute.get('edmoCode'):
            group_data['extras'].append({'key': 'ocean_expert_edmo_code', 'value': str(oe_institute['edmoCode'])})
        
        # Logo URL if available
        if oe_institute.get('instLogo'):
            group_data['image_url'] = oe_institute['instLogo']
        
        # Additional metadata
        if oe_institute.get('activities'):
            group_data['extras'].append({'key': 'activities', 'value': oe_institute['activities']})
        if oe_institute.get('lDateUpdated'):
            group_data['extras'].append({'key': 'ocean_expert_updated', 'value': oe_institute['lDateUpdated']})
    
    # Add sync metadata
    group_data['extras'].append({'key': 'data_source', 'value': 'obis_oceanexpert'})
    group_data['extras'].append({'key': 'data_quality', 'value': data_source_detail})
    group_data['extras'].append({'key': 'sync_date', 'value': time.strftime('%Y-%m-%d')})
    
    return group_data

def sync_obis_institutions():
    """Main function to sync OBIS institutions with Ocean Expert enrichment"""
    print("Starting OBIS institutions synchronization with Ocean Expert...")
    print("=" * 60)
    
    # Check configuration
    if not CKAN_TOKEN:
        print("✗ Error: Please set the CKAN_TOKEN environment variable")
        print("Usage: CKAN_TOKEN=your-token python3 obis_institutions_sync.py")
        return False
    
    # Fetch data
    institutions = fetch_obis_institutions()
    if not institutions:
        print("✗ No institutions found or API error")
        return False
    
    print("Fetching existing CKAN groups...")
    existing_groups = get_existing_groups()
    
    # Check for resume file
    resume_file = 'institutions_sync_progress.json'
    start_index = 0
    if os.path.exists(resume_file):
        try:
            with open(resume_file, 'r') as f:
                progress = json.load(f)
                start_index = progress.get('last_processed', 0)
                print(f"Resuming from institution {start_index + 1}")
        except:
            print("Could not read resume file, starting from beginning")
    
    # Process each institution
    print(f"\nProcessing {len(institutions)} OBIS institutions with Ocean Expert IDs...")
    print(f"Starting from index {start_index}")
    created = updated = failed = ocean_expert_enriched = skipped = 0
    
    for i, institution in enumerate(institutions[start_index:], start_index + 1):
        oe_id = institution.get('id')
        
        try:
            # Determine group name and check for conflicts BEFORE fetching Ocean Expert data
            inst_name = institution.get('name', f'Institution {institution.get("id")}')
            preliminary_slug = slugify(inst_name)
            
            print(f"[{i}/{len(institutions)}] Processing: {inst_name} (OE ID: {oe_id})")
            print(f"  Preliminary group slug: {preliminary_slug}")
            
            # Check if this group already exists (using preliminary slug)
            if preliminary_slug in existing_groups:
                print(f"  Found existing group: {preliminary_slug}")
                
                # For existing groups, still fetch Ocean Expert data to update with latest info
                ocean_expert_data = None
                if oe_id:
                    print(f"  Fetching Ocean Expert data for update...")
                    ocean_expert_data = fetch_ocean_expert_institution(oe_id)
                    if ocean_expert_data:
                        ocean_expert_enriched += 1
                        print(f"  ✓ Retrieved Ocean Expert data")
                    else:
                        print(f"  ! No Ocean Expert data available")
                    time.sleep(1)  # Rate limiting
                
                if update_group(existing_groups[preliminary_slug], institution, ocean_expert_data):
                    updated += 1
                else:
                    failed += 1
            else:
                print(f"  Group doesn't exist, will create new one")
                
                # Fetch Ocean Expert data for new groups
                ocean_expert_data = None
                if oe_id:
                    print(f"  Fetching Ocean Expert data for ID {oe_id}...")
                    ocean_expert_data = fetch_ocean_expert_institution(oe_id)
                    if ocean_expert_data:
                        ocean_expert_enriched += 1
                        print(f"  ✓ Retrieved Ocean Expert data")
                        
                        # Re-calculate slug with Ocean Expert name if available
                        oe_institute = ocean_expert_data.get('institute', {})
                        if oe_institute.get('instName'):
                            final_slug = slugify(oe_institute['instName'])
                            print(f"  Final group slug (Ocean Expert): {final_slug}")
                            
                            # Check if the Ocean Expert name creates a conflict
                            if final_slug in existing_groups:
                                print(f"  ! Ocean Expert name creates conflict with existing group: {final_slug}")
                                print(f"  ! Will update existing group instead of creating new one")
                                if update_group(existing_groups[final_slug], institution, ocean_expert_data):
                                    updated += 1
                                else:
                                    failed += 1
                                print()
                                continue
                        else:
                            final_slug = preliminary_slug
                    else:
                        print(f"  ! No Ocean Expert data available - will create linkage anyway")
                        final_slug = preliminary_slug
                    
                    time.sleep(1)  # Rate limiting
                else:
                    final_slug = preliminary_slug
                
                print(f"  Creating new group: {final_slug}")
                if create_group(institution, ocean_expert_data):
                    created += 1
                    # Add to existing_groups to prevent future conflicts
                    existing_groups[final_slug] = {'name': final_slug}
                else:
                    failed += 1
            
            # Save progress every 10 institutions
            if i % 10 == 0:
                with open(resume_file, 'w') as f:
                    json.dump({'last_processed': i}, f)
            
            print()  # Blank line for readability
            
        except KeyboardInterrupt:
            print(f"\n⚠️  Interrupted by user at institution {i}")
            print(f"Progress saved. Resume with the same command.")
            with open(resume_file, 'w') as f:
                json.dump({'last_processed': i - 1}, f)
            return False
            
        except Exception as e:
            print(f"  ✗ Unexpected error processing institution {i}: {e}")
            failed += 1
            continue
    
    # Clean up resume file on successful completion
    if os.path.exists(resume_file):
        os.remove(resume_file)
    
    # Summary
    print("=" * 60)
    print("Synchronization complete!")
    print(f"Created: {created}")
    print(f"Updated: {updated}")
    print(f"Failed: {failed}")
    print(f"Ocean Expert enriched: {ocean_expert_enriched}")
    print(f"Total processed: {len(institutions)}")
    print(f"Success rate: {((created + updated) / len(institutions) * 100):.1f}%")
    
    return failed == 0

if __name__ == "__main__":
    success = sync_obis_institutions()
    exit(0 if success else 1)
