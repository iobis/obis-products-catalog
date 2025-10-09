import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckanext.zenodo import validators


class ZenodoPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IValidators)
    plugins.implements(plugins.IPackageController, inherit=True)
    plugins.implements(plugins.IClick)
    plugins.implements(plugins.IFacets, inherit=True)
    plugins.implements(plugins.ITemplateHelpers) 

    def update_config(self, config_):
        toolkit.add_template_directory(config_, "templates")
        toolkit.add_public_directory(config_, "public")
        toolkit.add_resource("assets", "zenodo")
     
    def get_validators(self):
        return {
            'scheming_required_if_spatial_type_is_point': validators.scheming_required_if_spatial_type_is_point,
            'scheming_required_if_spatial_type_is_bbox': validators.scheming_required_if_spatial_type_is_bbox,
            'scheming_valid_json_array': validators.scheming_valid_json_array,
            'convert_to_json_string': validators.convert_to_json_string,
        }
    
    def before_dataset_index(self, pkg_dict):
        """
        Ensure site_id is present for Solr indexing and properly index list fields.
        """
        # Ensure site_id is present
        pkg_dict['site_id'] = toolkit.config.get('ckan.site_id', 'default')
        
        # Solr needs these as proper lists for multi-valued fields
        # The field names need _ss suffix for multi-valued string fields
        if 'product_type_tags' in pkg_dict:
            if isinstance(pkg_dict['product_type_tags'], str):
                try:
                    import json
                    tags = json.loads(pkg_dict['product_type_tags'])
                except:
                    tags = [pkg_dict['product_type_tags']]
            else:
                tags = pkg_dict['product_type_tags']
            # Store with _ss suffix for Solr dynamic multi-valued field
            pkg_dict['vocab_product_type_tags'] = tags
        
        if 'thematic_tags' in pkg_dict:
            if isinstance(pkg_dict['thematic_tags'], str):
                try:
                    import json
                    tags = json.loads(pkg_dict['thematic_tags'])
                except:
                    tags = [pkg_dict['thematic_tags']]
            else:
                tags = pkg_dict['thematic_tags']
            # Store with _ss suffix for Solr dynamic multi-valued field  
            pkg_dict['vocab_thematic_tags'] = tags
        
        return pkg_dict
    
    def get_commands(self):
        from ckanext.zenodo import cli
        return [cli.zenodo]
    
    def dataset_facets(self, facets_dict, package_type):
        """Add custom facets to dataset search"""
        facets_dict['vocab_product_type_tags'] = toolkit._('Product Types')
        facets_dict['vocab_thematic_tags'] = toolkit._('Thematic Areas')
        return facets_dict
    
    def group_facets(self, facets_dict, group_type, package_type):
        """Add custom facets to group search"""
        facets_dict['product_type_tags'] = toolkit._('Product Types')
        facets_dict['thematic_tags'] = toolkit._('Thematic Areas')
        return facets_dict
    
    def organization_facets(self, facets_dict, organization_type, package_type):
        """Add custom facets to organization search"""
        facets_dict['product_type_tags'] = toolkit._('Product Types')
        facets_dict['thematic_tags'] = toolkit._('Thematic Areas')
        return facets_dict
    
    def get_helpers(self):
        return {
            'get_product_type_stats': get_product_type_stats,
            'get_thematic_stats': get_thematic_stats,
            'get_recent_datasets': get_recent_datasets,
        }

def get_product_type_stats():
    """Get count of datasets by product type"""
    try:
        context = {'ignore_auth': True}
        
        # Get all product types from vocabulary
        vocab = toolkit.get_action('vocabulary_show')(context, {'id': 'product_types'})
        product_types = [tag['name'] for tag in vocab.get('tags', [])]
        
        stats = []
        for product_type in product_types:
            # Search for datasets with this product type
            result = toolkit.get_action('package_search')(
                context,
                {'fq': f'vocab_product_type_tags:"{product_type}"', 'rows': 0}
            )
            count = result.get('count', 0)
            if count > 0:  # Only include types that have datasets
                stats.append({
                    'name': product_type,
                    'count': count,
                    'icon': get_product_type_icon(product_type)
                })
        
        return stats
    except Exception as e:
        return []

def get_thematic_stats():
    """Get count of datasets by thematic area"""
    try:
        context = {'ignore_auth': True}
        
        # Get all thematics from vocabulary
        vocab = toolkit.get_action('vocabulary_show')(context, {'id': 'thematics'})
        thematics = [tag['name'] for tag in vocab.get('tags', [])]
        
        stats = []
        for thematic in thematics:
            # Search for datasets with this thematic area
            result = toolkit.get_action('package_search')(
                context,
                {'fq': f'vocab_thematic_tags:"{thematic}"', 'rows': 0}
            )
            count = result.get('count', 0)
            if count > 0:  # Only include areas that have datasets
                stats.append({
                    'name': thematic,
                    'count': count,
                    'icon': get_thematic_icon(thematic)
                })
        
        return stats
    except Exception as e:
        return []

def get_thematic_icon(thematic):
    """Map thematic areas to Font Awesome icons"""
    icon_map = {
        'Biodiversity': 'fa-leaf',
        'Climate Change': 'fa-thermometer-half',
        'Ocean Acidification': 'fa-flask',
        'Marine Protected Areas': 'fa-shield-alt',
        'Fisheries': 'fa-fish',
        'Pollution': 'fa-skull-crossbones',
        'Coastal Management': 'fa-umbrella-beach',
        'Deep Sea': 'fa-water',
        'Coral Reefs': 'fa-gem',
        'Species Distribution': 'fa-map-marked-alt'
    }
    return icon_map.get(thematic, 'fa-tag')

def get_product_type_icon(product_type):
    """Map product types to Font Awesome icons"""
    icon_map = {
        'Raw Dataset': 'fa-database',
        'Derived Dataset': 'fa-table',
        'Model Output': 'fa-calculator',
        'Report': 'fa-file-text',
        'Presentation': 'fa-presentation',
        'Data Visualization': 'fa-chart-bar',
        'Map': 'fa-map',
        'Workflow': 'fa-project-diagram',
        'Software': 'fa-code',
        'Standard': 'fa-check-circle'
    }
    return icon_map.get(product_type, 'fa-file')

def get_recent_datasets(limit=4):
    """Get most recently updated datasets"""
    try:
        context = {'ignore_auth': True}
        result = toolkit.get_action('package_search')(
            context,
            {
                'sort': 'metadata_modified desc',
                'rows': limit
            }
        )
        return result.get('results', [])
    except Exception as e:
        return []