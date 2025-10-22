import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckanext.obis_theme import helpers
import click
import requests
import re
import json
import time


class ObisThemePlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IClick)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, "templates")
        toolkit.add_public_directory(config_, "public")
        toolkit.add_resource("assets", "obis_theme")
        

    def get_helpers(self):
        return {
            'dataset_type_class': helpers.dataset_type_class,
            'obis_get_product_type_stats': helpers.obis_get_product_type_stats,
            'obis_get_thematic_stats': helpers.obis_get_thematic_stats,
            'obis_get_recent_datasets': helpers.obis_get_recent_datasets,
        }

    # IClick
    
    def get_commands(self):
        return [obis]


@click.group()
def obis():
    """OBIS data synchronization commands"""
    pass

@obis.command('sync-nodes')
def sync_nodes():
    """Sync OBIS nodes as CKAN organizations"""
    from ckan import model
    from ckan.model import Group
    
    def slugify(text):
        text = text.lower()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[-\s]+', '-', text)
        return text.strip('-')
    
    click.echo("Fetching OBIS nodes...")
    try:
        response = requests.get("https://api.obis.org/v3/node", timeout=30)
        response.raise_for_status()
        nodes = response.json().get('results', [])
    except Exception as e:
        click.echo(f"Error fetching nodes: {e}", err=True)
        return
    
    click.echo(f"Processing {len(nodes)} OBIS nodes...")
    created = updated = 0
    
    for node in nodes:
        org_name = slugify(node['name'])
        
        # Check if organization exists
        existing = model.Session.query(Group).filter_by(name=org_name, type='organization').first()
        
        if existing:
            # Update
            existing.title = node['name']
            existing.description = node.get('description', '')
            click.echo(f"↻ Will update: {node['name']}")
            updated += 1
        else:
            # Create new
            org = Group(
                name=org_name,
                title=node['name'],
                description=node.get('description', ''),
                type='organization',
                is_organization=True
            )

            model.Session.add(org)
            click.echo(f"✓ Will create: {node['name']}")
            created += 1
    
    # Commit ALL at once at the end
    click.echo("\nCommitting all changes...")
    model.Session.flush()
    model.Session.commit()
    click.echo("Commit complete")
    
    click.echo("\n" + "=" * 50)
    click.echo(f"Created: {created}, Updated: {updated}")
    click.echo(f"Total: {len(nodes)}")
    
    # Verify with fresh query
    model.Session.expire_all()
    final_count = model.Session.query(Group).filter_by(type='organization').count()
    click.echo(f"\n✓ {final_count} organizations in database after commit")

@obis.command('sync-institutions')
@click.option('--limit', default=None, type=int, help='Limit number of institutions to process')
def sync_institutions(limit):
    """Sync OBIS institutions as CKAN groups (with Ocean Expert enrichment)"""
    
    def slugify(text):
        if not text:
            return "unknown-institution"
        import unicodedata
        text = unicodedata.normalize('NFKD', text)
        text = text.encode('ascii', 'ignore').decode('ascii')
        text = text.lower()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[-\s]+', '-', text)
        text = text.strip('-')
        if len(text) > 100:
            text = text[:100]
        return text or "unknown-institution"
    
    context = {'user': 'ckan_admin', 'ignore_auth': True}
    
    # Fetch OBIS institutions
    click.echo("Fetching OBIS institutions...")
    try:
        response = requests.get("https://api.obis.org/v3/institute", 
                              params={'size': 10000}, timeout=120)
        response.raise_for_status()
        data = response.json()
        institutions = data.get('results', [])
        
        # Filter for those with Ocean Expert IDs
        institutions = [i for i in institutions if i.get('id') is not None]
        
        if limit:
            institutions = institutions[:limit]
            
        click.echo(f"Found {len(institutions)} institutions with Ocean Expert IDs")
    except Exception as e:
        click.echo(f"Error fetching institutions: {e}", err=True)
        return
    
    created = updated = failed = enriched = 0
    
    for i, inst in enumerate(institutions, 1):
        inst_name = inst.get('name', f'Institution {inst.get("id")}')
        oe_id = inst.get('id')
        
        click.echo(f"[{i}/{len(institutions)}] Processing: {inst_name}")
        
        # Fetch Ocean Expert data
        ocean_expert_data = None
        if oe_id:
            try:
                oe_response = requests.get(
                    f"https://oceanexpert.org/api/v1/institute/{oe_id}.json",
                    timeout=30
                )
                oe_response.raise_for_status()
                ocean_expert_data = oe_response.json()
                enriched += 1
                time.sleep(1)  # Rate limiting
            except Exception as e:
                click.echo(f"  Warning: Could not fetch Ocean Expert data: {e}")
        
        # Build group data
        oe_institute = ocean_expert_data.get('institute') if ocean_expert_data else None
        
        if oe_institute and oe_institute.get('instName'):
            title = oe_institute['instName'].strip()
        else:
            title = inst_name.strip()
        
        group_name = slugify(title)
        
        group_data = {
            'name': group_name,
            'title': title,
            'description': oe_institute.get('instAddress', '') if oe_institute else '',
            'type': 'group',
            'extras': [
                {'key': 'ocean_expert_id', 'value': str(oe_id)},
                {'key': 'obis_institution_code', 'value': inst.get('code', '')},
                {'key': 'data_source', 'value': 'obis_oceanexpert'}
            ]
        }
        
        # Add Ocean Expert metadata if available
        if oe_institute:
            if oe_institute.get('instUrl'):
                group_data['extras'].append({'key': 'website', 'value': oe_institute['instUrl']})
            if oe_institute.get('country'):
                group_data['extras'].append({'key': 'country', 'value': oe_institute['country']})
            if oe_institute.get('instLogo'):
                group_data['image_url'] = oe_institute['instLogo']
        
        try:
            toolkit.get_action('group_create')(context, group_data)
            click.echo(f"  ✓ Created: {title}")
            created += 1
        except toolkit.ValidationError as e:
            if 'name' in str(e):
                try:
                    toolkit.get_action('group_update')(context, group_data)
                    click.echo(f"  ↻ Updated: {title}")
                    updated += 1
                except Exception as e2:
                    click.echo(f"  ✗ Failed to update: {e2}", err=True)
                    failed += 1
            else:
                click.echo(f"  ✗ Failed to create: {e}", err=True)
                failed += 1
    
    click.echo("\n" + "=" * 50)
    click.echo(f"Created: {created}, Updated: {updated}, Failed: {failed}")
    click.echo(f"Ocean Expert enriched: {enriched}")
    click.echo(f"Total: {len(institutions)}")