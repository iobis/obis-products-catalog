import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckanext.obis_schema import validators


class ObisSchemaPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IValidators)
    plugins.implements(plugins.IPackageController, inherit=True)
    plugins.implements(plugins.IClick)
    plugins.implements(plugins.IFacets, inherit=True)

    def update_config(self, config_):
        toolkit.add_template_directory(config_, "templates")
        toolkit.add_public_directory(config_, "public")

    def get_validators(self):
        return {
            'scheming_required_if_spatial_type_is_point': validators.scheming_required_if_spatial_type_is_point,
            'scheming_required_if_spatial_type_is_bbox': validators.scheming_required_if_spatial_type_is_bbox,
            'scheming_valid_json_array': validators.scheming_valid_json_array,
            'convert_to_json_string': validators.convert_to_json_string,
        }

    def before_dataset_index(self, pkg_dict):
        """Ensure site_id is present and properly index multi-valued fields."""
        import json

        pkg_dict['site_id'] = toolkit.config.get('ckan.site_id', 'default')

        if 'product_type' in pkg_dict:
            if isinstance(pkg_dict['product_type'], str):
                try:
                    tags = json.loads(pkg_dict['product_type'])
                except Exception:
                    tags = [pkg_dict['product_type']]
            else:
                tags = pkg_dict['product_type']
            pkg_dict['vocab_product_type_tags'] = tags

        if 'thematic_tags' in pkg_dict:
            if isinstance(pkg_dict['thematic_tags'], str):
                try:
                    tags = json.loads(pkg_dict['thematic_tags'])
                except Exception:
                    tags = [pkg_dict['thematic_tags']]
            else:
                tags = pkg_dict['thematic_tags']
            pkg_dict['vocab_thematic_tags'] = tags

        return pkg_dict

    def get_commands(self):
        from ckanext.obis_schema import cli
        return [cli.obis_schema]

    def dataset_facets(self, facets_dict, package_type):
        facets_dict['vocab_product_type_tags'] = toolkit._('Product Types')
        facets_dict['vocab_thematic_tags'] = toolkit._('Thematic Areas')
        return facets_dict

    def group_facets(self, facets_dict, group_type, package_type):
        facets_dict['vocab_product_type_tags'] = toolkit._('Product Types')
        facets_dict['vocab_thematic_tags'] = toolkit._('Thematic Areas')
        return facets_dict

    def organization_facets(self, facets_dict, organization_type, package_type):
        facets_dict['vocab_product_type_tags'] = toolkit._('Product Types')
        facets_dict['vocab_thematic_tags'] = toolkit._('Thematic Areas')
        return facets_dict