# exdrf-gen-openapi2rtk

Generate RTK Query TypeScript modules from an OpenAPI 3.x document (JSON),
with optional HTTP caching for remote specs.

## Usage

### CLI

The command is registered on the shared ``exdrf-gen`` CLI as ``openapi2rtk``:

```bash
python -m exdrf_gen openapi2rtk /path/to/routes/out \
  --openapi-file /path/to/openapi.json \
  --types-import "@app/models" \
  --base-api-profile minimal
```

Use ``--base-api-profile fr_one`` when generating for the fr-one customer SPA
(same wiring as the historical ``resi_gen r2ts`` output).

## See also

- ``resi_gen r2ts`` in ``bk-one`` snapshots ``app.openapi()`` then calls this
  generator with ``--types-import @resi/models`` and ``fr_one`` base API.
