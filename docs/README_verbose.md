# GEOG670 Terrain Tool Starter

This starter package contains a PostgreSQL/PostGIS-centered terrain packaging workflow for converting georeferenced elevation rasters into engine-ready terrain-package artifacts.

The workflow is organized around one main Python tool:

```text
terrain_tool.py
```

and three workflow modes:

1. **Mode 1 — Raster registration**
   Register source elevation datasets.

2. **Mode 2 — AOI registration**
   Register reusable AOI definitions.

3. **Mode 3 — Terrain package operations**
   Create, build, export, validate, re-export, or generate diagnostic terrain-package artifacts.

Database schema preparation is handled separately before Modes 1–3 are used.

At the current stage, **Mode 3A: Create tile plan only** is implemented. Later Mode 3 branches are part of the planned architecture but are not yet implemented in the starter script.

---

# Starter Package Structure

The starter ZIP should contain this structure:

```text
terrain_tool_starter/
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
    manifest-rule.schema-notes.md
    tile-catalog.schema-notes.md
    database_schema_notes.md

  outputs/
    .gitkeep
```

The `logs/` and `outputs/` folders may initially contain only `.gitkeep` files. These are empty placeholder files that allow empty folders to be preserved in a ZIP or Git repository.

Actual logs and terrain-package artifacts are created later when the tool runs.

---

# Required Software

This workflow assumes:

* PostgreSQL installed and running
* PostGIS installed and available
* PostGIS Raster available if raster payload storage is used later
* Python 3.12 or later
* Required Python packages installed in the active environment
* Access to the project database, for example:

```text
geog670_terrain_packaging_v1
```

Recommended Python environment name:

```text
geog670_terrain
```

Activate the environment before running the database preparation scripts or terrain tool.

Example:

```bash
conda activate geog670_terrain
```

---

# Required Python Packages

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
import yaml          # package: PyYAML
import psycopg       # package: Psycopg
import rasterio
import geopandas as gpd
from shapely import ...
from pyproj import CRS as PyprojCRS
```

Pandas and GDAL-related libraries may be used indirectly through GeoPandas, Rasterio, Fiona, or pyogrio, depending on the environment.

Current GeoPackage export may produce a warning that Pandas prefers SQLAlchemy database connections. This does not by itself mean the export failed. SQLAlchemy may be added later as a cleaner database bridge for GeoPandas/PostGIS export, but the current core database workflow uses Psycopg directly.

---

# Setup Order

Run the setup steps in this order.

## 1. Unzip the starter package

Unzip the starter package wherever the project should live.

Example:

```text
D:/GIS/GEOG670/terrain_tool/
```

After unzipping, the project root should contain:

```text
README.md
terrain_tool.py
db/
config/
logs/
docs/
outputs/
```

Open a terminal in the project root folder before running the later commands.

---

## 2. Create local YAML configuration files

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

Then edit the copied files for the local machine.

The `.example` files should remain as reusable templates.

---

# Configuration Files

## `config/database_config.yaml`

This file stores database connection settings.

Example:

```yaml
database:
  host: "localhost"
  port: 5432
  name: "geog670_terrain_packaging_v1"
  user: "postgres"
  password_env_var: "GEOG670_DB_PASSWORD"

schema:
  name: "public"
```

The preferred pattern is to avoid storing the database password directly in the YAML file.

Instead, store the name of an environment variable:

```yaml
password_env_var: "GEOG670_DB_PASSWORD"
```

Then set that environment variable locally.

Example in PowerShell for the current session:

```powershell
$env:GEOG670_DB_PASSWORD = "your_password_here"
```

For persistent use on Windows, set the environment variable through Windows Environment Variables settings or through a PowerShell profile.

---

## `config/tool_config.yaml`

This file stores tool behavior defaults.

Current Mode 3A uses this file for terrain planning defaults and output-artifact settings. The user is not prompted for every setting at startup. Instead, the tool loads defaults, computes the tile plan, displays a resolved summary, and then asks the user to accept, cancel, or choose grouped override categories.

Representative structure:

```yaml
paths:
  schema_sql_path: "db/schema.sql"

logging:
  level: "INFO"
  verbose: false

defaults:
  path_storage_mode: "root_plus_relative"
  manifest_schema_version: "0.4.0"
  tile_catalog_schema_version: "0.4.0"
  expected_database_schema_version: "0.1.1"

runtime_profiles:
  default_profile_id: "unity_arcgis_maps_sdk"

mode3:
  default_heightmap_resolution: 1025
  default_target_sample_spacing_meters: 1.0
  default_tile_size_strategy: "derive_from_heightmap_resolution_and_target_sample_spacing"
  default_tile_size_meters: null

  default_edge_policy: "ceil_to_full_tiles"

  default_grid_anchor_policy: "snap_to_source_raster_grid"
  default_snap_reference: "source_raster_cell_edges"
  default_snap_min_direction: "floor_to_southwest"
  default_snap_max_direction: "ceil_to_northeast"
  default_aoi_enclosure_policy: "fully_enclose_aoi"

  default_output_root_folder: null

  default_generate_manifest_rule: true
  default_export_tile_grid_geopackage: true

  require_confirmation_for_unsnapped_grid: true
  warn_when_grid_not_snapped_to_source: true
  warn_when_target_spacing_exceeds_source_cell_size: true
  note_when_target_spacing_is_finer_than_source_cell_size: true
```

Current supported runtime profile IDs are:

```text
unity_arcgis_maps_sdk
unity_cesium
```

If `default_output_root_folder` is `null`, current Mode 3A writes artifacts under:

```text
outputs/mode3/<session_id>/
```

Example:

```text
outputs/mode3/pyp_test_003_plan_001/
```

YAML is used for human-edited local configuration.

JSON is used for strict exported machine artifacts such as:

```text
manifest-rule.json
tile-catalog.json
```

---

# Database Preparation

Before running Modes 1–3, the PostgreSQL/PostGIS database schema must be created.

The database itself should already exist.

For this project, the expected database is:

```text
geog670_terrain_packaging_v1
```

If the database does not exist, create it first in pgAdmin or with PostgreSQL tools.

Then run:

```bash
python db/db_prepare.py
```

`db_prepare.py` should:

* read database settings from `config/database_config.yaml`
* connect to the project database
* execute `db/schema.sql`
* create required PostGIS extensions if available
* create the workflow tables
* create indexes
* create constraints
* create triggers
* create database comments
* report success or failure

The authoritative schema definition is:

```text
db/schema.sql
```

Do not manually create the workflow tables in pgAdmin as the primary method. pgAdmin is useful for inspection and debugging, but the reproducible schema should come from `schema.sql`.

---

# Database Readiness Check

After preparing the database, run:

```bash
python db/db_check.py
```

`db_check.py` should verify:

* database connection
* PostGIS availability
* PostGIS Raster availability, if required
* required tables
* required columns
* required indexes
* required constraints
* expected schema version

If the check fails, correct the reported issue before running `terrain_tool.py`.

---

# Running the Terrain Tool

After setup and database preparation are complete, run:

```bash
python terrain_tool.py
```

The tool should present the workflow modes:

```text
Mode 1: Register Source Raster Dataset
Mode 2: Register AOI Definition
Mode 3: Terrain Package Operations
```

Modes 1–3 assume that the database schema already exists.

If the schema is missing or incomplete, `terrain_tool.py` should stop and tell the user to run:

```bash
python db/db_prepare.py
python db/db_check.py
```

---

# Current Mode 3 Status

Mode 3 is designed as a multi-branch terrain-package workflow.

Current implemented branch:

```text
Mode 3A: Create tile plan only
```

Planned but not yet implemented branches:

```text
Mode 3B: Create tile plan and build raster tiles
Mode 3C: Use existing tile plan to build raster tiles
Mode 3D: Export RAW files from stored raster tiles
Mode 3E: Validate or re-export from manifest-rule.json
Mode 3F: Export sample-lattice overlay from existing tile plan
```

The current Mode 3 menu may show planned branches as placeholders. Only Mode 3A should be treated as implemented unless the script has since been extended.

---

# Current Mode 3A Behavior

Mode 3A creates a tile plan only.

It prompts for:

```text
run_id
Source ID (source_dataset_id)
AOI ID (aoi_id)
```

It then reads:

```text
source_raster_datasets
aoi_definitions
```

and loads planning defaults from:

```text
config/tool_config.yaml
```

Mode 3A computes:

* terrain intervals per side
* target sample spacing
* tile size
* sampling relationship
* sampling severity
* snapped grid origin
* enclosing grid extent
* row count
* column count
* tile count
* AOI intersection per tile
* AOI occupied fraction per tile

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

In plain terms:

```text
Mode 3A creates the approved real-world tile footprint plan.
It does not yet create engine-ready heightmap files.
```

---

# Expected Current Mode 3A Output Structure

If `default_output_root_folder` is `null`, Mode 3A currently writes to:

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

If `default_output_root_folder` is set in `tool_config.yaml`, Mode 3A writes to:

```text
<default_output_root_folder>/<session_id>/
```

Current Mode 3A does not write:

```text
tile-catalog.json
raw_tiles/
```

Those belong to later build/export modes.

A future full terrain package may look like:

```text
<output_root>/<session_id>/
  manifest-rule.json
  tile-catalog.json
  tile_grid.gpkg

  raw_tiles/
    terrain_r0_c0.raw
    terrain_r0_c1.raw
    terrain_r0_c2.raw

  logs/
    <session_id>.log
```

But that is not the current Mode 3A output.

---

# Expected Working Project Structure

After local configuration and tool use, the project folder may look like this:

```text
project_root/
  README.md
  terrain_tool.py

  db/
    schema.sql
    db_prepare.py
    db_check.py

  config/
    database_config.yaml.example
    tool_config.yaml.example
    database_config.yaml
    tool_config.yaml

  logs/
    terrain_tool.log
    mode1_raster_registration.log
    mode2_aoi_registration.log
    mode3_terrain_package_operations.log

  docs/
    manifest-rule.schema-notes.md
    tile-catalog.schema-notes.md
    database_schema_notes.md

  outputs/
    mode3/
      <session_id>/
        manifest-rule.json
        tile_grid.gpkg
```

Source rasters do not need to live inside the project root.

Large source datasets may remain in external GIS data folders and be registered by Mode 1 using:

```text
source_root_path + relative_path
```

Example:

```text
D:/GIS/Eryri/DTM/tiles/
  SN65_DTM_1m.tif
  SN66_DTM_1m.tif
  SN67_DTM_1m.tif
```

The database records where those sources are and how they should be accessed.

---

# File Roles

## `terrain_tool.py`

Main workflow tool.

Implements:

* Mode 1 raster registration
* Mode 2 AOI registration
* Mode 3 terrain package operations

Current implemented Mode 3 branch:

```text
Mode 3A: Create tile plan only
```

## `db/schema.sql`

Authoritative SQL schema definition.

Creates required database extensions, tables, indexes, constraints, triggers, and database comments.

## `db/db_prepare.py`

Runs `schema.sql` against the configured PostgreSQL/PostGIS database.

This prepares the database for the terrain workflow.

## `db/db_check.py`

Checks whether the database is ready for `terrain_tool.py`.

## `config/database_config.yaml.example`

Template for local database connection configuration.

Copy this file to:

```text
config/database_config.yaml
```

then edit the copy.

## `config/tool_config.yaml.example`

Template for local tool behavior configuration.

Copy this file to:

```text
config/tool_config.yaml
```

then edit the copy.

## `docs/`

Documentation for JSON artifacts and database schema notes.

These files explain field meanings and schema assumptions beyond what belongs directly inside strict JSON artifacts.

## `logs/`

General tool logs and mode-specific logs.

## `outputs/`

Default output folder for generated Mode 3 artifacts when no explicit output root is configured.

Current Mode 3A creates session-specific folders under:

```text
outputs/mode3/
```

---

# Safety Rules

The setup and preparation workflow should follow these rules:

* Do not overwrite existing user-edited YAML configuration files.
* Do not drop database tables unless the user explicitly chooses a development reset option.
* Do not store database passwords directly in committed configuration files if avoidable.
* Treat `schema.sql` as the authoritative schema definition.
* Treat PostgreSQL/PostGIS as the authoritative workflow state.
* Treat `manifest-rule.json` as the current standard planning/recovery/control artifact for Mode 3A.
* Treat `tile-catalog.json` as a later runtime/output catalog that should not be generated until actual terrain tile outputs exist.
* Treat source rasters as external source material unless explicitly loaded into PostGIS.
* Treat Mode 3A tile plans as planned terrain package structure, not realized terrain output.

---

# Recommended First Run Sequence

From the project root:

```bash
conda activate geog670_terrain
```

Copy and edit:

```text
config/database_config.yaml.example → config/database_config.yaml
config/tool_config.yaml.example → config/tool_config.yaml
```

Then run:

```bash
python db/db_prepare.py
python db/db_check.py
python terrain_tool.py
```

Within `terrain_tool.py`, a typical first workflow is:

```text
1. Mode 1: Register Source Raster Dataset
2. Mode 2: Register AOI Definition
3. Mode 3: Terrain Package Operations
   1. Create tile plan only
```

For Mode 3A, the current successful output should include:

```text
terrain_tile_runs row
terrain_tile_grid_plan rows
outputs/mode3/<session_id>/manifest-rule.json
outputs/mode3/<session_id>/tile_grid.gpkg
```

That completes initial setup and creates a first plan-only terrain tile package artifact.