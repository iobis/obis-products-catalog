# Changing "Dataset" to "Product" in CKAN UI

## Overview
This guide shows how to change all instances of "Dataset/Datasets" to "Product/Products" in the CKAN user interface using translation overrides. This is a UI-only change - no database modifications required.

## Why Translation Override?
- **Single file to maintain** - All changes in one place
- **Catches everything** - Applies across all templates automatically
- **Upgrade-safe** - Survives CKAN updates
- **No template duplication** - Don't need to override dozens of template files
- **Proper i18n** - Uses CKAN's built-in internationalization system

## Implementation Steps

### 1. Create the Translation Directory Structure
```bash
mkdir -p src/ckanext-obis_theme/ckanext/obis_theme/i18n/en/LC_MESSAGES
```

### 2. Create the Translation File
Create: `src/ckanext-obis_theme/ckanext/obis_theme/i18n/en/LC_MESSAGES/ckanext-obis_theme.po`

```po
msgid ""
msgstr ""
"Content-Type: text/plain; charset=utf-8\n"

msgid "dataset"
msgstr "product"

msgid "Dataset"
msgstr "Product"

msgid "datasets"
msgstr "products"

msgid "Datasets"
msgstr "Products"

msgid "Add Dataset"
msgstr "Add Product"

msgid "Search datasets"
msgstr "Search products"

msgid "Search Datasets"
msgstr "Search Products"

msgid "dataset information"
msgstr "product information"

msgid "Create Dataset"
msgstr "Create Product"

msgid "Edit Dataset"
msgstr "Edit Product"

msgid "View Dataset"
msgstr "View Product"

msgid "Delete Dataset"
msgstr "Delete Product"
```

### 3. Compile the Translation
This converts the human-readable `.po` file to a machine-readable `.mo` file:

```bash
docker-compose -f docker-compose.dev.yml exec ckan-dev bash
cd /srv/app/src_extensions/ckanext-obis_theme
python setup.py compile_catalog
exit
```

You should see output like:
```
running compile_catalog
compiling catalog ckanext/obis_theme/i18n/en/LC_MESSAGES/ckanext-obis_theme.po to ckanext/obis_theme/i18n/en/LC_MESSAGES/ckanext-obis_theme.mo
```

### 4. Restart CKAN
```bash
docker-compose -f docker-compose.dev.yml restart ckan-dev
```

### 5. Verify
Visit your CKAN site and check:
- Main navigation menu
- Search box placeholder text
- Page titles and headings
- Buttons (Add Dataset → Add Product)
- Breadcrumbs

All instances of "dataset" should now show as "product".

## Adding More Translations

If you find more instances that need changing:

1. Edit the `.po` file and add new msgid/msgstr pairs
2. Re-compile: `python setup.py compile_catalog`
3. Restart CKAN

## Troubleshooting

### Translations Not Showing
**Check if the .mo file was created:**
```bash
ls -la src/ckanext-obis_theme/ckanext/obis_theme/i18n/en/LC_MESSAGES/
```
You should see both `.po` and `.mo` files.

**Check CKAN logs for i18n errors:**
```bash
docker-compose -f docker-compose.dev.yml logs ckan-dev | grep -i i18n
```

**Verify the extension is loading translations:**
Make sure your `plugin.py` doesn't override `update_config` in a way that breaks i18n.

### Some Text Still Says "Dataset"
Some text might be:
- **Hardcoded in custom templates** - Add those msgid entries to your .po file
- **In JavaScript** - You'll need to override those JS files separately
- **In other extensions** - Those extensions would need their own translation overrides

### Rebuild vs Restart
- **After editing .po file**: Compile + Restart
- **After changing Python code**: Restart only
- **After changing Dockerfile**: Rebuild required

## Database Impact

**ZERO** - The database structure remains unchanged:
- Tables still named `package`, `package_extra`, etc.
- API endpoints still use `/dataset/`
- Internal code still references "datasets"

Only the user-facing labels change. The URL structure (`/dataset/`) stays the same for backward compatibility.

## Best Practices

1. **Keep a list** of all msgid/msgstr pairs you add for documentation
2. **Test thoroughly** after adding translations - check all pages
3. **Version control** your `.po` file (not the compiled `.mo` file)
4. **Document custom translations** in your extension README

## Common msgid Patterns to Override

```po
# Singular/plural variations
msgid "1 dataset"
msgstr "1 product"

msgid "{n} datasets"
msgstr "{n} products"

# With punctuation
msgid "dataset."
msgstr "product."

# In sentences
msgid "This dataset contains"
msgstr "This product contains"

# With articles
msgid "a dataset"
msgstr "a product"

msgid "the dataset"
msgstr "the product"
```

## When to Rebuild the Catalog

Rebuild when you:
- Add new translation entries
- Modify existing translations
- Fix typos in msgstr values

Don't need to rebuild when:
- Changing unrelated Python code
- Modifying templates (unless they contain new translatable strings)
- Updating CSS/JavaScript