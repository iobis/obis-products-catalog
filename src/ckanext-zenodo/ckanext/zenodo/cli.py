"""
CKAN CLI commands for Zenodo harvesting
"""
import click
import requests
from datetime import datetime
import ckan.plugins.toolkit as toolkit


@click.group()
def zenodo():
    """Zenodo harvesting commands"""
    pass


@zenodo.command()
@click.option('--registry', default='/srv/app/src_extensions/ckanext-zenodo/ckanext/zenodo/config/zenodo_dois.txt',
              help='Path to DOI registry file')
@click.option('--org', default='obis-community',
              help='Organization to import datasets into')
def harvest(registry, org):
    """Harvest datasets from Zenodo DOI registry"""
    
    click.echo(f"=== Zenodo DOI Harvest ===")
    click.echo(f"Registry: {registry}")
    click.echo(f"Target org: {org}\n")
    
    # Load DOIs from registry
    dois = load_doi_registry(registry)
    click.echo(f"Found {len(dois)} DOIs to check\n")
    
    stats = {
        'found': 0,
        'imported': 0,
        'updated': 0,
        'failed': 0
    }
    
    for doi in dois:
        click.echo(f"Checking: {doi}")
        
        try:
            # Check if dataset exists
            dataset = find_dataset_by_doi(doi)
            
            if dataset:
                # Existing dataset - check for updates
                click.echo(f"  ✓ Found: {dataset['title']}")
                click.echo(f"    Last modified: {dataset.get('metadata_modified', 'Unknown')}")
                
                # Check if Zenodo has updates
                zenodo_modified = get_zenodo_last_modified(doi)
                if zenodo_modified:
                    click.echo(f"    Zenodo updated: {zenodo_modified}")
                    if should_update(dataset.get('metadata_modified'), zenodo_modified):
                        click.echo(f"    → Updating...")
                        if update_dataset(dataset['id'], doi, org):
                            stats['updated'] += 1
                            click.echo(f"    ✓ Updated successfully")
                        else:
                            stats['failed'] += 1
                            click.echo(f"    ✗ Update failed")
                    else:
                        click.echo(f"    → No update needed")
                stats['found'] += 1
            else:
                # New dataset - import it
                click.echo(f"  → Not in CKAN, importing...")
                if import_dataset(doi, org):
                    stats['imported'] += 1
                    click.echo(f"    ✓ Imported successfully")
                else:
                    stats['failed'] += 1
                    click.echo(f"    ✗ Import failed")
        
        except Exception as e:
            click.echo(f"  ✗ Error: {str(e)}")
            stats['failed'] += 1
        
        click.echo()
    
    # Summary
    click.echo(f"\nSummary:")
    click.echo(f"  Found: {stats['found']}/{len(dois)} datasets in CKAN")
    click.echo(f"  Imported: {stats['imported']} new datasets")
    click.echo(f"  Updated: {stats['updated']} datasets")
    click.echo(f"  Failed: {stats['failed']} operations")


def load_doi_registry(registry_file):
    """Load DOIs from registry file"""
    dois = []
    try:
        with open(registry_file, 'r') as f:
            for line in f:
                doi = line.strip()
                if doi and not doi.startswith('#'):
                    dois.append(doi)
    except FileNotFoundError:
        click.echo(f"Error: Registry file not found: {registry_file}", err=True)
        raise click.Abort()
    return dois


def find_dataset_by_doi(doi):
    """Search for existing dataset by DOI in canonical_id field"""
    try:
        context = {'ignore_auth': True}
        
        # Search by canonical_id (which should contain the DOI URL)
        result = toolkit.get_action('package_search')(
            context,
            {'q': f'canonical_id:"{doi}"', 'rows': 1}
        )
        
        if result['count'] > 0:
            return result['results'][0]
        
        # Fallback: search by url field
        result = toolkit.get_action('package_search')(
            context,
            {'q': f'url:"{doi}"', 'rows': 1}
        )
        
        if result['count'] > 0:
            return result['results'][0]
        
        return None
    
    except Exception as e:
        click.echo(f"    Search error: {str(e)}", err=True)
        return None


def get_zenodo_last_modified(doi):
    """Get last modified date from Zenodo record"""
    try:
        if 'zenodo' not in doi.lower():
            return None
        
        # Extract record ID
        zenodo_id = doi.split('/')[-1]
        if zenodo_id.startswith('zenodo.'):
            zenodo_id = zenodo_id.replace('zenodo.', '')
        
        url = f"https://zenodo.org/api/records/{zenodo_id}"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data.get('updated')
    
    except Exception as e:
        click.echo(f"    Zenodo API error: {str(e)}", err=True)
        return None


def should_update(ckan_modified, zenodo_modified):
    """Check if dataset should be updated based on modification dates"""
    if not zenodo_modified:
        return False
    
    try:
        ckan_dt = datetime.fromisoformat(ckan_modified.replace('Z', '+00:00'))
        zenodo_dt = datetime.fromisoformat(zenodo_modified.replace('Z', '+00:00'))
        return zenodo_dt > ckan_dt
    except:
        return False


def import_dataset(doi, org):
    """Import new dataset using doi_import actions"""
    try:
        context = {'ignore_auth': True, 'user': 'default'}
        
        # Fetch metadata from DOI
        metadata = toolkit.get_action('doi_fetch_metadata')(
            context,
            {'doi_url': doi}
        )
        
        # Create dataset
        dataset = toolkit.get_action('doi_create_dataset')(
            context,
            {
                'metadata': metadata,
                'owner_org': org,
                'contributing_organizations': []
            }
        )
        
        return True
    
    except Exception as e:
        click.echo(f"    Import error: {str(e)}", err=True)
        return False


def update_dataset(dataset_id, doi, org):
    """Update existing dataset with fresh metadata"""
    try:
        context = {'ignore_auth': True, 'user': 'default'}
        
        # Fetch fresh metadata
        metadata = toolkit.get_action('doi_fetch_metadata')(
            context,
            {'doi_url': doi}
        )
        
        # Preserve the existing dataset ID and name
        metadata['id'] = dataset_id
        
        # Get existing dataset to preserve name
        existing = toolkit.get_action('package_show')(
            context,
            {'id': dataset_id}
        )
        metadata['name'] = existing['name']
        metadata['owner_org'] = org
        
        # Update the dataset
        toolkit.get_action('package_update')(context, metadata)
        
        return True
    
    except Exception as e:
        click.echo(f"    Update error: {str(e)}", err=True)
        return False
    
@zenodo.command()
def init_vocabularies():
    """Initialize controlled vocabularies for product types and thematics"""
    
    click.echo("=== Initializing Vocabularies ===\n")
    
    vocabularies = {
        'product_types': [
            'Raw Dataset',
            'Derived Dataset',
            'Model Output',
            'Report',
            'Presentation',
            'Data Visualization',
            'Map',
            'Workflow',
            'Software',
            'Standard'
        ],
        'thematics': [
            'Biodiversity',
            'Climate Change',
            'Ocean Acidification',
            'Marine Protected Areas',
            'Fisheries',
            'Pollution',
            'Coastal Management',
            'Deep Sea',
            'Coral Reefs',
            'Species Distribution'
        ]
    }
    
    context = {'ignore_auth': True}
    
    for vocab_name, tags in vocabularies.items():
        click.echo(f"Creating vocabulary: {vocab_name}")
        
        try:
            # Check if vocabulary exists
            try:
                toolkit.get_action('vocabulary_show')(context, {'id': vocab_name})
                click.echo(f"  → Vocabulary '{vocab_name}' already exists, skipping")
                continue
            except:
                pass
            
            # Create vocabulary
            vocab = toolkit.get_action('vocabulary_create')(
                context,
                {'name': vocab_name}
            )
            click.echo(f"  ✓ Created vocabulary: {vocab_name}")
            
            # Add tags to vocabulary
            for tag_name in tags:
                toolkit.get_action('tag_create')(
                    context,
                    {'name': tag_name, 'vocabulary_id': vocab['id']}
                )
                click.echo(f"    + {tag_name}")
            
            click.echo(f"  ✓ Added {len(tags)} tags to {vocab_name}\n")
            
        except Exception as e:
            click.echo(f"  ✗ Error creating {vocab_name}: {str(e)}\n", err=True)
    
    click.echo("Done!")