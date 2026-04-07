# Theming & Aesthetics

This guide covers how to change the visual appearance of the OBIS Products Catalog. All theming is handled by the `ckanext-obis_theme` extension.

## File Map

All theme files live under `src/ckanext-obis_theme/ckanext/obis_theme/`. Here's what controls what:

| What you want to change | File to edit |
|---|---|
| Colors, fonts | `public/css/theme.css` |
| CKAN overrides (buttons, dropdowns, search) | `assets/style.css` |
| JavaScript (collapse, interactions) | `assets/script.js` |
| Logo | `templates/header.html` |
| Header layout and navigation | `templates/header.html` |
| Footer layout and logos | `templates/footer.html` |
| Homepage structure | `templates/home/layout1.html` |
| Homepage stats (product types, thematic areas) | `templates/home/snippets/highlights.html` |
| Homepage product cards | `templates/home/snippets/products.html` |
| Dataset page layout | `templates/package/read.html` |
| Font loading | `templates/base.html` |
| Icons (product types and thematic areas) | `helpers.py` → `icon_mapping` dict |

## Colors

Colors are defined as CSS custom properties in `public/css/theme.css`. To change a color, update the variable value — all references throughout the codebase use these variables.

| Variable | Value | Swatch | Used for |
|---|---|---|---|
| `--color-brand` | `#2F6FEF` | <span style="display:inline-block;width:16px;height:16px;background:#2F6FEF;border-radius:3px;vertical-align:middle;"></span> | Primary blue — buttons, links |
| `--color-brand-light` | `#e8f0fd` | <span style="display:inline-block;width:16px;height:16px;background:#e8f0fd;border-radius:3px;border:1px solid #ccc;vertical-align:middle;"></span> | Light blue — tag backgrounds |
| `--color-brand-faded` | `rgba(47,111,239,0.5)` | <span style="display:inline-block;width:16px;height:16px;background:rgba(47,111,239,0.5);border-radius:3px;vertical-align:middle;"></span> | Faded blue — homepage icons |
| `--color-accent` | `#CDDEE7` | <span style="display:inline-block;width:16px;height:16px;background:#CDDEE7;border-radius:3px;vertical-align:middle;"></span> | Light teal — masthead background |
| `--color-dark` | `#343A40` | <span style="display:inline-block;width:16px;height:16px;background:#343A40;border-radius:3px;vertical-align:middle;"></span> | Dark grey — footer, body text |
| `--color-mid` | `#6c757d` | <span style="display:inline-block;width:16px;height:16px;background:#6c757d;border-radius:3px;vertical-align:middle;"></span> | Mid grey — labels, secondary text |
| `--color-light` | `#f2f3f4` | <span style="display:inline-block;width:16px;height:16px;background:#f2f3f4;border-radius:3px;border:1px solid #ccc;vertical-align:middle;"></span> | Light grey — section backgrounds |
| `--color-border` | `#ced4da` | <span style="display:inline-block;width:16px;height:16px;background:#ced4da;border-radius:3px;vertical-align:middle;"></span> | Input and element borders |

To change a color, update the variable value in `theme.css`. All references throughout the codebase use these variables.

## Font

The catalog uses **Noto Sans** from Google Fonts, loaded in `templates/base.html` and set as the default via `--bs-font-sans-serif` in `theme.css`. To change the font, update both the Google Fonts link in `base.html` and the CSS variable in `theme.css`.

## Logo

The header loads two logos directly from obis.org in `templates/header.html`:

```html
<img src="https://obis.org/images/ioc_logo_blue_2.svg" alt="{{ g.site_title }}" title="{{ g.site_title }}" />
<img src="https://obis.org/images/logo_simple.png" style="height: 30px;">
```

These are loaded externally and will reflect any changes made on obis.org. Logo height is constrained in `theme.css`:

```css
.masthead .navbar .logo img {
    max-height: 30px !important;
}
```

## Footer Logos

The footer includes IOC and IODE logos, loaded externally from `templates/footer.html`:

```html
<a href="http://www.ioc-unesco.org/" target="_blank">
    <img src="https://obis.org/images/logo_ioc_new.png">
</a>
<a href="http://www.iode.org/" target="_blank">
    <img src="https://obis.org/images/logo_iode.png">
</a>
```

Footer logo height is set in `theme.css`:
```css
#logos img {
    height: 40px;
}
```

## Icons

Icons use [Font Awesome 4](https://fontawesome.com/v4/icons/) classes. They appear on the homepage in the product type and thematic area stat grids. The icon mappings are defined in `helpers.py`. To change an icon, find the relevant dictionary and update the Font Awesome class.

**Product type icons** — in `obis_get_product_type_stats()`:

```python
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
```

**Thematic area icons** — in `obis_get_thematic_stats()`:

```python
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
}
```

Browse available icons at [fontawesome.com/v4/icons](https://fontawesome.com/v4/icons/).

## Applying Changes

After editing any theme files, rebuild and restart:

```bash
docker compose build ckan && docker compose up -d
```

CSS and template changes require a rebuild because the files are copied into the Docker image at build time.