"""
CKAN CLI commands for DOI harvesting and catalog management.
"""
import click
import csv
import io
import re
from datetime import datetime

import ckan.plugins.toolkit as toolkit
from ckanext.doi_import.plugin import _is_blacklisted
from ckanext.doi_import.mappers.base import detect_source


@click.group()
def doi_import():
    """DOI import and catalog management commands."""
    pass


@doi_import.command()
@click.option('--registry', default='/srv/app/catalog_whitelist.csv',
              help='Path to DOI registry CSV file')
@click.option('--org', default='obis-community',
              help='Organization to import datasets into')
def harvest(registry, org):
    """Harvest datasets from DOI registry CSV."""

    click.echo(f"=== DOI Harvest ===")
    click.echo(f"Registry: {registry}")
    click.echo(f"Target org: {org}\n")

    dois = _load_doi_registry(registry)
    click.echo(f"Found {len(dois)} DOIs to check\n")

    stats = {
        'found': 0,
        'imported': 0,
        'updated': 0,
        'failed': 0,
        'skipped': 0,
    }

    for doi in dois:
        click.echo(f"Checking: {doi}")

        # Check blacklist
        blacklist_reason = _is_blacklisted(doi)
        if blacklist_reason:
            click.echo(f"  ⊘ Blacklisted: {blacklist_reason}")
            stats['skipped'] += 1
            continue

        try:
            dataset = _find_dataset_by_doi(doi)

            if dataset:
                click.echo(f"  ✓ Found: {dataset['title']}")
                click.echo(f"    Last modified: {dataset.get('metadata_modified', 'Unknown')}")

                source = detect_source(doi)
                last_modified = _get_source_last_modified(doi, source)

                if last_modified:
                    click.echo(f"    Source updated: {last_modified}")
                    if _should_update(dataset.get('metadata_modified'), last_modified):
                        click.echo(f"    → Updating...")
                        if _update_dataset(dataset['id'], doi, org):
                            stats['updated'] += 1
                            click.echo(f"    ✓ Updated successfully")
                        else:
                            stats['failed'] += 1
                            click.echo(f"    ✗ Update failed")
                    else:
                        click.echo(f"    → No update needed")
                stats['found'] += 1
            else:
                click.echo(f"  → Not in CKAN, importing...")
                if _import_dataset(doi, org):
                    stats['imported'] += 1
                    click.echo(f"    ✓ Imported successfully")
                else:
                    stats['failed'] += 1
                    click.echo(f"    ✗ Import failed")

        except Exception as e:
            click.echo(f"  ✗ Error: {str(e)}")
            stats['failed'] += 1

        click.echo()

    click.echo(f"\nSummary:")
    click.echo(f"  Found: {stats['found']}/{len(dois)} datasets in CKAN")
    click.echo(f"  Imported: {stats['imported']} new datasets")
    click.echo(f"  Updated: {stats['updated']} datasets")
    click.echo(f"  Failed: {stats['failed']} operations")
    click.echo(f"  Skipped: {stats['skipped']} blacklisted")


@doi_import.command()
@click.option('--output', default=None,
              help='Output file path (default: stdout)')
def export_whitelist(output):
    """Export catalog whitelist as CSV (doi, title, source_url, catalog_url)."""

    click.echo("=== Exporting Catalog Whitelist ===", err=True)

    context = {'ignore_auth': True}
    site_url = toolkit.config.get('ckan.site_url', 'http://localhost:5000')

    result = toolkit.get_action('package_search')(
        context, {'rows': 10000, 'include_private': False}
    )

    datasets = result.get('results', [])
    click.echo(f"Found {len(datasets)} products", err=True)

    if output:
        f = open(output, 'w', newline='')
    else:
        f = io.StringIO()

    writer = csv.writer(f)
    writer.writerow(['doi', 'title', 'source_url', 'catalog_url'])

    for ds in sorted(datasets, key=lambda d: d.get('title', '')):
        extras = {e['key']: e['value'] for e in ds.get('extras', [])}
        source_url = ds.get('source_url') or extras.get('source_url') or ds.get('url') or ''

        canonical_id = ds.get('canonical_id', '')
        doi = canonical_id if canonical_id else ''

        catalog_url = f"{site_url}/dataset/{ds['name']}"
        writer.writerow([doi, ds.get('title', ''), source_url, catalog_url])

    if output:
        f.close()
        click.echo(f"Written to {output}", err=True)
    else:
        click.echo(f.getvalue())


# --- Helper functions ---

def _load_doi_registry(registry_file):
    """Load DOIs from registry CSV file."""
    dois = []
    try:
        with open(registry_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                doi = line.split(',')[0].strip()
                if doi == 'doi':
                    continue
                dois.append(doi)
    except FileNotFoundError:
        click.echo(f"Error: Registry file not found: {registry_file}", err=True)
        raise click.Abort()
    return dois


def _find_dataset_by_doi(doi):
    """Search for existing dataset by DOI in canonical_id field."""
    try:
        context = {'ignore_auth': True}

        result = toolkit.get_action('package_search')(
            context,
            {'q': f'canonical_id:"{doi}"', 'rows': 1}
        )
        if result['count'] > 0:
            return result['results'][0]

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


def _get_source_last_modified(doi, source):
    """Get last modified timestamp from the source repository."""
    if source == 'zenodo':
        from ckanext.doi_import.mappers.zenodo import get_last_modified
        return get_last_modified(doi)
    return None


def _should_update(ckan_modified, source_modified):
    """Check if dataset should be updated based on modification dates."""
    if not source_modified:
        return False
    try:
        ckan_dt = datetime.fromisoformat(ckan_modified.replace('Z', '+00:00'))
        source_dt = datetime.fromisoformat(source_modified.replace('Z', '+00:00'))
        return source_dt > ckan_dt
    except Exception:
        return False


def _import_dataset(doi, org):
    """Import a new dataset via doi_import actions."""
    try:
        context = {'ignore_auth': True, 'user': 'default'}
        metadata = toolkit.get_action('doi_fetch_metadata')(
            context, {'doi_url': doi}
        )
        toolkit.get_action('doi_create_dataset')(
            context,
            {
                'metadata': metadata,
                'owner_org': org,
                'contributing_organizations': [],
            }
        )
        return True
    except Exception as e:
        click.echo(f"    Import error: {str(e)}", err=True)
        return False


def _update_dataset(dataset_id, doi, org):
    """Update an existing dataset with fresh metadata."""
    try:
        context = {'ignore_auth': True, 'user': 'default'}
        metadata = toolkit.get_action('doi_fetch_metadata')(
            context, {'doi_url': doi}
        )
        existing = toolkit.get_action('package_show')(
            context, {'id': dataset_id}
        )
        metadata['id'] = dataset_id
        metadata['name'] = existing['name']
        toolkit.get_action('doi_create_dataset')(
            context,
            {
                'metadata': metadata,
                'owner_org': org,
                'contributing_organizations': [],
                'is_update': True,
            }
        )
        return True
    except Exception as e:
        click.echo(f"    Update error: {str(e)}", err=True)
        return False