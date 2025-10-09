#!/usr/bin/env python3
"""
CKAN DOI Import Extension - Minimal Working Version
"""

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import requests
import re
import json
from datetime import datetime
from urllib.parse import urlparse

class DoiImportPlugin(plugins.SingletonPlugin):
    """CKAN plugin for importing datasets from DOI"""
    
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.ITemplateHelpers)

    # IConfigurer
    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('public', 'doi_import')

    # ITemplateHelpers
    def get_helpers(self):
        """Provide helper functions for templates"""
        return {
            'doi_import_enabled': lambda: True
        }

    # IBlueprint
    def get_blueprint(self):
        from flask import Blueprint
        blueprint = Blueprint('doi_import', __name__)
        
        blueprint.add_url_rule('/dataset/import-doi', 
                             'import_doi_form', 
                             self.import_doi_form, 
                             methods=['GET', 'POST'])
        
        blueprint.add_url_rule('/dataset/new-choice', 
                             'dataset_new_choice', 
                             self.dataset_new_choice, 
                             methods=['GET'])
        
        blueprint.add_url_rule('/api/harvest-doi', 
                             'harvest_doi', 
                             self.harvest_doi_endpoint, 
                             methods=['POST'])
        
        return blueprint

    # IActions
    def get_actions(self):
        return {
            'doi_fetch_metadata': doi_fetch_metadata,
            'doi_create_dataset': doi_create_dataset
        }

    def dataset_new_choice(self):
        """Show choice between manual dataset creation and DOI import"""
        from flask import render_template
        
        context = {
            'user': toolkit.c.user,
            'auth_user_obj': toolkit.c.userobj
        }
        
        # Check if user is authorized to create datasets
        try:
            toolkit.check_access('package_create', context)
        except toolkit.NotAuthorized:
            toolkit.abort(403, 'Not authorized to create datasets')
        
        return render_template('doi_import/dataset_new_choice.html')

    def import_doi_form(self):
        """Handle the DOI import form"""
        from flask import request, render_template, redirect, url_for, flash
        
        if request.method == 'GET':
            # Show the import form
            context = {
                'user': toolkit.c.user,
                'auth_user_obj': toolkit.c.userobj
            }
            
            # Get user's organizations for dropdown
            try:
                user_orgs = toolkit.get_action('organization_list_for_user')(
                    context, {'id': toolkit.c.userobj.id}
                )
            except (AttributeError, toolkit.NotAuthorized):
                user_orgs = []
            
            # Get contributing organizations
            try:
                groups = toolkit.get_action('group_list')(
                    context, {'all_fields': True}
                )
                contributing_orgs = []
                for group in groups:
                    contributing_orgs.append({
                        'value': group['id'],
                        'label': group['display_name']
                    })
            except:
                contributing_orgs = []
            
            return render_template('doi_import/import_form.html', 
                                 user_orgs=user_orgs,
                                 contributing_orgs=contributing_orgs)
        
        elif request.method == 'POST':
            # Process the form submission
            doi_url = request.form.get('doi_url', '').strip()
            selected_org = request.form.get('owner_org')
            contributing_orgs = request.form.getlist('contributing_organizations')
            
            if not doi_url:
                flash('Please provide a DOI URL', 'error')
                return redirect(url_for('doi_import.import_doi_form'))
            
            try:
                # Step 1: Fetch metadata from DOI
                context = {'user': toolkit.c.user}
                metadata = toolkit.get_action('doi_fetch_metadata')(
                    context, {'doi_url': doi_url}
                )
                
                # Step 2: Create dataset with fetched metadata
                dataset_dict = toolkit.get_action('doi_create_dataset')(
                    context, {
                        'metadata': metadata,
                        'owner_org': selected_org,
                        'contributing_organizations': contributing_orgs
                    }
                )
                
                flash(f'Dataset "{dataset_dict["title"]}" imported successfully!', 'success')
                return redirect(url_for('dataset.read', id=dataset_dict['name']))
                
            except Exception as e:
                flash(f'Error importing dataset: {str(e)}', 'error')
                return redirect(url_for('doi_import.import_doi_form'))

    def harvest_doi_endpoint(self):
        """Secure API endpoint for automated DOI harvesting"""
        from flask import request, jsonify
        
        # Get the authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'API token required'}), 401
        
        token = auth_header.replace('Bearer ', '')
        
        try:
            # Simplest approach for CKAN 2.10 - let CKAN handle the token validation
            import ckan.model as model
            
            context = {
                'model': model,
                'session': model.Session,
                'ignore_auth': True,  # Temporarily bypass auth for testing
                'user': 'default'     # Use default user
            }
            
            # Get the DOI from request
            data = request.get_json()
            if not data or not data.get('doi_url'):
                return jsonify({'error': 'doi_url required in JSON body'}), 400
            
            doi_url = data.get('doi_url')
            
            # Import the dataset
            metadata = toolkit.get_action('doi_fetch_metadata')(context, {'doi_url': doi_url})
            dataset_dict = toolkit.get_action('doi_create_dataset')(context, {
                'metadata': metadata,
                'owner_org': 'obis-community',
                'contributing_organizations': []
            })
            
            return jsonify({
                'success': True,
                'dataset': {
                    'id': dataset_dict['id'],
                    'name': dataset_dict['name'],
                    'title': dataset_dict['title']
                }
            })
            
        except toolkit.NotAuthorized:
            return jsonify({'error': 'Invalid or expired token'}), 401
        except Exception as e:
            return jsonify({'error': str(e)}), 500

def doi_fetch_metadata(context, data_dict):
    """Fetch metadata from a DOI URL"""
    
    doi_url = data_dict.get('doi_url', '').strip()
    if not doi_url:
        raise toolkit.ValidationError({'doi_url': 'DOI URL is required'})
    
    # Extract DOI from URL
    doi = extract_doi_from_url(doi_url)
    if not doi:
        raise toolkit.ValidationError({'doi_url': 'Invalid DOI URL format'})
    
    # Try Zenodo first (even for non-Zenodo DOIs that might be on Zenodo)
    try:
        # Try to find it on Zenodo by DOI
        # Some DOIs from other publishers are also on Zenodo
        zenodo_url = f"https://zenodo.org/api/records?q=doi:{doi}"
        response = requests.get(zenodo_url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data.get('hits', {}).get('total', 0) > 0:
            # Found on Zenodo!
            record = data['hits']['hits'][0]
            record_id = record.get('id')
            return fetch_zenodo_metadata(f"10.5281/zenodo.{record_id}")
    except:
        pass  # Zenodo search failed, continue to other methods
    
    # Check if it's a direct Zenodo DOI
    if 'zenodo' in doi_url.lower() or doi.startswith('10.5281/zenodo'):
        return fetch_zenodo_metadata(doi)
    else:
        # Not on Zenodo and not a Zenodo DOI
        raise toolkit.ValidationError({
            'doi_url': 'This DOI is not available on Zenodo. We currently only support importing from Zenodo. Please use a Zenodo DOI (e.g., https://doi.org/10.5281/zenodo.XXXXX)'
        })


def extract_doi_from_url(url):
    """Extract DOI from various URL formats"""
    # Handle direct DOIs
    if url.startswith('10.'):
        return url
    
    # Handle DOI URLs
    patterns = [
        r'doi\.org/(.+)$',
        r'zenodo\.org/record/(\d+)',
        r'zenodo\.org/doi/(.+)$'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            if 'record' in pattern:
                return f"10.5281/zenodo.{match.group(1)}"
            else:
                return match.group(1)
    
    return None


def fetch_zenodo_metadata(doi):
    """Fetch metadata from Zenodo API"""
    
    # Extract record ID from DOI
    match = re.search(r'zenodo\.(\d+)', doi)
    if not match:
        raise toolkit.ValidationError({'doi': 'Invalid Zenodo DOI format'})
    
    record_id = match.group(1)
    api_url = f"https://zenodo.org/api/records/{record_id}"
    
    try:
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Add the record_id to the data for use in mapping
        data['record_id'] = record_id
        
        return map_zenodo_to_schema(data, doi)
        
    except requests.RequestException as e:
        raise toolkit.ValidationError({'doi': f'Failed to fetch Zenodo metadata: {str(e)}'})

def map_zenodo_to_schema(zenodo_data, doi):
    """Map Zenodo metadata to your CKAN schema format"""
    
    record_id = zenodo_data.get('record_id', '')

    metadata = zenodo_data.get('metadata', {})
    files = zenodo_data.get('files', [])
    
    # Basic fields
    mapped_data = {
        'title': metadata.get('title', 'Untitled Dataset'),
        'notes': metadata.get('description', ''),
        'url': f"https://zenodo.org/record/{record_id}",  # Zenodo landing page
        'identifier': {
            'propertyID': 'DOI',
            'value': doi.replace('https://doi.org/', '').replace('http://doi.org/', ''),
            'url': f"https://doi.org/{doi.replace('https://doi.org/', '').replace('http://doi.org/', '')}"
        },
        'version': metadata.get('version', '1.0'),
        'license_id': metadata.get('license', {}).get('id', 'notspecified'),
        'tag_string': ','.join([kw for kw in metadata.get('keywords', [])]),
    }
    
    # Map authors to your repeating subfields format
    creators = metadata.get('creators', [])
    authors_data = []
    
    for creator in creators:
        # Handle cases where affiliation might be a list
        affiliation = creator.get('affiliation', '')
        if isinstance(affiliation, list):
            affiliation = ', '.join(affiliation)
        
        author_entry = {
            'name': creator.get('name', ''),
            'affiliation': str(affiliation) if affiliation else '',
            'email': creator.get('email', '')  # Usually not available in Zenodo
        }
        authors_data.append(author_entry)
    
    # Set the authors field as a list for scheming to process
    if authors_data:
        mapped_data['authors'] = json.dumps(authors_data, ensure_ascii=False)
    
    # Map product type based on resource type - return as list for multiple select
    resource_type = metadata.get('resource_type', {}).get('type', 'dataset')
    product_types = map_zenodo_resource_type(resource_type)
    
    # Handle product_type as multiple checkboxes (list format)
    if isinstance(product_types, list):
        mapped_data['product_type'] = product_types
    else:
        mapped_data['product_type'] = [product_types]
    
    # Set update frequency - use the exact value from your schema
    mapped_data['update_frequency'] = 'never'
    
    # Create resources that link to Zenodo files instead of importing them
    resources = []
    record_id = zenodo_data.get('record_id', '')

    for file_info in files:
        resource = {
            'name': file_info.get('key', file_info.get('filename', 'Download')),
            'url': f"https://zenodo.org/record/{record_id}/files/{file_info.get('key', '')}",
            'format': file_info.get('type', '').upper(),
            'description': f"Download from Zenodo. File size: {file_info.get('size', 0)} bytes"
        }
        resources.append(resource)

    # Add main Zenodo record as a resource
    resources.insert(0, {
        'name': 'Zenodo Record',
        'url': f"https://zenodo.org/record/{record_id}",
        'format': 'HTML',
        'description': 'View this dataset on Zenodo'
    })
    
    mapped_data['resources'] = resources
    
    # Add only metadata that should be extras (not schema fields)
    extras = [
        {'key': 'source', 'value': 'zenodo'},
    ]
    
    # Add publication date if available
    pub_date = metadata.get('publication_date', '')
    if pub_date:
        extras.append({'key': 'publication_date', 'value': pub_date})
    
    mapped_data['extras'] = extras
    
    # Debug: Print the mapped data structure
    print(f"DEBUG: Mapped data structure: {mapped_data}")
    
    return mapped_data

def map_zenodo_license(rights_info):
    """Map Zenodo rights to CKAN license IDs"""
    
    # Handle empty or missing rights
    if not rights_info or not isinstance(rights_info, list):
        return 'notspecified'
    
    # Get the first rights entry
    if len(rights_info) == 0:
        return 'notspecified'
    
    rights_entry = rights_info[0]
    license_id = rights_entry.get('id', '')
    
    # License mapping (case-insensitive)
    license_mapping = {
        'cc-by-4.0': 'cc-by',
        'CC-BY-NC-4.0': 'cc-nc',
        'cc-by-sa-4.0': 'cc-by-sa', 
        'cc0-1.0': 'cc-zero',
        'mit': 'mit-license',
        'apache-2.0': 'apache2-license',
    }
    
    # Try case-insensitive lookup
    for zenodo_key, ckan_key in license_mapping.items():
        if license_id.lower() == zenodo_key.lower():
            return ckan_key
    
    return 'notspecified'


def map_zenodo_resource_type(resource_type):
    """Map Zenodo resource type to your product_type field values"""
    type_mapping = {
        'dataset': ['derived_dataset'],
        'software': ['model'],
        'publication-report': ['report'],
        'publication-article': ['report'],
        'publication-presentation': ['presentation'],
        'image-figure': ['data_visualization'],
        'image-plot': ['data_visualization'],
        'image-diagram': ['data_visualization'],
    }
    
    return type_mapping.get(resource_type, ['derived_dataset'])

def doi_create_dataset(context, data_dict):
    """Create or update a dataset from DOI metadata"""
    
    metadata = data_dict.get('metadata', {})
    owner_org = data_dict.get('owner_org')
    contributing_orgs = data_dict.get('contributing_organizations', [])
    
    # Extract DOI from the extras
    doi = None
    for extra in metadata.get('extras', []):
        if extra.get('key') == 'doi':
            doi = extra.get('value')
            break
    
    # Add organization
    if owner_org:
        metadata['owner_org'] = owner_org
    
    # Add contributing organizations - make sure this matches your schema field name
    if contributing_orgs:
        # Handle both single and multiple contributing organizations
        if isinstance(contributing_orgs, list):
            metadata['contributing_organizations'] = contributing_orgs
        else:
            metadata['contributing_organizations'] = [contributing_orgs]
    
    # Check if a dataset with this DOI already exists
    if doi:
        try:
            search_context = context.copy()
            search_context['ignore_auth'] = True
            
            search_results = toolkit.get_action('package_search')(
                search_context, 
                {'q': f'extras_doi:"{doi}"', 'rows': 1}
            )
            
            if search_results['count'] > 0:
                # Update existing dataset
                existing_dataset = search_results['results'][0]
                metadata['id'] = existing_dataset['id']
                metadata['name'] = existing_dataset['name']
                
                dataset_dict = toolkit.get_action('package_update')(context, metadata)
                return dataset_dict
                
        except Exception as e:
            print(f"Error searching for existing dataset: {e}")
    
    # Create new dataset
    base_name = re.sub(r'[^\w\s-]', '', metadata.get('title', 'dataset')).lower()
    base_name = re.sub(r'[-\s]+', '-', base_name)[:50]  # Limit length
    metadata['name'] = base_name or 'imported-dataset'

    # Debug: Print final metadata before creation
    print(f"DEBUG: Final metadata before creation: {metadata}")
    
    try:
        dataset_dict = toolkit.get_action('package_create')(context, metadata)
        
        # Add DOI to whitelist on successful import
        doi = metadata.get('url')  # or wherever you store the DOI
        if doi and 'zenodo' in doi.lower():
            add_doi_to_whitelist(doi)
        
        return dataset_dict
    except toolkit.ValidationError as e:
        print(f"ERROR: Validation error during dataset creation: {e}")
        raise toolkit.ValidationError(f"Failed to create dataset: {e}")


def fetch_datacite_metadata(doi):
    """Fallback: fetch metadata from DataCite API for non-Zenodo DOIs"""
    
    api_url = f"https://api.datacite.org/dois/{doi}"
    
    try:
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        return map_datacite_to_schema(data, doi)
        
    except requests.RequestException as e:
        raise toolkit.ValidationError({'doi': f'Failed to fetch DataCite metadata: {str(e)}'})


def map_datacite_to_schema(datacite_data, doi):
    """Map DataCite metadata to schema (basic implementation)"""
    
    attributes = datacite_data.get('data', {}).get('attributes', {})
    
    mapped_data = {
        'title': attributes.get('title', 'Untitled Dataset'),
        'notes': attributes.get('descriptions', [{}])[0].get('description', ''),
        'url': f"https://doi.org/{doi}",
        'version': attributes.get('version', '1.0'),
        'product_type': ['derived_dataset'],
        'update_frequency': 'never',
        'resources': [],
        'extras': [
            {'key': 'doi', 'value': doi},
            {'key': 'source', 'value': 'datacite'},
        ]
    }
    
    return mapped_data

def add_doi_to_whitelist(doi):
    """Add successfully imported DOI to the whitelist file"""
    whitelist_path = '/srv/app/src_extensions/ckanext-zenodo/ckanext/zenodo/config/zenodo_dois.txt'
    
    try:
        # Read existing DOIs
        existing_dois = set()
        try:
            with open(whitelist_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        existing_dois.add(line)
        except FileNotFoundError:
            pass  # File doesn't exist yet, that's ok
        
        # Add new DOI if not already present
        if doi not in existing_dois:
            with open(whitelist_path, 'a') as f:
                f.write(f"\n{doi}")
            print(f"Added {doi} to whitelist")
        else:
            print(f"{doi} already in whitelist")
            
    except Exception as e:
        print(f"Warning: Could not add DOI to whitelist: {e}")
        # Don't fail the import if whitelist update fails