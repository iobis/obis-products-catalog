import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from flask import Blueprint, jsonify, abort, make_response
import json
import logging
from urllib.parse import urlparse

log = logging.getLogger(__name__)


class OdisPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IBlueprint)

    # IConfigurer
    def update_config(self, config_):
        toolkit.add_template_directory(config_, "templates")
        toolkit.add_public_directory(config_, "public")
        toolkit.add_resource("assets", "odis")

    # IBlueprint
    def get_blueprint(self):
        blueprint = Blueprint('odis', self.__module__)
        blueprint.add_url_rule(
            '/dataset/<id>/odis.jsonld',
            'export_odis',
            view_func=self.export_odis,
            methods=['GET']
        )
        return blueprint

    def export_odis(self, id):
        """
        Export a CKAN dataset as ODIS-compliant Schema.org JSON-LD
        
        Args:
            id: Dataset ID or name
            
        Returns:
            JSON-LD response with proper content-type
        """
        try:
            # Get the dataset
            context = {'user': toolkit.g.user}
            dataset = toolkit.get_action('package_show')(context, {'id': id})
            
            # Transform to ODIS format
            odis_data = self.transform_to_odis(dataset)
            
            # Return as JSON-LD
            response = make_response(json.dumps(odis_data, indent=2, ensure_ascii=False))
            response.headers['Content-Type'] = 'application/ld+json; charset=utf-8'
            return response
            
        except toolkit.ObjectNotFound:
            abort(404, 'Dataset not found')
        except Exception as e:
            log.error(f"Error exporting ODIS for dataset {id}: {str(e)}")
            abort(500, f'Error generating ODIS export: {str(e)}')

    def transform_to_odis(self, dataset):
        """
        Transform CKAN dataset to ODIS-compliant Schema.org JSON-LD
        
        Args:
            dataset: CKAN dataset dict
            
        Returns:
            dict: Schema.org JSON-LD structure
        """
        odis = {}
        
        # ============================================================================
        # CONTEXT AND TYPE - Fixed values for ODIS compliance
        # ============================================================================
        odis['@context'] = {'@vocab': 'https://schema.org/'}
        
        # Determine @type from resource_type or default to CreativeWork
        resource_type = dataset.get('resource_type', 'CreativeWork')
        # Remove schema.org URL prefix if present
        if resource_type.startswith('https://schema.org/'):
            resource_type = resource_type.replace('https://schema.org/', '')
        elif resource_type.startswith('http://schema.org/'):
            resource_type = resource_type.replace('http://schema.org/', '')
        odis['@type'] = resource_type or 'CreativeWork'
        
        # ============================================================================
        # DIRECT MAPPINGS - Simple 1:1 field mappings
        # ============================================================================
        
        # Required: @id (canonical identifier - DOI)
        if dataset.get('canonical_id'):
            odis['@id'] = dataset['canonical_id']
        
        # Required: name (title)
        if dataset.get('title'):
            odis['name'] = dataset['title']
        
        # Required: description
        if dataset.get('notes'):
            odis['description'] = dataset['notes']
        
        # Optional direct mappings
        if dataset.get('url'):
            odis['url'] = dataset['url']
        
        if dataset.get('date_published'):
            odis['datePublished'] = dataset['date_published']
        
        if dataset.get('date_created'):
            odis['dateCreated'] = dataset['date_created']
        
        if dataset.get('date_modified'):
            odis['dateModified'] = dataset['date_modified']
        
        if dataset.get('license_url'):
            odis['license'] = dataset['license_url']
        
        if dataset.get('language'):
            odis['inLanguage'] = dataset['language']
        
        if dataset.get('temporal_coverage'):
            odis['temporalCoverage'] = dataset['temporal_coverage']
        
        # Keywords
        if dataset.get('keywords'):
            odis['keywords'] = dataset['keywords']
        
        # ============================================================================
        # STRUCTURED OBJECT MAPPINGS - Build complex nested objects
        # ============================================================================
        
        # Identifier (DOI as PropertyValue)
        if dataset.get('doi'):
            odis['identifier'] = self._build_doi_identifier(dataset['doi'])
        
        # Author (required - array of Person objects)
        authors_data = self._parse_json_field(dataset.get('authors'))
        if authors_data:
            odis['author'] = self._build_authors(authors_data)
        
        # Contributor (array of Organization objects from contributor affiliations)
        contributors_data = self._parse_json_field(dataset.get('contributors'))
        if contributors_data:
            contributor_orgs = self._extract_contributor_organizations(contributors_data)
            if contributor_orgs:
                odis['contributor'] = contributor_orgs
        
        # Publisher
        if dataset.get('publisher_name'):
            odis['publisher'] = self._build_publisher(dataset['publisher_name'])
        
        # Provider (your CKAN catalog - required)
        odis['provider'] = self._build_provider()
        
        # Spatial Coverage
        spatial = self._build_spatial_coverage(dataset)
        if spatial:
            odis['spatialCoverage'] = spatial
        
        # Funding
        funding_data = self._parse_json_field(dataset.get('funding'))
        if funding_data:
            odis['funding'] = self._build_funding(funding_data)
        
        return odis

    # ============================================================================
    # HELPER METHODS FOR BUILDING STRUCTURED OBJECTS
    # ============================================================================
    
    def _parse_json_field(self, field_value):
        """Parse JSON string field to Python object"""
        if not field_value:
            return None
        
        if isinstance(field_value, str):
            try:
                return json.loads(field_value)
            except (json.JSONDecodeError, ValueError) as e:
                log.warning(f"Failed to parse JSON field: {e}")
                return None
        
        # Already a dict/list
        return field_value
    
    def _build_doi_identifier(self, doi):
        """Build PropertyValue object for DOI identifier"""
        # Extract DOI value from URL
        doi_value = doi
        if doi.startswith('https://doi.org/') or doi.startswith('http://doi.org/'):
            doi_value = 'doi:' + doi.split('doi.org/')[-1]
        
        return {
            '@id': doi,
            '@type': 'PropertyValue',
            'propertyID': 'https://registry.identifiers.org/registry/doi',
            'value': doi_value,
            'url': doi
        }
    
    def _build_authors(self, authors_data):
        """
        Build array of Person objects from authors data
        
        Args:
            authors_data: List of author dicts
            
        Returns:
            list: Array of Person objects
        """
        if not isinstance(authors_data, list):
            return []
        
        authors = []
        for author in authors_data:
            if not isinstance(author, dict):
                continue
            
            person = {'@type': 'Person'}
            
            # Add @id if ORCID present
            if author.get('author_orcid'):
                person['@id'] = author['author_orcid']
            
            # Name (required)
            if author.get('author_name'):
                person['name'] = author['author_name']
            
            # Given name and family name (optional)
            if author.get('author_given_name'):
                person['givenName'] = author['author_given_name']
            
            if author.get('author_family_name'):
                person['familyName'] = author['author_family_name']
            
            # Affiliation (optional)
            if author.get('author_affiliation_name'):
                affiliation = {
                    '@type': 'Organization',
                    'name': author['author_affiliation_name']
                }
                if author.get('author_affiliation_ror'):
                    affiliation['@id'] = author['author_affiliation_ror']
                
                person['affiliation'] = [affiliation]
            
            authors.append(person)
        
        return authors
    
    def _extract_contributor_organizations(self, contributors_data):
        """
        Extract unique organizations from contributors
        ODIS wants organizations as contributors, not individual people
        
        Args:
            contributors_data: List of contributor dicts
            
        Returns:
            list: Array of unique Organization objects
        """
        if not isinstance(contributors_data, list):
            return []
        
        # Collect organizations and deduplicate
        orgs_dict = {}
        
        for contributor in contributors_data:
            if not isinstance(contributor, dict):
                continue
            
            affiliation_name = contributor.get('contributor_affiliation_name')
            if not affiliation_name:
                continue
            
            affiliation_ror = contributor.get('contributor_affiliation_ror')
            
            # Use ROR as key for deduplication, fallback to name
            key = affiliation_ror if affiliation_ror else affiliation_name
            
            if key not in orgs_dict:
                org = {
                    '@type': 'Organization',
                    'legalName': affiliation_name
                }
                if affiliation_ror:
                    org['@id'] = affiliation_ror
                
                orgs_dict[key] = org
        
        return list(orgs_dict.values())
    
    def _build_publisher(self, publisher_name):
        """Build publisher Organization object"""
        publisher = {
            '@type': 'Organization',
            'legalName': publisher_name,
            'name': publisher_name
        }
        
        # Add known publisher IDs
        if publisher_name.lower() == 'zenodo':
            publisher['@id'] = 'https://zenodo.org'
        
        return publisher
    
    def _build_provider(self):
        """
        Build provider Organization (your CKAN catalog)
        Uses configuration from environment
        """
        catalog_url = toolkit.config.get('ckan.site_url', 'http://localhost:5000')
        catalog_name = toolkit.config.get('odis.catalog_name', 'OBIS Products Catalog')
        catalog_legal_name = toolkit.config.get('odis.catalog_legal_name', 
                                                'Ocean Biodiversity Information System (OBIS) Products Catalog')
        
        return {
            '@id': catalog_url,
            '@type': 'Organization',
            'legalName': catalog_legal_name,
            'name': catalog_name,
            'url': catalog_url
        }
    
    def _build_spatial_coverage(self, dataset):
        """
        Build spatialCoverage Place object
        
        Args:
            dataset: CKAN dataset dict
            
        Returns:
            dict or None: Place object with geo information
        """
        spatial_type = dataset.get('spatial_coverage_type')
        
        if not spatial_type:
            return None
        
        place = {'@type': 'Place'}
        
        if spatial_type == 'point':
            # Point coordinates
            lat = dataset.get('spatial_point_latitude')
            lon = dataset.get('spatial_point_longitude')
            
            if lat is not None and lon is not None:
                try:
                    place['geo'] = {
                        '@type': 'GeoCoordinates',
                        'latitude': float(lat),
                        'longitude': float(lon)
                    }
                except (ValueError, TypeError):
                    log.warning(f"Invalid lat/lon values: {lat}, {lon}")
                    return None
        
        elif spatial_type == 'box':
            # Bounding box
            bbox = dataset.get('spatial_box')
            
            if bbox:
                place['geo'] = {
                    '@type': 'GeoShape',
                    'box': bbox,
                    'description': 'schema.org expects lat long (Y X) coordinate order. Box syntax is: miny minx maxy maxx'
                }
                
                # Add spatial reference system
                place['additionalProperty'] = {
                    '@type': 'PropertyValue',
                    'propertyID': 'https://dbpedia.org/page/Spatial_reference_system',
                    'value': 'https://www.w3.org/2003/01/geo/wgs84_pos'
                }
        
        # Add description if present
        if dataset.get('spatial_description'):
            place['description'] = dataset['spatial_description']
        
        # Only return if we have geo data
        if 'geo' in place:
            return place
        
        return None
    
    def _build_funding(self, funding_data):
        """
        Build funding array with grant information
        
        Args:
            funding_data: List of funding dicts
            
        Returns:
            list: Array of MonetaryGrant objects
        """
        if not isinstance(funding_data, list):
            return []
        
        grants = []
        for fund in funding_data:
            if not isinstance(fund, dict):
                continue
            
            grant = {'@type': 'MonetaryGrant'}
            
            # Funder
            if fund.get('funder_name'):
                funder = {
                    '@type': 'Organization',
                    'name': fund['funder_name']
                }
                if fund.get('funder_id'):
                    funder['@id'] = fund['funder_id']
                
                grant['funder'] = funder
            
            # Grant details
            if fund.get('grant_id'):
                grant['identifier'] = fund['grant_id']
            
            if fund.get('grant_name'):
                grant['name'] = fund['grant_name']
            
            if fund.get('grant_url'):
                grant['url'] = fund['grant_url']
            
            grants.append(grant)
        
        return grants