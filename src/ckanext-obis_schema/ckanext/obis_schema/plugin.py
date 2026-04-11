import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckanext.obis_schema import validators


# Maps stored license_id values to constraint-oriented display buckets.
# Any license_id not in this map will be indexed as 'Unclassified',
# which acts as a work queue for licenses that haven't been mapped yet.
LICENSE_FAMILY_MAP = {
    # Public Domain
    "cc-zero":   "Public Domain",
    "CC0-1.0":   "Public Domain",
    "other-pd":  "Public Domain",

    # Open (Attribution required)
    "cc-by-4.0":  "Open (Attribution required)",
    "CC-BY-4.0":  "Open (Attribution required)",
    "cc-by-3.0":  "Open (Attribution required)",
    "CC-BY-3.0":  "Open (Attribution required)",
    "ODC-BY-1.0": "Open (Attribution required)",
    "odc-by":     "Open (Attribution required)",
    "other-at":   "Open (Attribution required)",

    # Open (Share-Alike)
    "CC-BY-SA-4.0": "Open (Share-Alike)",
    "cc-by-sa-4.0": "Open (Share-Alike)",
    "CC-BY-SA-3.0": "Open (Share-Alike)",

    # Non-Commercial
    "CC-BY-NC-4.0": "Non-Commercial",
    "cc-by-nc-4.0": "Non-Commercial",
    "other-nc":     "Non-Commercial",

    # Not Specified
    "notspecified": "Not Specified",

    # Other Open — known open licenses not fitting above buckets
    "MIT":         "Other Open",
    "mit-license": "Other Open",
    "other-open":  "Other Open",
    "PDDL-1.0":    "Other Open",
    "ODbL-1.0":    "Other Open",
}


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

        # Index license family for faceting
        license_id = pkg_dict.get('license_id', '')
        pkg_dict['license_family'] = LICENSE_FAMILY_MAP.get(license_id, 'Unclassified')

        return pkg_dict

    def get_commands(self):
        from ckanext.obis_schema import cli
        return [cli.obis_schema]

    def dataset_facets(self, facets_dict, package_type):
        facets_dict.pop('license_id', None)
        facets_dict['vocab_product_type_tags'] = toolkit._('Product Types')
        facets_dict['vocab_thematic_tags'] = toolkit._('Thematic Areas')
        facets_dict['license_family'] = toolkit._('License')
        return facets_dict

    def group_facets(self, facets_dict, group_type, package_type):
        facets_dict.pop('license_id', None)
        facets_dict['vocab_product_type_tags'] = toolkit._('Product Types')
        facets_dict['vocab_thematic_tags'] = toolkit._('Thematic Areas')
        facets_dict['license_family'] = toolkit._('License')
        return facets_dict

    def organization_facets(self, facets_dict, organization_type, package_type):
        facets_dict.pop('license_id', None)
        facets_dict['vocab_product_type_tags'] = toolkit._('Product Types')
        facets_dict['vocab_thematic_tags'] = toolkit._('Thematic Areas')
        facets_dict['license_family'] = toolkit._('License')
        return facets_dict