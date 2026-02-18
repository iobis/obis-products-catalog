# Operations

!!! note "Stub"
    This page is a skeleton. Content will be filled in during documentation sprints.

## Routine Commands

```bash
# Restart everything
docker compose down && docker compose up -d

# Rebuild after code changes
docker compose build ckan && docker compose up -d

# View logs
docker compose logs -f ckan

# Rebuild search index
docker compose exec ckan ckan -c /srv/app/ckan.ini search-index rebuild

# Database backup
docker compose exec db pg_dump -U ckandbuser ckandb -Fc > backup_$(date +%Y%m%d).dump

# Sync OBIS nodes
docker compose exec ckan ckan -c /srv/app/ckan.ini obis sync-nodes

# Sync institutions
docker compose exec ckan ckan -c /srv/app/ckan.ini obis sync-institutions
```

## Troubleshooting

| Symptom | Likely Cause |
|---|---|
| CKAN won't start | Check `docker compose logs ckan` for Python traceback |
| Datasets missing in browser | Solr index needs rebuild |
| Facet counts wrong | Check `before_dataset_index` field names, rebuild index |
| Nginx "host not found" | CKAN service isn't running |
| Extensions not found | Forgot to rebuild after code change |
| Exit code 137 | Out of memory — check `docker stats` |

## Git Workflow

All work happens on branches off `prod-setup`. Changes are committed on the droplet and pushed to GitHub. When stable, branches merge to `main`.

`.env` is never committed. Each deployment maintains its own `.env` from `.env.example`.
