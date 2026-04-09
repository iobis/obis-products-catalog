import ckan.plugins.toolkit as toolkit
import json
import random
from flask import request, redirect
from sqlalchemy import func
from ckan.model import Session, Package, PackageExtra

FEATURED_CONFIG_KEY = 'ckanext.obis_theme.featured_products'
FEATURED_MAX_POOL = 8
FEATURED_DISPLAY = 4


def dataset_type_class(value):
    """Returns a CSS-safe class name for dataset types, or '' if unknown or missing."""
    if not value:
        return ""
    mapping = {
        'Derived': 'derived',
        'Raw dataset': 'raw',
        'Interpolated': 'interpolated',
        'Aggregated': 'aggregated',
        'Map': 'map',
    }
    css_class = mapping.get(value)
    return f"add-info-value-{css_class}" if css_class else ""


class StatObject:
    def __init__(self, name, count, icon, display_name):
        self.name = name
        self.count = count
        self.icon = icon
        self.display_name = display_name


def obis_parse_json_field(value):
    """Parse a JSON string field into a Python object for templates."""
    if not value:
        return None
    if isinstance(value, (list, dict)):
        return value
    try:
        parsed = json.loads(value)
        return parsed if parsed else None
    except (json.JSONDecodeError, TypeError):
        return None


def obis_is_sysadmin():
    """Template helper: is the current user a sysadmin?"""
    try:
        return toolkit.g.userobj and toolkit.g.userobj.sysadmin
    except Exception:
        return False


def _get_featured_ids():
    """Return the list of featured product IDs/names from config."""
    try:
        raw = toolkit.config.get(FEATURED_CONFIG_KEY, '')
        if not raw:
            return []
        return json.loads(raw)
    except Exception:
        return []


def obis_get_featured_datasets(display=FEATURED_DISPLAY):
    """Get featured datasets for the homepage.

    Reads a pool of up to FEATURED_MAX_POOL product names/IDs from config.
    Randomly samples FEATURED_DISPLAY of them each page load.
    Falls back to recently updated datasets if none are configured.
    """
    class DatasetObject:
        def __init__(self, name, title, metadata_modified, owner_org,
                     product_type_tags, thematic_tags, hero_image):
            self.name = name
            self.title = title
            self.metadata_modified = metadata_modified
            self.owner_org = owner_org
            self.product_type_tags = product_type_tags
            self.thematic_tags = thematic_tags
            self.hero_image = hero_image

    def pkg_to_obj(pkg):
        extras_dict = {item['key']: item['value']
                       for item in pkg.get('extras', [])}
        try:
            product_types = json.loads(extras_dict.get('product_type', '[]'))
        except (json.JSONDecodeError, TypeError):
            product_types = []
        try:
            thematic_tags = json.loads(extras_dict.get('thematic_tags', '[]'))
        except (json.JSONDecodeError, TypeError):
            thematic_tags = []
        return DatasetObject(
            name=pkg.get('name'),
            title=pkg.get('title'),
            metadata_modified=pkg.get('metadata_modified'),
            owner_org=pkg.get('owner_org'),
            product_type_tags=product_types,
            thematic_tags=thematic_tags,
            hero_image=pkg.get('hero_image', ''),
        )

    try:
        pool_ids = _get_featured_ids()

        if pool_ids:
            # Sample from pool
            sample = random.sample(pool_ids, min(display, len(pool_ids)))
            datasets = []
            for id_ in sample:
                try:
                    pkg = toolkit.get_action('package_show')(
                        {'ignore_auth': True}, {'id': id_}
                    )
                    datasets.append(pkg_to_obj(pkg))
                except Exception:
                    pass
            if datasets:
                return datasets

        # Fallback: recent datasets
        result = toolkit.get_action('package_search')({}, {
            'rows': display,
            'sort': 'metadata_modified desc',
        })
        return [pkg_to_obj(pkg) for pkg in result.get('results', [])]

    except Exception:
        return []


def featured_products_admin():
    """Admin view for managing featured products pool."""
    if not obis_is_sysadmin():
        toolkit.abort(403, 'Sysadmin access required')

    error = None
    success = None

    if request.method == 'POST':
        # Read submitted IDs (one per line or comma-separated)
        raw = request.form.get('featured_ids', '')
        ids = [i.strip() for i in raw.replace('\n', ',').split(',') if i.strip()]

        # Validate each ID exists
        valid = []
        invalid = []
        for id_ in ids[:FEATURED_MAX_POOL]:
            try:
                pkg = toolkit.get_action('package_show')(
                    {'ignore_auth': True}, {'id': id_}
                )
                valid.append(pkg['name'])
            except Exception:
                invalid.append(id_)

        if invalid:
            error = f"Could not find these products: {', '.join(invalid)}"
        else:
            try:
                toolkit.get_action('config_option_update')(
                    {'ignore_auth': True},
                    {FEATURED_CONFIG_KEY: json.dumps(valid)}
                )
                success = f"Saved {len(valid)} featured products."
            except Exception as e:
                error = f"Could not save config: {e}"

    # Load current pool with full details
    pool_ids = _get_featured_ids()
    pool_datasets = []
    for id_ in pool_ids:
        try:
            pkg = toolkit.get_action('package_show')(
                {'ignore_auth': True}, {'id': id_}
            )
            pool_datasets.append(pkg)
        except Exception:
            pool_datasets.append({'name': id_, 'title': f'[Not found: {id_}]'})

    return toolkit.render('admin/featured_products.html', extra_vars={
        'pool_datasets': pool_datasets,
        'pool_ids_text': '\n'.join(pool_ids),
        'featured_max': FEATURED_MAX_POOL,
        'featured_display': FEATURED_DISPLAY,
        'error': error,
        'success': success,
    })


def obis_get_product_type_stats():
    """Get statistics for product types from product_type field."""
    try:
        results = Session.query(
            PackageExtra.value,
            func.count(PackageExtra.package_id)
        ).join(
            Package, Package.id == PackageExtra.package_id
        ).filter(
            PackageExtra.key == 'product_type',
            PackageExtra.state == 'active',
            Package.state == 'active',
            Package.private == False
        ).group_by(PackageExtra.value).all()

        icon_mapping = {
            'dataset': 'fa-database',
            'publication': 'fa-file-text',
            'software': 'fa-code',
            'presentation': 'fa-desktop',
            'poster': 'fa-person-chalkboard',
            'image': 'fa-image',
            'video': 'fa-video-camera',
            'lesson': 'fa-graduation-cap',
            'physical_object': 'fa-cube',
            'other': 'fa-folder',
        }

        label_mapping = {
            'dataset': 'Dataset',
            'publication': 'Publication',
            'software': 'Software',
            'presentation': 'Presentation',
            'poster': 'Poster',
            'image': 'Image/Figure',
            'video': 'Video',
            'lesson': 'Lesson',
            'physical_object': 'Physical Object',
            'other': 'Other',
        }

        product_counts = {}
        for value_str, count in results:
            try:
                product_types = json.loads(value_str) if value_str else []
                if isinstance(product_types, list):
                    for ptype in product_types:
                        product_counts[ptype] = product_counts.get(ptype, 0) + count
            except (json.JSONDecodeError, TypeError):
                pass

        stats = []
        for ptype, label in label_mapping.items():
            stats.append(StatObject(
                name=ptype,
                count=product_counts.get(ptype, 0),
                icon=icon_mapping.get(ptype, 'fa-folder'),
                display_name=label
            ))

        return sorted(stats, key=lambda x: (-x.count, x.display_name))
    except Exception:
        return []


def obis_get_thematic_stats():
    """Get statistics for thematic areas from thematic_tags field."""
    try:
        results = Session.query(
            PackageExtra.value,
            func.count(PackageExtra.package_id)
        ).join(
            Package, Package.id == PackageExtra.package_id
        ).filter(
            PackageExtra.key == 'thematic_tags',
            PackageExtra.state == 'active',
            Package.state == 'active',
            Package.private == False
        ).group_by(PackageExtra.value).all()

        icon_mapping = {
            'biodiversity': 'fa-leaf',
            'climate change': 'fa-cloud',
            'ocean acidification': 'fa-tint',
            'marine protected areas': 'fa-shield',
            'edna': 'fa-dna',
            'invasives': 'fa-bug',
            'fisheries': 'fa-ship',
            'pollution': 'fa-exclamation-triangle',
            'coastal management': 'fa-anchor',
            'deep sea': 'fa-water',
            'coral reefs': 'fa-pagelines',
            'species distribution': 'fa-map-marker',
            'near-realtime': 'fa-clock-o',
        }

        label_mapping = {
            'Biodiversity': 'Biodiversity',
            'Climate Change': 'Climate Change',
            'Ocean Acidification': 'Ocean Acidification',
            'Marine Protected Areas': 'Marine Protected Areas',
            'eDNA': 'eDNA',
            'Invasives': 'Invasives',
            'Fisheries': 'Fisheries',
            'Pollution': 'Pollution',
            'Coastal Management': 'Coastal Management',
            'Deep Sea': 'Deep Sea',
            'Coral Reefs': 'Coral Reefs',
            'Species Distribution': 'Species Distribution',
            'Near-Realtime': 'Near-Realtime',
        }

        thematic_counts = {}
        for value_str, count in results:
            try:
                thematic_tags = json.loads(value_str) if value_str else []
                if isinstance(thematic_tags, list):
                    for tag in thematic_tags:
                        thematic_counts[tag] = thematic_counts.get(tag, 0) + count
            except (json.JSONDecodeError, TypeError):
                pass

        stats = []
        for tag, label in label_mapping.items():
            stats.append(StatObject(
                name=tag,
                count=thematic_counts.get(tag, 0),
                icon=icon_mapping.get(tag.lower(), 'fa-tag'),
                display_name=label
            ))

        return sorted(stats, key=lambda x: (-x.count, x.display_name))
    except Exception:
        return []


def obis_get_recent_datasets(limit=4):
    """Get recently updated datasets."""
    try:
        result = toolkit.get_action('package_search')({}, {
            'rows': limit,
            'sort': 'metadata_modified desc'
        })

        class DatasetObject:
            def __init__(self, name, title, metadata_modified, owner_org,
                         product_type_tags, thematic_tags):
                self.name = name
                self.title = title
                self.metadata_modified = metadata_modified
                self.owner_org = owner_org
                self.product_type_tags = product_type_tags
                self.thematic_tags = thematic_tags

        datasets = []
        for pkg in result.get('results', []):
            extras_dict = {item['key']: item['value']
                           for item in pkg.get('extras', [])}
            try:
                product_types = json.loads(extras_dict.get('product_type', '[]'))
            except (json.JSONDecodeError, TypeError):
                product_types = []
            try:
                thematic_tags = json.loads(extras_dict.get('thematic_tags', '[]'))
            except (json.JSONDecodeError, TypeError):
                thematic_tags = []
            datasets.append(DatasetObject(
                name=pkg.get('name'),
                title=pkg.get('title'),
                metadata_modified=pkg.get('metadata_modified'),
                owner_org=pkg.get('owner_org'),
                product_type_tags=product_types,
                thematic_tags=thematic_tags,
            ))

        return datasets
    except Exception:
        return []


def obis_get_node_orgs():
    """Get all OBIS node organizations (those prefixed with 'node-'), sorted by title."""
    try:
        orgs = toolkit.get_action('organization_list')(
            {'ignore_auth': True},
            {'all_fields': True, 'limit': 100}
        )
        nodes = [o for o in orgs if o['name'].startswith('node-')]
        return sorted(nodes, key=lambda x: x.get('title', '').lower())
    except Exception:
        return []