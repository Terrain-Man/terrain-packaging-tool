# GEOG670 Terrain Tool Starter

This repository contains a PostgreSQL/PostGIS-centered terrain packaging workflow for converting georeferenced elevation rasters into engine-ready terrain-package artifacts.

The project is organized around one main Python tool:

```text
terrain_tool.py
```

The workflow supports three major modes:

1. **Mode 1 — Raster registration**
   Register source elevation raster datasets.

2. **Mode 2 — AOI registration**
   Register reusable area-of-interest definitions.

3. **Mode 3 — Terrain package operations**
   Create terrain tile plans and, in later branches, build/export terrain-package artifacts.

At the current stage, **Mode 3A: Create tile plan only** is implemented. Later Mode 3 branches are part of the planned architecture but are not yet implemented.

---

## Project Status

This is a starter / vertical-slice implementation of a terrain-packaging workflow for GIS-to-engine terrain production.

The current implementation can:

* prepare and check a PostgreSQL/PostGIS database schema
* register source rasters
* register AOI definitions
* create a Mode 3A tile plan
* write tile-plan records to the database
* export planning artifacts such as `manifest-rule.json`
* optionally export a tile grid GeoPackage

The current implementation does **not yet** create raster tiles, RAW heightmap files, or a complete runtime `tile-catalog.json`.

In plain terms:

```text
Mode 3A creates the approved real-world tile footprint plan.
It does not yet create engine-ready heightmap files.
```

This matches the scope described in your verbose README: Mode 3A is implemented, while later terrain-build/export branches remain planned.

---

## Repository Structure

Expected starter structure:

```text
terrain_tool_starter/
  README.md
  README_verbose.md
  terrain_tool.py

  db/
    schema.sql
    db_prepare.py
    db_check.py

  config/
    database_config.yaml.example
    tool_config.yaml.example

  logs/
    .gitkeep

  docs/
    manifest-rule.schema-notes.md
    tile-catalog.schema-notes.md
    database_schema_notes.md

  outputs/
    .gitkeep
```

The `logs/` and `outputs/` folders may initially contain only `.gitkeep` files. Actual logs and terrain-package artifacts are created when the tool runs.

---

## Required Software

This workflow assumes:

* PostgreSQL installed and running
* PostGIS installed and available
* PostGIS Raster available if raster payload storage is used later
* Python 3.12 or later
* Required Python packages installed in the active environment
* Access to a project database, for example:

```text
terrain_tool_db
```

Recommended Python environment name:

```text
terrain_packaging tool
```

Activate the environment before running the database preparation scripts or terrain tool:

```bash
conda activate terrain_packaging_tool
```

---

## Required Python Packages

The current script uses these direct non-standard Python packages:

```text
PyYAML
Psycopg
Rasterio
GeoPandas
Shapely
pyproj
```

In import-name terms:

```python
import yaml
import psycopg
import rasterio
import geopandas as gpd
from shapely import ...
from pyproj import CRS as PyprojCRS
```

Pandas and GDAL-related libraries may also be used indirectly through GeoPandas, Rasterio, Fiona, or pyogrio, depending on the environment.

---

## Quick Start

This project was developed in a local Python environment using Anaconda/conda. Other Python environment managers may work, but the documented setup assumes Anaconda or Miniconda.

From the project root, activate the project environment if using conda:

```bash
conda activate terrain_packaging_tool
```

Copy the example configuration files:

```text
config/database_config.yaml.example → config/database_config.yaml
config/tool_config.yaml.example → config/tool_config.yaml
```

Edit the copied YAML files for the local machine.

Then run:

```bash
python db/db_prepare.py
python db/db_check.py
python terrain_tool.py
```

A typical first workflow inside `terrain_tool.py` is:

```text
1. Mode 1: Register Source Raster Dataset
2. Mode 2: Register AOI Definition
3. Mode 3: Terrain Package Operations
   1. Create tile plan only
```

The setup order follows your verbose README’s recommended first run sequence.

---

## Configuration

Do not edit the `.example` files as live configuration.

Instead, copy:

```text
config/database_config.yaml.example
```

to:

```text
config/database_config.yaml
```

and copy:

```text
config/tool_config.yaml.example
```

to:

```text
config/tool_config.yaml
```

Then edit the copied files.

The `.example` files should remain reusable templates.

Database passwords should not be committed to the repository. The preferred pattern is to store the password in a local environment variable and reference that variable from the YAML configuration.

Example:

```yaml
database:
  host: "localhost"
  port: 5432
  name: "terrain_tool_db"
  user: "user"
  password_env_var: "TERRAIN_TOOL_PASSWORD"
```

---

## Database Preparation

Before running Modes 1–3, the PostgreSQL/PostGIS database schema must be created.

The database itself should already exist. Then run:

```bash
python db/db_prepare.py
```

The authoritative schema definition is:

```text
db/schema.sql
```

Do not manually create the workflow tables in pgAdmin as the primary method. pgAdmin is useful for inspection and debugging, but the reproducible schema should come from `schema.sql`.

After preparing the database, run:

```bash
python db/db_check.py
```

If the check fails, correct the reported issue before running `terrain_tool.py`.

Your verbose README already separates database preparation from Modes 1–3 and identifies `db/schema.sql` as the authoritative schema definition.

---

## Current Mode 3A Behavior

Mode 3A creates a tile plan only.

It prompts for:

```text
run_id
Source ID (source_dataset_id)
AOI ID (aoi_id)
```

It then reads the registered source raster and AOI records from the database, loads planning defaults from:

```text
config/tool_config.yaml
```

and computes the tile footprint plan.

Mode 3A writes:

```text
terrain_tile_runs
terrain_tile_grid_plan
manifest-rule.json
tile_grid.gpkg, if enabled
```

Mode 3A does not create:

```text
raster tiles
RAW files
tile-catalog.json
terrain_tile_grid_outputs
terrain_tile_grid_rasters
```

---

## Expected Mode 3A Outputs

If no explicit output root is configured, Mode 3A writes artifacts under:

```text
outputs/mode3/<session_id>/
```

Example:

```text
outputs/
  mode3/
    pyp_test_003_plan_001/
      manifest-rule.json
      tile_grid.gpkg
```

A later full terrain package may include additional outputs such as:

```text
tile-catalog.json
raw_tiles/
```

but those belong to later build/export modes.

---

## Documentation

Additional notes are stored under:

```text
docs/
```

These files explain artifact schemas, database assumptions, and implementation details that are too detailed for the base README.

The longer version of this README is preserved as:

```text
README_verbose.md
```

---

## Data and Safety Notes

This repository should not include:

* local machine paths
* database passwords
* API keys or tokens
* large source rasters
* generated RAW tiles
* private or licensed source datasets unless redistribution is explicitly allowed

Source rasters can remain in external GIS data folders and be registered by Mode 1 using stored path references.

Use `.gitignore` to exclude local configuration files, generated outputs, logs, caches, and large GIS data files.

---

## License and Data Sources

Code licensing and data redistribution terms should be handled separately.

Large elevation datasets are not included in this starter repository. Users are responsible for obtaining any source raster data under appropriate license terms.
