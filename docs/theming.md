# Theming & Aesthetics

This guide covers how to change the visual appearance of the OBIS Products Catalog. All theming is handled by the `ckanext-obis_theme` extension.

## File Map

All theme files live under `src/ckanext-obis_theme/ckanext/obis_theme/`. Here's what controls what:

| What you want to change | File to edit |
|---|---|
| Colors, fonts, spacing | `assets/style.css` |
| Logo | `templates/header.html` |
| Header layout and navigation | `templates/header.html` |
| Footer layout and logos | `templates/footer.html` |
| Homepage structure | `templates/home/layout1.html` |
| Homepage stats (product types, thematic areas) | `templates/home/snippets/highlights.html` |
| Homepage product cards | `templates/home/snippets/products.html` |
| Dataset page layout | `templates/package/read.html` |
| Highlight images | `public/images/highlight-*.png` |
| Font loading | `templates/base.html` |
| Icons (product types) | `helpers.py` → `icon_mapping` dict |
| Icons (thematic areas) | `helpers.py` → `icon_mapping` dict |

## Colors

All colors are defined as CSS custom properties at the top of `assets/style.css`:

```css
:root {
    --main-color: #b1b695;          /* Primary brand color (sage green) */
    --main-a-color: #b1b695;        /* Link color in navigation */
    --main-a-hover-color: #cfd2bb;  /* Link hover color */
    --bs-primary-rgb: 177, 182, 149 !important;
}
```

**To change the brand color**, update all three `--main-*` variables and the `--bs-primary-rgb` value. The RGB value should match `--main-color` (convert hex to RGB).

Other hardcoded colors in `style.css` that you may want to update:

| Element | Current color | Where in `style.css` |
|---|---|---|
| Top account bar | `rgb(40, 40, 40)` | `.account-masthead` |
| Footer background | `#222222` | `.site-footer` |
| Search bar background | `#f2f3f4` | `.masthead-container-2` |
| Section background (stats area) | `#f2f3f4` | `.main-secondary` |

## Font

The catalog uses **Noto Sans** loaded from Google Fonts. This is set in two places:

1. **CSS** (`assets/style.css`):
    ```css
    :root {
        --bs-font-sans-serif: "Noto Sans", sans-serif !important;
    }
    ```

2. **HTML** (`templates/base.html`):
    ```html
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans:ital,wght@0,100..900;1,100..900&display=swap" rel="stylesheet">
    ```

**To change the font**, update both files: swap the Google Fonts URL for your new font, and update the CSS variable.

## Logo

The header logo is set directly in `templates/header.html`:

```html
<img src="https://obis.org/images/logo.png" alt="{{ g.site_title }}"
     title="{{ g.site_title }}" />
```

This currently loads the OBIS logo from `obis.org`. To use a local logo instead:

1. Place your logo image in `public/images/` (e.g., `public/images/logo.png`)
2. Update the `src` in `templates/header.html`:
    ```html
    <img src="/images/logo.png" alt="{{ g.site_title }}"
         title="{{ g.site_title }}" />
    ```

The logo height is constrained by CSS:
```css
.masthead .navbar .logo img {
    max-height: 30px !important;
}
```

## Footer Logos

The footer includes IOC and IODE logos, also loaded externally. These are in `templates/footer.html`:

```html
<a href="http://www.ioc-unesco.org/" target="_blank">
    <img src="https://obis.org/images/logo_ioc_new.png">
</a>
<a href="http://www.iode.org/" target="_blank">
    <img src="https://obis.org/images/logo_iode.png">
</a>
```

Footer logo height is set in CSS:
```css
#logos img {
    height: 40px;
}
```

## Icons

Icons use [Font Awesome 4](https://fontawesome.com/v4/icons/) classes. They appear in two places on the homepage: the product type stats and the thematic area stats.

The icon mappings are defined in `helpers.py`. To change an icon, find the relevant dictionary and update the Font Awesome class.

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

## Homepage Images

Three highlight images are stored in `public/images/`:

- `highlight-1.png`
- `highlight-2.png`
- `highlight-3.png`

To replace them, drop new image files with the same filenames into that directory. These are referenced in `templates/home/snippets/products.html`.

## Applying Changes

After editing any theme files, rebuild and restart:

```bash
docker compose build ckan && docker compose up -d
```

CSS and template changes require a rebuild because the files are copied into the Docker image at build time (they are not live-mounted in production).

!!! tip
    If you're only changing CSS and want to iterate quickly, you can edit the file inside the running container for a preview: `docker compose exec ckan bash`, edit the file, and refresh. But remember to also make the change in `src/` and rebuild — container edits are lost on restart.
