import ckan.plugins.toolkit as toolkit
import json
from sqlalchemy import func
from ckan.model import Session, Package, PackageExtra

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


# Simple class to hold stat data that supports dot notation
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
        
def obis_get_product_type_stats():
    """Get statistics for product types from product_type field."""
    try:
        # Query database directly for product_type extras
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
        
        # Icon mapping for different product types
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
        
        # All product types in vocabulary (keys match stored values)
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
        
        # Parse the results - value is JSON string like '["video", "other"]'
        product_counts = {}
        for value_str, count in results:
            try:
                product_types = json.loads(value_str) if value_str else []
                if isinstance(product_types, list):
                    for ptype in product_types:
                        product_counts[ptype] = product_counts.get(ptype, 0) + count
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Build stats for ALL product types, even those with 0 count
        stats = []
        for ptype, label in label_mapping.items():
            stats.append(StatObject(
                name=ptype,
                count=product_counts.get(ptype, 0),
                icon=icon_mapping.get(ptype, 'fa-folder'),
                display_name=label
            ))
        
        return sorted(stats, key=lambda x: (-x.count, x.display_name))
    except Exception as e:
        return []


def obis_get_thematic_stats():
    """Get statistics for thematic areas from thematic_tags field."""
    try:
        # Query database directly for thematic_tags extras
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
        
        # Icon mapping (lowercase keys for lookup)
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
        
        # All thematic areas (keys match stored values in DB)
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
        
        # Parse the results - value is JSON string like '["Biodiversity", "Climate Change"]'
        thematic_counts = {}
        for value_str, count in results:
            try:
                thematic_tags = json.loads(value_str) if value_str else []
                if isinstance(thematic_tags, list):
                    for tag in thematic_tags:
                        thematic_counts[tag] = thematic_counts.get(tag, 0) + count
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Build stats for ALL thematic areas, even those with 0 count
        stats = []
        for tag, label in label_mapping.items():
            stats.append(StatObject(
                name=tag,
                count=thematic_counts.get(tag, 0),
                icon=icon_mapping.get(tag.lower(), 'fa-tag'),
                display_name=label
            ))
        
        return sorted(stats, key=lambda x: (-x.count, x.display_name))
    except Exception as e:
        return []


def obis_get_recent_datasets(limit=4):
    """Get recently updated datasets."""
    try:
        result = toolkit.get_action('package_search')({}, {
            'rows': limit,
            'sort': 'metadata_modified desc'
        })
        
        # Simple class for dataset objects
        class DatasetObject:
            def __init__(self, name, title, metadata_modified, owner_org, product_type_tags, thematic_tags):
                self.name = name
                self.title = title
                self.metadata_modified = metadata_modified
                self.owner_org = owner_org
                self.product_type_tags = product_type_tags
                self.thematic_tags = thematic_tags
        
        datasets = []
        for pkg in result.get('results', []):
            extras_dict = {item['key']: item['value'] for item in pkg.get('extras', [])}
            
            try:
                product_types = json.loads(extras_dict.get('product_type', '[]'))
            except (json.JSONDecodeError, TypeError):
                product_types = []
            
            try:
                thematic_tags = json.loads(extras_dict.get('thematic_tags', '[]'))
            except (json.JSONDecodeError, TypeError):
                thematic_tags = []
            
            dataset = DatasetObject(
                name=pkg.get('name'),
                title=pkg.get('title'),
                metadata_modified=pkg.get('metadata_modified'),
                owner_org=pkg.get('owner_org'),
                product_type_tags=product_types,
                thematic_tags=thematic_tags
            )
            datasets.append(dataset)
        
        return datasets
    except Exception as e:
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