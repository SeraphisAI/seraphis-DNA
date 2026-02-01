# Migration Pack

Example migration:
```bash
python -m migrations.migrate --in export.json --out export_v0_2_0.json --to 0.2.0
```

Rollback:
- Keep the original `export.json`.
