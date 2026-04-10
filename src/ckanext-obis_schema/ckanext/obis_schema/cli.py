"""
CKAN CLI commands for OBIS schema management.
"""
import click
import ckan.plugins.toolkit as toolkit


@click.group()
def obis_schema():
    """OBIS schema management commands."""
    pass


@obis_schema.command()
def init_vocabularies():
    """Initialize controlled vocabularies for product types and thematic areas."""

    click.echo("=== Initializing Vocabularies ===\n")

    vocabularies = {
        'product_types': [
            'dataset',
            'publication',
            'software',
            'presentation',
            'poster',
            'image',
            'video',
            'lesson',
            'physical_object',
            'other',
        ],
        'thematics': [
            'Biodiversity',
            'Climate Change',
            'Ocean Acidification',
            'Marine Protected Areas',
            'eDNA',
            'Invasives',
            'Fisheries',
            'Pollution',
            'Coastal Management',
            'Deep Sea',
            'Coral Reefs',
            'Species Distribution',
            'Near-Realtime',
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
            except Exception:
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