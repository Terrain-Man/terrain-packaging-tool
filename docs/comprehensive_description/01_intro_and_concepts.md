## 1. Introduction

This plan describes a database-centered terrain production workflow for converting georeferenced elevation rasters into engine-ready terrain packages.

The workflow organizes source data, AOIs, tile plans, exported RAW files, JSON artifacts, logs, and validation records through a coherent PostgreSQL/PostGIS-backed process.

The overall design should be **one script with three major modes**, not several disconnected scripts. The single entry point keeps the workflow coherent, while the modes keep responsibilities separated.

Proposed script:

**`terrain_tool.py`**

The tool has three major modes:

1. **Mode 1 (raster registration)**
2. **Mode 2 (AOI registration)**
3. **Mode 3 (terrain package operations)**

Mode 1 and Mode 2 are upstream preparation stages. They populate reusable database records.

Mode 3 is the production and management stage. It uses a registered `source_dataset_id` and a registered `aoi_id` to create, manage, export, store, validate, or re-export terrain packages.

The major architectural idea is:

**Python is the launcher and file orchestrator. PostgreSQL/PostGIS is the terrain-production engine.**

Python should prompt the user, collect parameters, call database routines, verify files, create output folders, write JSON artifacts, export RAW files, compute or record checksums, write logs, and update run status.

PostgreSQL/PostGIS should handle the spatial logic: registering source raster metadata, storing AOIs, managing source/AOI relationships, generating tile grids with `ST_SquareGrid`, computing tile extents and metadata, creating run records, and generating or supporting the JSON contents used by downstream engine/runtime importers.

The database remains the authoritative state record. Files on disk are supporting inputs, outputs, logs, and portable artifacts.

---

## 2. Concepts and Artifacts

### 2.1 Core Design Principles

#### One tool, separated modes

The workflow should be implemented as one tool with three major modes.

The modes are separated by responsibility, not by unrelated scripts:

* Mode 1 (raster registration) registers source elevation datasets.
* Mode 2 (AOI registration) registers reusable project boundaries.
* Mode 3 (terrain package operations) manages terrain-package planning, realization, export, validation, and re-export.

This keeps the workflow reproducible and easier to validate, while still allowing each mode to remain conceptually clean.

#### Database-centered, not database-only

The workflow is database-centered, but not everything belongs inside the database.

The database should store:

* registered source dataset metadata
* registered source file metadata
* registered AOI definitions
* run/session records
* tile plans
* realized/exported tile metadata
* optional derived raster payloads
* status fields
* artifact paths
* checksums
* validation results

The filesystem should store:

* source material:
	* original source rasters, unless explicitly loaded into PostGIS
	* virtual mosaics such as VRT files
* workflow output:
	* terrain packages, each consisting of:
	  * **exported RAW files (primary terrain output)**
	  * **generated `manifest-rule.json` (interprets terrain package)**
	  * **generated `tile-catalog.json`  (indexes terrain package tiles)**
	* optional GeoPackage tile grids
	* logs
	* other portable output artifacts

The normal default should be:

**Store metadata and provenance in the database. Keep large source raster files on disk unless there is a specific reason to load them into PostGIS.**

#### Engine/runtime-neutral terrain production

The terrain-production workflow should not be hard-coded to one engine or SDK.

Mode 1 and Mode 2 are engine-neutral.

Mode 3 chooses a target engine/runtime profile when runtime-facing artifacts need to be generated.

Initial supported runtime profiles should be:

1. Unity with ArcGIS Maps SDK for Unity
2. Unity with Cesium for Unity

Additional profiles can be added later, such as:

* Unity local-only/no geospatial SDK
* Unreal with ArcGIS Maps SDK for Unreal Engine
* Unreal with Cesium for Unreal
* Unreal native georeferencing
* custom importer profile

The workflow working CRS remains the authority for terrain production unless the user explicitly chooses a reprojection-based terrain-production workflow.

The target runtime profile determines how the finished package describes itself to the downstream engine or SDK.

In plain terms:

**The workflow produces terrain packages for game engines. Unity is the first practical target, not the only conceptual target.**

---

### 2.2 Core Database Tables at a Glance

The first implementation should use these core database tables:

* `source_raster_datasets`
* `source_raster_files`
* `aoi_definitions`
* `terrain_tile_runs`
* `terrain_tile_grid_plan`
* `terrain_tile_grid_outputs`
* `terrain_tile_grid_rasters`

If `postgis_raster` source storage is implemented in the first version, the database should also include:

* `source_raster_payloads`

This table would store original registered source raster payloads loaded into PostGIS. It should be kept separate from `terrain_tile_grid_rasters`, which stores generated terrain-tile rasters, not original source rasters.

These tables correspond to the main workflow objects described in the next section.

Optional/helper tables can be added later:

* `terrain_run_artifacts` 
* `terrain_runtime_profiles`
* `terrain_validation_events`
* `terrain_tile_source_contributions`

If repeated exports from the same stored raster session become common, export events could later be tracked either in `terrain_run_artifacts` or in a dedicated `terrain_tile_export_events` table. This is not required for the first implementation.

If detailed per-tile source provenance becomes important, `terrain_tile_source_contributions` could record which registered source raster files contributed to each realized terrain tile. For the first implementation, that information can remain in `terrain_tile_grid_outputs` metadata or be omitted.

For the first implementation, artifact paths and runtime profile metadata can remain in `terrain_tile_runs` and JSONB fields unless normalization becomes useful later.


---

### 2.3 Major Workflow Objects and Their Storage

The workflow distinguishes between several related but separate objects. Some are stored directly in database tables, while others are exported filesystem artifacts.

#### Source raster dataset

The named source elevation surface registered by Mode 1 (raster registration).

Stored primarily in the database table:

* `source_raster_datasets`

For external raster datasets, the physical source files are tracked in:

* `source_raster_files`

A source raster dataset is the logical terrain/elevation source selected later by `source_dataset_id`.

#### Source raster files

The physical raster files that make up a source raster dataset.

Stored in the database table:

* `source_raster_files`

For a single-file dataset, this table has one row. For a tiled source dataset, this table has one row per registered source raster file.

#### AOI definition

A reusable project boundary registered by Mode 2 (AOI registration).

Stored in the database table:

* `aoi_definitions`

An AOI definition is selected later by `aoi_id`.

#### Terrain package run/session

A Mode 3 terrain-package operation.

Stored in the database table:

* `terrain_tile_runs`

A run/session records the selected source dataset, AOI, operation type, workflow CRS, runtime profile, terrain-production settings, output location, status, and artifact checksums.

#### Tile plan

The intended terrain grid.

Stored in the database table:

* `terrain_tile_grid_plan`

A tile plan can exist without realized raster tiles or exported RAW files.

#### Output metadata

The record of what was realized or exported.

Stored in the database table:

* `terrain_tile_grid_outputs`

Output metadata can exist without storing raster payloads in the database.

#### Stored derived raster payloads

Optional generated raster tiles stored in PostGIS.

Stored in the database table:

* `terrain_tile_grid_rasters`

This table is optional and potentially heavy. It stores generated terrain rasters, not the original source rasters.

#### Exported files

Portable artifacts written to disk, such as:

* RAW terrain tiles
* `manifest-rule.json`
* `tile-catalog.json`
* tile grid GeoPackage
* logs

These are filesystem artifacts, not primary database tables. They can exist with or without retaining derived raster payloads in the database.

The database should record important exported artifact paths, checksums, and validation status.

---
### 2.4 Requested Actions Versus Completed State

The schema should distinguish requested actions from completed state.

Requested-action fields record what the user or workflow intended to do. Completed-state fields record what actually happened. This distinction matters for failed, interrupted, partial, resumed, and validation-only runs.

Requested/completed pairs should use parallel field names so the relationship is clear at a glance.

Preferred pattern:

```text
<stage_or_artifact>_<action>_requested
<stage_or_artifact>_<action>_completed
```

For example:

* `tile_plan_creation_requested` versus `tile_plan_creation_completed`
* `raster_tile_realization_requested` versus `raster_tile_realization_completed`
* `derived_raster_storage_requested` versus `derived_raster_storage_completed`
* `raw_file_export_requested` versus `raw_file_export_completed`
* `manifest_rule_generation_requested` versus `manifest_rule_generation_completed`
* `tile_catalog_generation_requested` versus `tile_catalog_generation_completed`
* `tile_grid_geopackage_export_requested` versus `tile_grid_geopackage_export_completed`

For example:

* `derived_raster_storage_requested = true` means the user or workflow requested database storage of derived raster tiles.
* `derived_raster_storage_completed = false` means that storage did not complete, even though it was requested.

This lets the database record both intent and outcome without relying only on logs or filesystem inspection.

Requested/completed field pairs should be supported by broader status fields such as:

* `operation_status`
* `validation_status`
* `failure_reason`
* `last_error_message`

The requested/completed pairs record **what was intended and whether each stage finished**.

The status/error fields record **the overall run state and the reason for failure, partial completion, or validation problems**.

For example:

```text
raw_file_export_requested = true
raw_file_export_completed = false
operation_status = failed
failure_reason = raw_export_failed
last_error_message = "Unable to write terrain_r2_c4.raw because the output folder was not writable."
```

Best rule:

**Use mirrored requested/completed field pairs for major workflow stages and artifact outputs. Use status/error fields to explain the overall run condition and any failure reason.**

---

### 2.5 Recommended Project and Output Folder Structure

The project should use a clear folder structure because the workflow deliberately combines database records, schema-preparation files, source files, configuration files, generated artifacts, and logs.

Suggested structure:

```text
project_root/
  terrain_tool.py

  db/
    schema.sql
    db_prepare.py
    db_check.py

  config/
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

  terrain_packages/
    <run_id>/
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

The `db/` folder contains reproducible database-preparation files. It is separate from `terrain_tool.py` because schema setup is a prerequisite, not one of the three terrain workflow modes.

Source rasters do not necessarily need to live inside `project_root/`. For large datasets, they may remain in external GIS data folders and be referenced by `source_root_path` plus file-level `relative_path`.

For example:

```text
D:/GIS/Eryri/DTM/tiles/
  SN65_DTM_1m.tif
  SN66_DTM_1m.tif
  SN67_DTM_1m.tif
```

The database records where those sources are and how they should be accessed.

---
### 2.6 Policies

#### Configuration Policy

The tool should use human-editable configuration files for stable local settings that should not be repeatedly entered at the command line.

Configuration files should be stored under:

```text
config/
  database_config.yaml
  tool_config.yaml
```

The preferred configuration format is **YAML**.

YAML is appropriate here because it is broadly familiar in Python, GIS-adjacent, data-engineering, DevOps, and conda workflows. It is easier for humans to read and edit than JSON while remaining structured enough for machine parsing.

JSON should remain the format for strict machine artifacts such as `manifest-rule.json` and `tile-catalog.json`. YAML should be used for editable tool configuration, not for terrain-package manifests or catalogs.

Configuration files should support both:

* database preparation and readiness checks
* normal terrain workflow operations

In practical terms:

* `db_prepare.py` should read database connection settings from `config/database_config.yaml`.
* `db_check.py` should read database connection settings from `config/database_config.yaml`.
* `terrain_tool.py` should read database connection settings from `config/database_config.yaml` and tool defaults from `config/tool_config.yaml`.

`database_config.yaml` should store database connection defaults and related database-access settings.

Example `database_config.yaml`:

```yaml
database:
  host: "localhost"
  port: 5432
  name: "terrain_tool_database"
  user: "user"
  password_env_var: "TERRAIN_TOOL_PASSWORD"

schema:
  name: "public"
```

`tool_config.yaml` should store tool behavior defaults, paths, logging settings, and expected schema information.

Example `tool_config.yaml`:

```yaml
paths:
  default_output_root: "D:/GIS/GEOG670/terrain_packages"
  schema_sql_path: "db/schema.sql"

logging:
  level: "INFO"
  verbose: false

defaults:
  path_storage_mode: "root_plus_relative"
  manifest_schema_version: "0.4.0"
  tile_catalog_schema_version: "0.4.0"
  expected_database_schema_version: "0.1.0"
```

Configuration files may store:

* database connection defaults
* database schema name
* path to `schema.sql`
* expected database schema version
* default output root folders
* logging defaults
* default path-handling behavior
* default JSON schema versions
* optional project-level defaults

Configuration files should not replace database records. Registered source datasets, registered AOIs, terrain-package runs, tile plans, output metadata, checksums, and validation state belong in PostgreSQL/PostGIS.

Configuration files should also not replace `manifest-rule.json` or `tile-catalog.json`. Those JSON files are exported package artifacts and recovery/interpretation handles.

Passwords should not be written directly into project configuration files if avoidable. The preferred pattern is to store the name of an environment variable, such as `GEOG670_DB_PASSWORD`, and let Python read the password from the environment.

Strings, file paths, dates, CRS labels, schema versions, and values such as `"yes"`, `"no"`, `"on"`, or `"off"` should be quoted to avoid accidental type interpretation.

Best rule:

**YAML is for human-edited local configuration. JSON is for strict exported machine artifacts. PostgreSQL/PostGIS remains the authoritative workflow state. Database-preparation scripts and terrain workflow scripts should read shared configuration rather than duplicating connection settings.**

---

#### JSON Artifact Policy

The workflow should use strict JSON for machine-read artifacts.

Primary JSON artifacts:

* `manifest-rule.json`
* `tile-catalog.json`

These files should not contain comments, Markdown syntax, or non-JSON extensions.

`manifest-rule.json` should be treated as the standard Mode 3 recovery/control artifact for package-producing operations. It should normally be generated, copied, or rewritten whenever Mode 3 creates a tile plan artifact, exports terrain-package files, re-exports stored rasters, or produces a compatible alternate runtime package.

For Mode 3E (validate or re-export from `manifest-rule.json`), the manifest is the input recovery handle. That branch should not routinely regenerate the same manifest in place, but it may write a fresh manifest into a new output folder when re-exporting or producing an alternate runtime-facing package.

Human-readable explanation may be included selectively through explicit JSON fields such as:

* `description`
* `note`
* `provenance_note`
* `warning`
* `*_note`

This is especially appropriate in `manifest-rule.json`, because that file acts as a human-auditable recovery and control artifact.

For `tile-catalog.json`, explanatory metadata should mostly stay outside the repeated `tiles` array. Per-tile notes should be used only when the note is tile-specific, such as edge padding, unusual source coverage, or validation warnings.

Comprehensive field explanations should live in companion documentation files, such as:

```text
docs/
  manifest-rule.schema-notes.md
  tile-catalog.schema-notes.md
```

Best rule:

**Machine-read files stay strict JSON. Selective in-JSON descriptions prevent misinterpretation. Full explanations belong in companion schema notes.**

---

#### Artifact Tracking Policy

The database should record important artifact paths, checksums, and validation status.

For the first implementation, `terrain_tile_runs` can store run-level artifact fields such as:

* `manifest_rule_sha256`
* `tile_catalog_sha256`
* `output_root_folder`
* `computed_output_folder`
* `log_file_path`

Per-tile artifact fields, such as RAW filenames, relative paths, expected file sizes, actual file sizes, SHA-256 values, and export status, should be stored in `terrain_tile_grid_outputs`.

Later, if artifact tracking becomes more complex, a helper table such as `terrain_run_artifacts` can be added.

A possible later `terrain_run_artifacts` table would track:

* artifact type
* relative path
* absolute path
* file size
* SHA-256 checksum
* validation status
* creation time
* artifact metadata

For the first version, keep artifact tracking simple unless the workflow starts producing many artifact types per run.

Best rule:

**The filesystem stores exported artifacts. PostgreSQL/PostGIS records where important artifacts are, what they represent, and whether they validated.**

---

#### Logging Policy

Logging should be always on at a normal `INFO` level.

Verbose/debug logging should be optional.

The database is the authoritative record of registered datasets, AOIs, runs, statuses, artifact paths, checksums, and validation results. Logs are supporting diagnostic artifacts that explain how an operation unfolded.

The tool should maintain:

* one general append log for the whole tool
* one append log per mode
* one per-session log for Mode 3 package operations when a `session_id` exists

Suggested global logs:

```text
logs/
  terrain_tool.log
  mode1_raster_registration.log
  mode2_aoi_registration.log
  mode3_terrain_package_operations.log
```

Suggested Mode 3 package-specific log:

```text
terrain_packages/<run_id>/logs/<session_id>.log
```

Default `INFO` logs should record:

* mode started
* selected operation
* IDs used or created
* important user choices
* source dataset selected
* AOI selected
* source storage mode
* target engine/runtime profile, when applicable
* output folder
* files checked
* counts of files found or missing
* major database operations completed
* artifacts written
* checksums computed
* validation result
* warnings and errors

Optional verbose/debug logs may record:

* detailed SQL calls
* file-by-file checks
* GDAL/rasterio command details
* CRS transformation details
* timings for each processing step
* full stack traces

Best rule:

**INFO logs are always written. Verbose mode adds DEBUG detail. The database remains authoritative; logs are supporting diagnostic artifacts.**

---