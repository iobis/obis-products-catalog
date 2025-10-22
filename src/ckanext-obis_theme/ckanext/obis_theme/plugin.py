import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckanext.obis_theme import helpers
import click
import requests
import re
import json
import time
import os


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
        # Add 'node-' prefix to avoid conflicts with institution groups
        org_name = 'node-' + slugify(node['name'])
        
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
            click.echo(f"✓ Will create: {node['name']} (as {org_name})")
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
    from ckan import model
    from ckan.model import Group, GroupExtra
    import unicodedata
    
    def slugify(text):
        """Convert text to URL-friendly slug"""
        if not text:
            return "unknown-institution"
        text = unicodedata.normalize('NFKD', text)
        text = text.encode('ascii', 'ignore').decode('ascii')
        text = text.lower()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[-\s]+', '-', text)
        text = text.strip('-')
        if len(text) > 100:
            text = text[:100]
        return text or "unknown-institution"
    
    def fetch_ocean_expert_data(oe_id):
        """Fetch detailed institution data from Ocean Expert API"""
        try:
            response = requests.get(
                f"https://oceanexpert.org/api/v1/institute/{oe_id}.json",
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            return data if data and isinstance(data, dict) else None
        except Exception as e:
            click.echo(f"    Warning: Could not fetch Ocean Expert data for ID {oe_id}: {e}")
            return None
    
    def set_group_extras(group, extras_dict):
        """Set extras for a group"""
        # Remove existing extras for this group
        model.Session.query(GroupExtra).filter_by(group_id=group.id).delete()
        
        # Add new extras
        for key, value in extras_dict.items():
            extra = GroupExtra(group_id=group.id, key=key, value=str(value))
            model.Session.add(extra)
    
    # Main sync logic
    click.echo("Starting OBIS institutions synchronization with Ocean Expert...")
    click.echo("=" * 60)
    
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
        click.echo(f"Found {len(institutions)} institutions with Ocean Expert IDs")
        
        if limit:
            institutions = institutions[:limit]
            click.echo(f"Limited to {len(institutions)} institutions")
            
    except Exception as e:
        click.echo(f"Error fetching institutions: {e}", err=True)
        return
    
    # Process institutions
    click.echo(f"\nProcessing {len(institutions)} institutions...")
    created = updated = failed = enriched = 0
    
    for i, inst in enumerate(institutions, 1):
        inst_name = inst.get('name', f'Institution {inst.get("id")}')
        oe_id = inst.get('id')
        
        try:
            preliminary_slug = slugify(inst_name)
            click.echo(f"[{i}/{len(institutions)}] Processing: {inst_name} (OE ID: {oe_id})")
            
            # Fetch Ocean Expert data
            ocean_expert_data = None
            if oe_id:
                ocean_expert_data = fetch_ocean_expert_data(oe_id)
                if ocean_expert_data:
                    enriched += 1
                    click.echo(f"  ✓ Retrieved Ocean Expert data")
                time.sleep(1)  # Rate limiting
            
            # Determine final title and slug
            oe_institute = ocean_expert_data.get('institute') if ocean_expert_data else None
            
            if oe_institute and oe_institute.get('instName'):
                data_quality = 'ocean_expert_full'
                title = oe_institute['instName'].strip()
                description = oe_institute.get('instAddress', '').strip()
                final_slug = slugify(title)
            elif ocean_expert_data:
                data_quality = 'ocean_expert_partial'
                title = inst_name.strip()
                description = ''
                final_slug = preliminary_slug
            else:
                data_quality = 'obis_only'
                title = inst_name.strip()
                description = ''
                final_slug = preliminary_slug
            
            # Check if group/organization with this name already exists (they share namespace)
            existing = model.Session.query(Group).filter_by(name=final_slug).first()
            
            if existing:
                if existing.type == 'group':
                    # Update existing group
                    existing.title = title
                    existing.description = description
                    click.echo(f"  ↻ Will update: {title}")
                    group = existing
                    updated += 1
                else:
                    # Name conflict with organization - skip
                    click.echo(f"  ⚠ Skipping: name '{final_slug}' already exists as {existing.type}")
                    failed += 1
                    continue
            else:
                # Create new group
                group = Group(
                    name=final_slug,
                    title=title,
                    description=description,
                    type='group',
                    is_organization=False
                )
                model.Session.add(group)
                model.Session.flush()  # Flush to get group.id for extras
                click.echo(f"  ✓ Will create: {title}")
                created += 1
            
            # Build extras dictionary
            extras = {
                'ocean_expert_id': str(oe_id),
                'obis_institution_code': inst.get('code', ''),
                'data_source': 'obis_oceanexpert',
                'data_quality': data_quality,
                'sync_date': time.strftime('%Y-%m-%d')
            }
            
            # Add comprehensive Ocean Expert metadata if available
            if oe_institute:
                if oe_institute.get('instUrl'):
                    extras['website'] = oe_institute['instUrl']
                if oe_institute.get('instEmail'):
                    extras['email'] = oe_institute['instEmail']
                if oe_institute.get('instTel'):
                    extras['phone'] = oe_institute['instTel']
                if oe_institute.get('instFax'):
                    extras['fax'] = oe_institute['instFax']
                if oe_institute.get('country'):
                    extras['country'] = oe_institute['country']
                if oe_institute.get('countryCode'):
                    extras['country_code'] = oe_institute['countryCode']
                if oe_institute.get('instRegion'):
                    extras['region'] = oe_institute['instRegion']
                if oe_institute.get('acronym'):
                    extras['acronym'] = oe_institute['acronym']
                if oe_institute.get('insttypeName'):
                    extras['institution_type'] = oe_institute['insttypeName']
                if oe_institute.get('edmoCode'):
                    extras['ocean_expert_edmo_code'] = str(oe_institute['edmoCode'])
                if oe_institute.get('activities'):
                    extras['activities'] = oe_institute['activities']
                if oe_institute.get('lDateUpdated'):
                    extras['ocean_expert_updated'] = oe_institute['lDateUpdated']
                if oe_institute.get('instLogo'):
                    group.image_url = oe_institute['instLogo']
            
            # Set extras
            set_group_extras(group, extras)
            
            click.echo(f"  Data quality: {data_quality}")
            
        except Exception as e:
            click.echo(f"  ✗ Error: {e}", err=True)
            failed += 1
            continue
    
    # Commit ALL at once at the end
    click.echo("\nCommitting all changes...")
    model.Session.flush()
    model.Session.commit()
    click.echo("Commit complete")
    
    # Summary
    click.echo("\n" + "=" * 60)
    click.echo("Synchronization complete!")
    click.echo(f"Created: {created}")
    click.echo(f"Updated: {updated}")
    click.echo(f"Failed: {failed}")
    click.echo(f"Ocean Expert enriched: {enriched}")
    click.echo(f"Total processed: {len(institutions)}")
    if len(institutions) > 0:
        click.echo(f"Success rate: {((created + updated) / len(institutions) * 100):.1f}%")
    
    # Verify with fresh query
    model.Session.expire_all()
    final_count = model.Session.query(Group).filter_by(type='group').count()
    click.echo(f"\n✓ {final_count} groups in database after commit")