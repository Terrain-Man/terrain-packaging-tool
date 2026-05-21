# Terrain Packaging Tool - Initial Implementation

This repository contains a PostgreSQL/PostGIS-centered terrain packaging workflow for converting georeferenced elevation rasters into engine-ready terrain-package artifacts.

The project is organized around one main Python script:

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

This is a first working implementation of a terrain-packaging workflow for GIS-to-engine terrain production.

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

---

## Repository Structure

```text
terrain_packaging_tool/
  README.md
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
    00_table_of_contents.md
    01_intro_and_concepts.md
    02_database_prep_and_schema_initialization.md
    03_mode_explanations.md
    04_appendix_a_database_table_plan.md
    05_appendix_b_json_artifact_examples.md
  outputs/
    .gitkeep
```

The `logs/` and `outputs/` folders may initially contain only `.gitkeep` files. Actual logs and terrain-package artifacts are generated when the tool runs and are excluded from version control.

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
terrain_packaging_tool
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

Then, starting with an empty database, run:

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

---

## License and Data Sources

No third-party elevation datasets are included in this repository. Users are responsible for obtaining source raster data under appropriate license terms.

Code licensing is not yet finalized. Until a license is added, this repository is provided for review and demonstration only.