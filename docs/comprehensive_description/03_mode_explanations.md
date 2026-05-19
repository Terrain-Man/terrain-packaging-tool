
## 4. Detailed Mode Explanations

### 4.1 Mode Summary

#### Mode 1 (raster registration)

Mode 1 creates or updates the source raster library.

It registers one source elevation dataset under a `source_dataset_id`.

The source registry is split into two related tables:

* `source_raster_datasets`
* `source_raster_files`

The conceptual distinction is:

**`source_raster_datasets` = the named source elevation surface that later workflow stages select.**

**`source_raster_files` = the physical raster files that make up that source surface.**

Mode 1 is upstream and engine-neutral.

#### Mode 2 (AOI registration)

Mode 2 creates or updates reusable AOI records.

It registers one AOI under an `aoi_id`.

The AOI should be normalized into the database, regardless of whether it began as:

* a GeoPackage layer
* a shapefile
* GeoJSON
* KML
* manual bounding box coordinates
* a source raster extent

Mode 2 is upstream and engine-neutral.

#### Mode 3 (terrain package operations)

Mode 3 creates, manages, exports, validates, or re-exports terrain packages.

It uses:

* a registered `source_dataset_id`
* a registered `aoi_id`
* a selected terrain-package operation
* a workflow working CRS
* a target engine/runtime profile when runtime-facing artifacts are generated

Mode 3 manages separable stages:

1. **Plan** — create or select the tile grid.
2. **Realize** — create raster tiles from the selected source dataset, AOI, and tile plan.
3. **Persist** — optionally store realized raster tiles in `terrain_tile_grid_rasters`.
4. **Export** — write files such as RAW tiles, `manifest-rule.json`, `tile-catalog.json`, logs, and optional GeoPackage artifacts.
5. **Validate** — check database records, generated artifacts, file sizes, checksums, source coverage, and runtime metadata.

Mode 3 also manages runtime-profile metadata generation and validation.

Source raster storage mode determines how elevation pixels are accessed.

The source registry tables determine where dataset-level and file-level source metadata are found.

The target runtime profile determines how the finished package describes its placement to an engine or SDK.

These concepts should not be collapsed into one menu choice.

### 4.2 Relationship Between Modes

Mode 1 and Mode 2 are reusable preparation stages.

Mode 3 is the production and management stage.

Mode 1 should answer:

**“What elevation sources does this project know about?”**

Mode 2 should answer:

**“What reusable project boundaries does this workflow know about?”**

Mode 3 should answer:

**“Using registered source data and a registered AOI, what terrain package operation should be performed?”**

Mode 3 should not begin by asking for arbitrary one-off raster files or one-off AOIs. It should use registered database records as the source of truth.

### 4.3 Mode 1: Register Source Raster Dataset

Mode 1 creates or updates the source raster library. 

Its purpose is to take one or more source elevation rasters and register them in the database so later terrain-package runs can refer to them by `source_dataset_id`.

Mode 1 is **upstream and engine-neutral**. It should not ask which game engine, SDK, or runtime profile will eventually consume the terrain package. Those decisions belong to Mode 3 (terrain package operations).

**Registration does not automatically mean storing the raster pixels inside PostgreSQL/PostGIS.** The default behavior should be to register external raster files while storing their metadata, provenance, validation information, and file references in the database.

Storing the actual raster payload in PostGIS should be an optional advanced choice, not the default.

Mode 1 should use two related source-registration tables:

* `source_raster_datasets`
* `source_raster_files`

The conceptual distinction is:

**`source_raster_datasets` = the named source elevation surface that later workflow stages select.**
**`source_raster_files` = the physical raster files that make up that source surface.**

For example, a folder of 361 DTM GeoTIFF tiles would become:

* one row in `source_raster_datasets`
* 361 rows in `source_raster_files`

A single merged GeoTIFF would become:

* one row in `source_raster_datasets`
* one row in `source_raster_files`

In plain terms:

**Mode 1 says, “Here are the elevation sources this project knows about, where they are stored, how they should be accessed, and what their spatial properties are.”**

#### Mode 1 should ask for

* `source_dataset_id`
* source dataset name
* source type, such as DTM, DSM, DEM, bathymetry, or other
* input path:

  * one GeoTIFF
  * a folder of GeoTIFF tiles
  * a list or CSV of GeoTIFF paths
* source storage mode:

  * `external_file`
  * `external_files`
  * `virtual_mosaic`
  * `postgis_raster`
* source root path handling, when registering external files:

  * enter `source_root_path` manually, default
  * infer `source_root_path` from listed file paths, then confirm
  * store absolute paths only, with portability warning
* expected CRS, or whether to derive CRS from the files
* whether files with mismatched CRS should be rejected or flagged for review
* whether to create a virtual mosaic, such as a GDAL VRT, when registering multiple files, or to record one if one already exists, or to do neither. NOTE: PostGIS can record VRTs, but if they must be computed and created, that is done by GDAL, and then subsequently recorded in the database by PostGIS
* optional description or provenance note

Mode 1 should **not** ask for:

* target engine
* target geospatial runtime
* Unity settings
* ArcGIS Maps SDK settings
* Cesium settings
* RAW export settings
* heightmap resolution
* tile size
* runtime origin
* engine-local placement rules

Those belong to Mode 3.

#### Source storage modes

##### `external_file`

The source dataset is one external raster file, such as a single GeoTIFF or COG.

This could be an original raster file, or it could be a raster that was already mosaicked before registration. If it was previously merged from many tiles, that fact should be recorded as provenance, but it does not need a separate operational storage mode.

Database effect:

* one row in `source_raster_datasets`
* one row in `source_raster_files`

Mode 3 can read this file directly when building terrain tiles.

##### `external_files`

The source dataset is a collection of external raster files registered as one dataset.

For example, a folder of DTM tiles can be registered under one `source_dataset_id`. The database records each file’s path, extent, CRS, cell size, NoData value, dimensions, and checksum.

Database effect:

* one row in `source_raster_datasets`
* one row per source file in `source_raster_files`

Mode 3 must select, mosaic, clip, or resample the relevant files when building terrain tiles.

##### `virtual_mosaic`

The source dataset consists of multiple external files, but Mode 1 creates or records a virtual mosaic reference, such as a GDAL VRT.

The VRT acts like one raster surface for GDAL/rasterio/QGIS processing, but it does not duplicate the source raster pixels.

Database effect:

* one row in `source_raster_datasets`
* one row per original source file in `source_raster_files`
* dataset-level VRT path or VRT metadata recorded in `source_raster_datasets`

Mode 3 can read from the VRT as if it were a single raster while the original files remain separate on disk.

##### `postgis_raster`

The source raster pixels are loaded into PostGIS.

Mode 3 reads the source elevation values from the database rather than from external raster files.

This may be useful for small test datasets, demonstrations of PostGIS raster capabilities, or SQL-based raster experiments, but it should not be the default for large source datasets.

Database effect:

* one row in `source_raster_datasets`
* file provenance rows in `source_raster_files`, if the raster was loaded from external files and those source files should remain traceable
* raster payload stored in PostGIS using the chosen source-raster storage design

For the first version, `postgis_raster` can remain an advanced option. The normal path should be external registration plus metadata, not loading large raster payloads into the database.

#### Source root path handling

When registering external files, Mode 1 should store paths in a way that supports later path repair if the dataset is moved.

The preferred structure is:

* dataset-level `source_root_path`, stored in `source_raster_datasets`
* file-level `relative_path`, stored in `source_raster_files`

The full path can then be reconstructed as:

```text
source_root_path + relative_path
```

This is better than storing only absolute paths because, if the dataset moves to another folder, drive, or machine, the user may only need to update `source_root_path` rather than correcting every file record individually.

#### Single-file input

If the user selects one GeoTIFF, Mode 1 should use the file’s parent folder as the default `source_root_path`.

Example:

```text
D:\GIS\Eryri\DTM\eryri_dtm_merged.tif
```

Stored as:

```text
source_root_path = D:\GIS\Eryri\DTM
relative_path = eryri_dtm_merged.tif
```

The dataset-level facts go in `source_raster_datasets`.

The file-level facts go in `source_raster_files`.

The tool may show this to the user, but this case does not need much extra prompting.

#### Folder input

If the user selects a folder of GeoTIFF tiles, Mode 1 should use the selected folder as the default `source_root_path`.

Example:

```text
D:\GIS\Eryri\DTM\tiles\
```

Files inside that folder are stored with paths relative to that root.

Example relative paths:

```text
SN65_DTM_1m.tif
SN66_DTM_1m.tif
SN67_DTM_1m.tif
```

If the folder contains subfolders, those subfolder paths should be preserved as part of `relative_path`.

The selected folder becomes the dataset-level `source_root_path`.

Each GeoTIFF becomes one file-level record in `source_raster_files`.

#### CSV or list input

If the user provides a CSV or list of file paths, Mode 1 should not assume that the correct root path is obvious.

The prompt should be:

```text
How should the source root path be set?

1. Enter source_root_path manually, default
2. Infer source_root_path from listed file paths, then confirm
3. Store absolute paths only — warning: reduces portability and may require manual correction if files are moved
```

Manual entry should be the default for now.

If the user chooses manual entry, Mode 1 should ask for `source_root_path`, then validate that the listed files can be expressed relative to that root.

Example validation output:

```text
Files inside source_root_path: 361
Files outside source_root_path: 0

Example relative paths:
SN65_DTM_1m.tif
SN66_DTM_1m.tif
SN67_DTM_1m.tif

Use this source_root_path? yes/no
```

If the user chooses inference, Mode 1 should infer the longest useful common parent path, present it to the user, and ask for confirmation.

Example inference output:

```text
Inferred source_root_path:
D:\GIS\Eryri\DTM\tiles

Example relative paths:
SN65_DTM_1m.tif
SN66_DTM_1m.tif
SN67_DTM_1m.tif

Use this source_root_path? yes/no
```

If the inferred root is too broad, such as a drive root or filesystem root, the tool should warn that no useful common source root could be inferred and ask the user to enter one manually or choose another option.

If the user chooses absolute path storage, Mode 1 should give a second confirmation warning:

```text
You have selected absolute path storage.

This records each source file using its full current path. If the files are moved to another folder, drive, or machine, later terrain-package operations may fail until the paths are manually corrected or the dataset is re-registered.

Proceed with absolute paths only? yes/no
```

Absolute path storage should be recorded as a path storage mode, not silently treated as equivalent to the preferred root-plus-relative structure.

#### CRS handling

Mode 1 should record the CRS of each source raster.

It should ask whether the expected CRS should be:

* entered by the user
* derived from the raster files
* derived from the first file and then checked against the rest of the dataset

For a single-file dataset, Mode 1 should read and record the file CRS.

For a multi-file dataset, Mode 1 should verify that all files use a compatible CRS. A mismatched CRS should not be silently accepted.

The user should be able to choose whether CRS mismatches are:

* rejected immediately
* flagged for review
* allowed only if the workflow records an explicit planned reprojection step later

The default should be to reject mismatched CRS for a single registered source dataset unless the user explicitly chooses a review or reprojection-aware workflow.

Mode 1 should not transform source rasters merely because a later engine/runtime might prefer a different coordinate model. Runtime-specific transformation belongs to Mode 3.

#### Mode 1 database responsibilities

Mode 1 should create or update dataset-level records in `source_raster_datasets`.

Dataset-level responsibilities include recording:

* `source_dataset_id`
* source dataset name
* source type
* `source_storage_mode`
* source CRS
* source cell size
* source NoData value
* source extent
* dataset-level metadata
* source root path, where applicable
* path storage mode
* primary source path, where applicable
* VRT path, where applicable
* file count
* whether a virtual mosaic exists
* whether source raster pixels are stored in PostGIS
* registration status
* validation status
* provenance notes

Mode 1 should also create or update file-level records in `source_raster_files`.

File-level responsibilities include recording, for each physical source raster file:

* `source_dataset_id`
* filename
* relative path
* absolute path, if absolute-path storage is explicitly selected
* file existence/readability status at registration
* file size
* file modified time
* file checksum
* file CRS
* file cell size
* file NoData value
* raster width and height
* raster band count
* raster data type
* file extent
* whether the file is part of a virtual mosaic
* registration notes
* validation status

Mode 1 should validate that:

* referenced files exist and are readable
* the dataset is internally consistent
* all files in a multi-file dataset share compatible CRS
* all files in a multi-file dataset share compatible cell size
* all files in a multi-file dataset have compatible NoData handling
* resolution expectations are consistent enough for later terrain-package operations
* a virtual mosaic, if created, can be opened by GDAL/rasterio
* the VRT-referenced files are registered and reachable

Mode 1 should not record runtime-profile metadata such as:

* `target_engine`
* `target_geospatial_runtime`
* `runtime_origin`
* engine-local axis mappings
* ArcGIS-specific placement fields
* Cesium-specific georeference fields
* Unity terrain import settings

Those are Mode 3 concerns.

#### Default behavior

The default behavior should be:

**Register raster metadata and file paths only.**

For a single file, this means:

* `source_storage_mode = external_file`
* one dataset row
* one file row

For many files, this means:

* `source_storage_mode = external_files`
* one dataset row
* one file row per source raster file

For many files where a VRT is created or registered, this means:

* `source_storage_mode = virtual_mosaic`
* one dataset row
* one file row per original source raster file
* VRT path recorded at the dataset level

For CSV/list input, the default path-handling method should be manual entry of `source_root_path`, not automatic inference.

This keeps the database lightweight while preserving the database-centered workflow. The database still acts as the authoritative catalog for source selection, CRS checks, extents, provenance, coverage checks, and later terrain-package runs.

#### Optional virtual mosaic behavior

If the source dataset contains many raster tiles, Mode 1 may offer to create a virtual mosaic.

This is useful because it lets Mode 3 treat many source tiles as one continuous raster surface without creating a large merged GeoTIFF and without loading the pixels into PostGIS.

In plain terms:

**A VRT gives the workflow the convenience of a mosaic without the storage cost of a physical mosaic.**

The VRT should be registered as part of the source dataset metadata. The original source files should still remain traceable through `source_raster_files`.

#### Optional in-database raster storage

The user may choose to load raster pixels into PostGIS.

This may be appropriate for:

* small test rasters
* demonstration of PostGIS raster capabilities
* SQL-based raster experiments
* workflows where database-contained raster storage is more important than keeping the database lightweight

This should not be the normal default for large source rasters, because it can greatly increase database size, backup size, restore time, and maintenance overhead.

If the raster was loaded from external files, the original files may still be recorded in `source_raster_files` as provenance, even if Mode 3 later reads the raster pixels from PostGIS.

#### Relationship to later terrain-package operations

Mode 1 prepares source rasters for later use by Mode 3.

Mode 3 may later use the registered source dataset to:

* create a tile plan
* build raster tiles
* export RAW files
* store derived raster tiles
* generate `manifest-rule.json`
* generate `tile-catalog.json`
* validate or re-export a terrain package
* write runtime-specific georeferencing metadata

Mode 3 selects the source dataset by `source_dataset_id`.

Internally, Mode 3 reads dataset-level metadata from `source_raster_datasets`. If raster pixels or file checks are needed, Mode 3 then reads the relevant file-level records from `source_raster_files`.

For example:

* `external_file`: Mode 3 reads one file row.
* `external_files`: Mode 3 reads the subset of file rows needed for the AOI or tile grid.
* `virtual_mosaic`: Mode 3 reads the dataset-level VRT path and may verify the registered source files behind the VRT.
* `postgis_raster`: Mode 3 reads the source raster payload from PostGIS and may use file rows only for provenance.

Mode 1 itself should remain independent of the eventual target engine or runtime profile.

The same `source_dataset_id` should be reusable for:

* Unity with ArcGIS Maps SDK for Unity
* Unity with Cesium for Unity
* a local-only Unity terrain package
* Unreal-oriented terrain-package experiments
* future custom runtime profiles

The source dataset should not need to be re-registered merely because the downstream runtime changes.

#### Mode 1 output

The output of Mode 1 is a registered **source dataset** that later runs can select by `source_dataset_id`.

That source dataset may refer to:

* one external raster file, `external_file`
* many external raster files, `external_files`
* a virtual mosaic reference, `virtual_mosaic`
* raster pixels stored directly in PostGIS, `postgis_raster`

For external file registrations, the dataset should also record how the file paths are stored:

* `source_root_path` plus file-level `relative_path`, preferred
* absolute paths only, fallback option with portability warning

In database terms, Mode 1 outputs:

* one dataset-level record in `source_raster_datasets`
* zero, one, or many file-level records in `source_raster_files`, depending on storage mode and provenance needs

In plain terms:

**Mode 1 says, “Here are the terrain/elevation sources this project knows about, where they are stored, how they should be accessed, what their spatial properties are, and whether their pixels live inside or outside the database.”**

Mode 1 should append to `logs/mode1_raster_registration.log`.

The log should record the selected input path, source storage mode, source root path handling, number of files registered, validation results, and created or updated `source_dataset_id`.
---

### 4.4 Mode 2: Register AOI Definition

Mode 2 creates or updates reusable AOI records.

Its purpose is to define the spatial boundary that later terrain-package runs will use. The AOI should be normalized into the database, regardless of whether it began as a GeoPackage layer, shapefile, GeoJSON, KML, bounding box, or source raster extent.

Mode 2 is **upstream and engine-neutral**. It should not ask which game engine, SDK, or runtime profile will eventually consume the terrain package. Those decisions belong to Mode 3 (terrain package operations).

In plain terms:

**Mode 2 says, “Here are the reusable project boundaries this workflow knows about.”**

#### Mode 2 should ask for

* `aoi_id`
* AOI name
* AOI source:

  * imported polygon file
  * existing vector file
  * bounding box coordinates
  * derived from a source raster extent
* CRS, read from the file if present
* whether to transform the AOI to the workflow working CRS
* optional description or note

Mode 2 should **not** ask for:

* target engine
* target geospatial runtime
* Unity settings
* ArcGIS Maps SDK settings
* Cesium settings
* RAW export settings
* heightmap resolution
* tile size
* runtime origin
* engine-local placement rules

Those belong to Mode 3.

#### First-version supported AOI formats

1. GeoPackage `.gpkg`
2. Shapefile `.shp`
3. GeoJSON `.geojson`
4. KML `.kml`
5. Manual bounding box coordinates
6. Source raster extent, derived from a registered `source_dataset_id`

GeoPackage is acceptable, but because it can contain many layers, the script should require explicit layer selection. The selected layer must contain polygon or multipolygon geometry. Points or lines should be rejected for AOI use.

For file-based AOIs, Mode 2 should inspect the available layers and geometry types before registration.

For manual bounding boxes, Mode 2 should require the user to specify the CRS of the entered coordinates.

For AOIs derived from a source raster extent, Mode 2 should use the registered source raster metadata from Mode 1 (raster registration), not inspect an arbitrary raster file outside the source registry.

#### AOI geometry requirements

The AOI should be stored as polygon or multipolygon geometry.

Mode 2 should reject:

* point geometries
* line geometries
* empty geometries
* invalid geometries that cannot be repaired or explicitly accepted
* geometries with unknown CRS unless the user supplies the CRS

Mode 2 may optionally repair simple geometry validity problems, but it should report that it did so.

For example:

* self-intersection repaired
* ring orientation normalized
* multipolygon dissolved into one AOI geometry
* geometry transformed to the workflow working CRS

If geometry repair changes the shape meaningfully, the tool should warn the user and require confirmation before registration.

#### CRS handling

Mode 2 should record both the AOI source CRS and the AOI working CRS.

The AOI source CRS is the CRS in which the AOI was originally supplied.

The AOI working CRS is the CRS used by the workflow for later database operations, tile planning, and terrain-package geometry.

The workflow working CRS may be:

* explicitly entered by the user
* selected from a registered source raster dataset
* inferred from the source raster dataset used for the intended terrain workflow
* inherited from a project default, if the project later supports default settings

A CRS mismatch is not automatically fatal.

For example, if the AOI is supplied in WGS84 and the source raster is in EPSG:27700, that is not an error. The tool should warn the user, transform the AOI deliberately into the workflow working CRS, and record the transformation.

Unknown or untransformable CRS is fatal unless the user explicitly supplies the CRS.

#### CRS rule

**CRS mismatch is not fatal. Unknown or untransformable CRS is fatal unless the user explicitly supplies the CRS.**

Mode 2 should not silently assume that an AOI CRS is correct merely because the coordinates appear plausible.

Mode 2 should also not transform AOIs merely because a later runtime profile may need WGS84, ECEF, or another engine-specific coordinate representation. Runtime-specific georeferencing belongs to Mode 3.

For example:

* EPSG:27700 AOI → EPSG:27700 working CRS: no transformation needed
* EPSG:4326 AOI → EPSG:27700 working CRS: transform and record transformation
* unknown CRS AOI → no user-supplied CRS: stop
* unknown CRS AOI → user supplies EPSG code: record the user-supplied CRS and continue if transformation succeeds

#### Mode 2 database responsibilities

Mode 2 should use PostgreSQL/PostGIS to:

* create or update records in `aoi_definitions`
* record `aoi_id`
* record AOI name
* record AOI source type
* store AOI geometry
* validate geometry
* optionally store original geometry
* store transformed working geometry
* record source CRS
* record working CRS
* record transformation metadata, if transformation occurred
* compute AOI area in working CRS units
* compute AOI bounding box in the working CRS
* optionally compute AOI centroid in the working CRS
* optionally compare AOI extent against a registered source raster’s coverage
* record description, notes, and provenance

Mode 2 should not record runtime-profile metadata such as:

* `target_engine`
* `target_geospatial_runtime`
* `runtime_origin`
* engine-local axis mappings
* ArcGIS-specific placement fields
* Cesium-specific georeference fields
* Unity terrain import settings

Those are Mode 3 concerns.

#### Optional source raster extent comparison

Mode 2 may optionally compare the AOI extent against a registered source raster dataset.

This can be useful for early validation, especially when the AOI is intended for a known source dataset.

However, this comparison should not make the AOI permanently dependent on that source dataset unless the user explicitly wants that relationship recorded.

The comparison should report:

* whether the AOI intersects the source raster coverage
* whether the AOI is fully inside the source raster coverage
* whether the AOI extends beyond the source raster coverage
* approximate overlap area or coverage percentage, if useful
* CRS transformation used for the comparison, if applicable

This is an optional validation convenience, not a replacement for Mode 3 coverage checks.

Mode 3 must still validate source coverage for the actual selected source dataset and tile grid before building raster tiles.

#### AOI source types

##### Imported polygon file

The AOI comes from a vector file such as GeoPackage, Shapefile, GeoJSON, or KML.

The tool should:

* read available layers if the format supports layers
* require explicit layer selection for GeoPackage
* verify polygon or multipolygon geometry
* read CRS from the file if available
* ask for CRS if missing
* validate geometry
* transform to the workflow working CRS if needed
* store the result in `aoi_definitions`

##### Existing vector file

This is similar to imported polygon file, but may refer to a file already used elsewhere in the project.

The tool should still validate geometry and CRS. It should not assume that a previously used vector file is valid for AOI registration.

##### Manual bounding box coordinates

The AOI is entered as numeric bounds.

Mode 2 should ask for:

* xmin
* ymin
* xmax
* ymax
* CRS of the entered coordinates
* intended workflow working CRS

The tool should validate that:

* xmin is less than xmax
* ymin is less than ymax
* coordinates are plausible for the declared CRS
* the resulting polygon is valid

Manual bounding boxes should be stored as polygon geometry, not merely as four numeric fields.

##### Derived from source raster extent

The AOI is derived from the extent of a registered source dataset.

Mode 2 should ask for:

* `source_dataset_id`
* whether to use the full source extent or a selected subset
* desired `aoi_id`
* AOI name
* optional description or note

The source raster extent should come from Mode 1 (raster registration) metadata.

This option is useful when the AOI should exactly match a known raster footprint or when creating a test AOI from source coverage.

The derived AOI should still be stored in `aoi_definitions` as an AOI record, so later Mode 3 operations can select it by `aoi_id`.

#### Default behavior

The default behavior should be:

**Store the AOI geometry in the workflow working CRS, while preserving enough source CRS/provenance information to understand where it came from.**

If the AOI’s source CRS and working CRS differ, the transformation should be deliberate and recorded.

If the AOI source CRS is unknown, the workflow should stop unless the user supplies it.

This keeps AOIs reusable across later terrain-package runs while preserving spatial provenance.

#### Relationship to later terrain-package operations

Mode 2 prepares AOIs for later use by Mode 3.

Mode 3 may later use the registered AOI to:

* create a tile plan
* build raster tiles
* determine package extent
* compute edge padding
* validate source coverage
* generate `manifest-rule.json`
* generate `tile-catalog.json`
* write runtime-specific georeferencing metadata

However, Mode 2 itself should remain independent of the eventual target engine or runtime profile.

For example, the same `aoi_id` should be reusable for:

* Unity with ArcGIS Maps SDK for Unity
* Unity with Cesium for Unity
* a local-only Unity terrain package
* Unreal-oriented terrain-package experiments
* future custom runtime profiles

The AOI should not need to be re-registered merely because the downstream runtime changes.

#### Mode 2 output

The output of Mode 2 is a registered **AOI definition** that later runs can select by `aoi_id`.

The AOI record should include:

* AOI ID
* AOI name
* AOI source type
* source CRS
* working CRS
* stored working geometry
* optional original geometry
* area
* bounding box
* transformation metadata, if applicable
* provenance notes

In plain terms:

**Mode 2 says, “Here are the reusable project boundaries this workflow knows about, in a normalized form that later terrain-package operations can safely use.”**

Mode 2 should append to `logs/mode2_aoi_registration.log`.

The log should record the AOI source, selected layer if applicable, source CRS, working CRS, transformation result, geometry validation result, and created or updated `aoi_id`.

---

### 4.5 Mode 3: Terrain Package Operations

Mode 3 is the main production and management mode.

It uses registered source datasets and registered AOIs to plan, realize, store, export, validate, or re-export terrain packages.

Mode 3 should not begin by asking for a random raster file or a one-off AOI. It should begin with a terrain-package operation, then use registered database records as the authoritative source of truth.

Mode 3 is organized around terrain-package operations, not around whether the source raster is stored inside or outside the database. The selected `source_dataset_id` already records its `source_storage_mode`, and Mode 3 should use that field internally to determine how raster pixels are accessed.

Mode 3 should also distinguish between:

* the **workflow working CRS**, used for database operations, tile planning, raster realization, and authoritative terrain-package extents
* the **target engine/runtime profile**, used for downstream placement in Unity or another engine
* the **source storage mode**, used to determine where the source elevation pixels come from
* the **source registry structure**, where dataset-level source metadata is stored separately from file-level source metadata

The working CRS remains the authority for terrain production unless the user explicitly chooses a reprojection-based terrain-production workflow. The target runtime profile determines how georeferencing metadata is written into `manifest-rule.json` and `tile-catalog.json`.

In plain terms:

**Mode 3 says, “Using registered source data and a registered AOI, create or manage a terrain package for a selected engine/runtime target.”**

#### Mode 3 stage vocabulary

Mode 3 is not merely a “make RAW files” operation. It manages terrain package runs through separable stages:

1. **Plan** — create or select the tile grid.
2. **Realize** — create raster tiles from source data, AOI geometry, and the tile plan.
3. **Persist** — optionally store realized raster payloads in `terrain_tile_grid_rasters`.
4. **Export** — write portable files such as RAW tiles, JSON artifacts, logs, and optional GeoPackage outputs.
5. **Validate** — check database records, generated artifacts, file sizes, checksums, source coverage, and runtime metadata.

Different Mode 3 operations combine these stages in different ways. A tile plan can exist without realized raster tiles. Output metadata can exist without stored raster payloads. Stored raster payloads can exist without RAW files having been exported. RAW files can exist without retaining raster payloads in the database.

Mode 3 may also include diagnostic or presentation exports that are derived from a tile plan but do not create terrain raster outputs. These exports should be clearly distinguished from runtime-facing terrain artifacts.

#### Mode 3 source registry lookup

Mode 3 selects source data by `source_dataset_id`.

The source registry is split into two related tables:

* `source_raster_datasets`
* `source_raster_files`

The distinction is:

**`source_raster_datasets` = the named source elevation surface Mode 3 selects.**
**`source_raster_files` = the physical raster files that make up that source surface.**

Mode 3 should first read dataset-level metadata from `source_raster_datasets`.

This includes:

* `source_dataset_id`
* source dataset name
* source type
* source storage mode
* source CRS
* source cell size
* source NoData value
* source extent
* source root path
* path storage mode
* VRT path, if applicable
* file count
* validation status
* provenance metadata

If the selected operation requires raster pixels or source-file accessibility checks, Mode 3 should then read relevant file-level records from `source_raster_files`.

For example:

* `external_file`: read one file row from `source_raster_files`
* `external_files`: read the subset of file rows needed for the selected AOI or tile grid
* `virtual_mosaic`: read the dataset-level VRT path from `source_raster_datasets`, and optionally verify the VRT’s registered source files through `source_raster_files`
* `postgis_raster`: read raster pixels from PostGIS raster storage; use `source_raster_files` only for provenance if file-level source history was recorded

The user should not normally choose individual source files in Mode 3. The user chooses a registered source dataset. The tool uses the file-level registry internally.

#### Mode 3 user-facing menu

Mode 3 should first ask the user to choose an operation:

1. Create tile plan only
2. Create tile plan and build raster tiles
3. Use existing tile plan to build raster tiles
4. Export RAW files from stored raster tiles
5. Validate or re-export from `manifest-rule.json`
6. Export sample-lattice overlay from existing tile plan

The operation menu should come first because different branches require different identifiers.

For example:

* options 1 and 2 need a new `run_id`
* option 3 needs an existing tile-plan `session_id`
* option 4 needs a `session_id` with stored raster tiles
* option 5 needs a `manifest-rule.json` path
* option 6 needs an existing tile-plan `session_id`

The tool should not ask for `run_id`, `session_id`, or `manifest-rule.json` before it knows which operation the user wants.

After the operation is selected, Mode 3 should ask for or recover the target runtime profile when that operation writes or regenerates runtime-facing artifacts such as `manifest-rule.json`, `tile-catalog.json`, RAW terrain files, or runtime placement metadata.

Diagnostic or presentation exports, such as a sample-lattice overlay, do not normally need a runtime profile unless they intentionally include runtime-local coordinate representations.

Initial supported runtime profiles should be:

1. Unity with ArcGIS Maps SDK for Unity
2. Unity with Cesium for Unity

Additional profiles can be added later, such as:

* Unity local-only/no geospatial SDK
* Unreal with ArcGIS Maps SDK for Unreal Engine
* Unreal with Cesium for Unreal
* Unreal native georeferencing
* custom importer profile

These later profiles should not be treated as first-version requirements unless the project scope expands.

#### Runtime georeferencing profile handling

Mode 3 should treat the target runtime profile as a separate concept from source storage mode.

The selected runtime profile affects:

* the structure and values written to `manifest-rule.json`
* the structure and values written to `tile-catalog.json`
* how the terrain package origin is represented for the target engine
* whether additional transformed origin coordinates are needed
* which engine-side component or georeference object the importer is expected to create or configure
* what warnings or assumptions should be recorded in the manifest

The selected runtime profile should not normally change:

* the registered source raster dataset
* the registered AOI
* the authoritative working CRS
* the tile grid geometry
* the generated RAW heightmap dimensions
* the source raster access method

The default rule is:

**Generate the terrain package in the workflow working CRS, then write runtime-specific georeferencing metadata needed by the selected engine or SDK.**

For **Unity with ArcGIS Maps SDK for Unity**:

* the runtime profile should record `target_engine` as `unity`
* the runtime profile should record `target_geospatial_runtime` as `arcgis_maps_sdk_for_unity`
* the manifest should describe the intended runtime parent/georeference object using ArcGIS Maps SDK placement metadata
* the package origin may be expressed directly in the workflow working CRS if that CRS is supported by the SDK and importer
* the manifest should record the spatial reference WKID, package origin, anchor corner, rotation assumptions, and local child offset convention

For **Unity with Cesium for Unity**:

* the runtime profile should record `target_engine` as `unity`
* the runtime profile should record `target_geospatial_runtime` as `cesium_for_unity`
* the terrain package should still be generated in the workflow working CRS unless the user explicitly chooses otherwise
* the manifest should preserve the workflow working-CRS origin as the authoritative package origin
* the manifest should also include a Cesium-compatible transformed origin, normally longitude/latitude/height or ECEF
* the manifest should warn that Cesium does not use the workflow working CRS as the active runtime placement CRS
* the tile catalog should keep authoritative tile extents in the workflow working CRS
* optional WGS84 approximate extents may be written for inspection, but they should not replace the working-CRS extents as the authoritative tile geometry

In plain terms:

**ArcGIS may be able to use the working CRS directly. Cesium needs a transformed georeference origin, but the terrain-production grid can still remain in the working CRS.**

#### Source storage mode handling

Mode 3 should check `source_storage_mode` whenever it selects or recovers a `source_dataset_id`.

The `source_storage_mode` is read from `source_raster_datasets`.

For planning-only operations, `source_storage_mode` is mostly informational. The tool usually needs metadata, not raster pixels.

For raster-realization operations, `source_storage_mode` determines how the tool accesses elevation pixels.

Possible source storage modes include:

* `external_file`
* `external_files`
* `virtual_mosaic`
* `postgis_raster`

Mode 3 should not ask the user to choose between database rasters and external rasters as a separate top-level option. That would duplicate the menu unnecessarily. Instead, Mode 3 should inspect the selected source dataset record and use the appropriate access method internally.

Example logic:

* if `source_storage_mode` is `external_file`, read the one registered file row from `source_raster_files`
* if `source_storage_mode` is `external_files`, query `source_raster_files` for the file rows needed by the AOI or tile grid
* if `source_storage_mode` is `virtual_mosaic`, read from the registered VRT path stored in `source_raster_datasets`, and optionally verify VRT source files through `source_raster_files`
* if `source_storage_mode` is `postgis_raster`, read from PostGIS raster records

Source storage mode answers:

**“Where do the elevation pixels come from?”**

Runtime profile answers:

**“How should the finished package describe itself to the target engine or SDK?”**

Those should remain separate.

#### Source file verification rule

Mode 3 should verify source accessibility after it knows which source dataset is relevant, but before any operation that requires raster pixels.

The tool should not ask the user to confirm paths when file checks succeed. That would add unnecessary friction.

Instead, it should:

1. read dataset-level path information from `source_raster_datasets`
2. read required file-level records from `source_raster_files`
3. reconstruct full paths where needed
4. check whether required files or raster records exist and are readable
5. report the result in the confirmation summary
6. only interrupt the workflow if required data is missing, unreadable, or insufficient for the selected operation

For `external_file`, Mode 3 should check that the single registered file exists and is readable.

For `external_files`, Mode 3 should reconstruct each required full path from:

```text
source_root_path + relative_path
```

where:

* `source_root_path` comes from `source_raster_datasets`
* `relative_path` comes from `source_raster_files`

It should then check whether the required files exist and are readable.

For `virtual_mosaic`, Mode 3 should check more than the VRT file itself. It should check that:

* the VRT path is registered in `source_raster_datasets`
* the VRT exists
* GDAL/rasterio can open it
* the VRT-referenced source files are reachable
* the VRT metadata matches the registered dataset metadata closely enough to proceed
* the original source files remain traceable in `source_raster_files`

For `postgis_raster`, Mode 3 should check that the relevant raster records exist in PostGIS.

#### Required files versus all registered files

For multi-file datasets, Mode 3 should distinguish between:

**Required source files**
Files needed for the selected AOI or tile grid.

**Non-required registered files**
Files that belong to the registered source dataset but are outside the current AOI or operation.

For build operations, missing required files should stop the workflow unless the user explicitly chooses a coverage or NoData policy.

Missing non-required files should be reported as a warning, not treated as fatal.

This matters because a large registered source dataset may contain many tiles that are irrelevant to the current terrain package.

In database terms:

* all registered files are rows in `source_raster_files`
* required source files are the subset of those rows intersecting the selected AOI or tile grid
* non-required registered files are rows outside the selected AOI or tile grid

Mode 3 should not require every registered file to be present if many of them are irrelevant to the selected operation.

#### Source coverage validation

File existence is not enough.

Mode 3 should separately validate source coverage.

It should check:

* source files or raster records exist
* source files or raster records are readable
* AOI intersects the source dataset coverage
* required source files or raster records cover the AOI or planned tile grid
* planned tile grid is covered by the source raster data
* edge or coverage policy is defined if the AOI or tile grid extends beyond available source coverage
* source NoData policy is defined and compatible with the selected operation

So Mode 3 needs both:

* source accessibility validation
* source coverage validation

A source file can exist and still fail coverage requirements.

For multi-file datasets, coverage validation should use the file-level extents recorded in `source_raster_files`, plus any more detailed raster checks needed during realization.

#### Path repair behavior

If required external source files are missing or unreadable, Mode 3 should stop and offer recovery choices.

For datasets using `source_root_path` plus `relative_path`, useful recovery options include:

1. recheck paths
2. enter a new `source_root_path` and remap files using existing `relative_path` values
3. enter replacement paths manually
4. continue with available files only, if coverage policy allows
5. abort

The “continue with available files only” option should not be the normal default for terrain building. It should be an advanced or explicit choice because it can create silent holes or NoData areas in the terrain package.

If the user enters a corrected source root path, Mode 3 should ask whether the correction is temporary or permanent:

1. use corrected path for this run only
2. update the registered source dataset with the new `source_root_path`

Mode 3 should not silently modify durable Mode 1 raster-registration records without user permission.

If the correction is permanent, Mode 3 should update the dataset-level `source_root_path` in `source_raster_datasets`. It should not rewrite every file-level `relative_path` unless the relative structure itself has changed.

For datasets registered with absolute paths only, path repair is less clean. The tool may still offer a new-root remap by filename or relative structure, but it should warn that absolute-path registration is less portable and may require manual correction if files are moved.

If manual replacement paths are entered, Mode 3 should not overwrite Mode 1 registration records unless the user explicitly chooses to make the repair permanent.

#### Confirmation summary

Before executing a terrain-package operation, Mode 3 should show a confirmation summary.

The summary should include:

* selected operation
* `run_id`, if creating a new run
* `session_id`, if using or deriving from an existing run
* `derived_from_session_id`, if applicable
* `source_dataset_id`, if applicable
* source dataset name, if applicable
* source type, if applicable
* `source_storage_mode`, if applicable
* source registry tables used:

  * `source_raster_datasets`
  * `source_raster_files`, if applicable
* raster access method, if raster access is required
* source CRS, if applicable
* source cell size, if applicable
* source extent, if applicable
* registered source file count, if applicable
* required source file count for this operation, if applicable
* selected `aoi_id`, if applicable
* AOI name, if applicable
* AOI working CRS, if applicable
* AOI extent, if applicable
* workflow working CRS
* target engine, if runtime-facing artifacts are generated
* target geospatial runtime profile, if runtime-facing artifacts are generated
* runtime georeferencing method, if runtime-facing artifacts are generated
* whether a transformed runtime origin will be written
* target cell size or target sample spacing
* heightmap resolution
* edge policy
* vertical encoding rule, if raster tiles or RAW files are generated
* RAW byte order, if RAW files are generated
* NoData handling policy
* output root folder
* whether RAW files will be exported
* whether derived raster tiles will be stored in the database
* whether `manifest-rule.json` will be generated
* whether `tile-catalog.json` will be generated
* whether diagnostic or presentation artifacts will be generated
* source accessibility check result, if raster access is required
* source coverage check result, if raster realization is required
* runtime georeferencing warning, if applicable

If the source verification succeeds, the tool should report that fact and continue. It should not require a separate path confirmation.

If the runtime profile requires transformed georeferencing metadata, such as the Cesium profile, the summary should show both:

* the working-CRS package origin
* the transformed runtime origin

For Cesium-oriented exports, the summary should make clear that the terrain package remains generated in the workflow working CRS unless the user explicitly chooses otherwise.

#### Mode 3A: Create Tile Plan Only

This operation creates only the tile grid and planning records.

It should ask directly for:

* new `run_id`
* `source_dataset_id`
* `aoi_id`

It should load default planning and artifact settings from `tool_config.yaml`, including:

* target runtime profile
* heightmap resolution
* target sample spacing or tile-size strategy
* edge handling policy
* grid anchor and snapping policy
* output root folder
* whether to generate `manifest-rule.json`
* whether to export the tile grid as a GeoPackage artifact

The tool should display a resolved confirmation summary after all defaults and computed values are visible. It should not prompt for every setting at startup.

If settings need to be changed interactively, the user-facing interface should use grouped override menus, such as:

1. terrain sampling and tile size
2. grid snapping and origin policy
3. runtime profile
4. output artifact settings
5. return to summary
6. cancel

This keeps Mode 3A from becoming an exhaustive questionnaire.

Mode 3A should then:

* read source dataset metadata from `source_raster_datasets`
* check `source_storage_mode`
* verify that the source dataset metadata is sufficient for planning
* read the registered AOI from `aoi_definitions`
* verify AOI compatibility with the source CRS and source extent
* establish the workflow working CRS
* establish the selected runtime profile if writing runtime-facing metadata
* compute or record runtime georeferencing metadata, if needed
* create a new `session_id`
* create a new run record in `terrain_tile_runs`
* generate the tile grid
* populate `terrain_tile_grid_plan`
* compute tile count, extents, row and column structure, anchors, and intended filenames
* compute AOI intersection and AOI occupied fraction for planned tiles
* generate `manifest-rule.json` as the standard planning/recovery artifact
* optionally export the tile grid as GeoPackage

This operation usually does not need raster pixels.

It should not normally query all file-level records from `source_raster_files` unless it needs them for source extent, optional file-level planning validation, or reporting.

It should not create raster tiles.

It should not export RAW files.

It should not generate `tile-catalog.json`.

It should not populate `terrain_tile_grid_outputs` except where lightweight planned-output metadata is intentionally recorded.

It should not populate `terrain_tile_grid_rasters`.

In plain terms:

**Mode 3A says, “Show me how the terrain would be tiled for the selected engine/runtime target, but do not build the tiles yet.”**

#### Mode 3B: Create Tile Plan and Build Raster Tiles

This operation creates a new tile plan and then realizes raster tiles from it.

It should ask for:

* new `run_id`
* `source_dataset_id`
* `aoi_id`
* target runtime profile
* target cell size
* heightmap resolution
* edge handling policy
* vertical encoding rule
* terrain height in meters, if fixed global terrain height is chosen
* output root folder
* whether to export RAW files
* whether to store derived raster tiles in PostGIS
* whether to generate `tile-catalog.json`

It should then:

* read source dataset metadata from `source_raster_datasets`
* check `source_storage_mode`
* identify required source files or raster records
* query relevant file rows from `source_raster_files`, if external files are involved
* verify required raster access
* verify source coverage
* establish the workflow working CRS
* establish the selected runtime profile
* compute or record runtime georeferencing metadata
* create a new `session_id`
* create a run record in `terrain_tile_runs`
* generate the tile grid
* populate `terrain_tile_grid_plan`
* realize raster tiles from the selected source dataset and AOI
* populate `terrain_tile_grid_outputs`
* populate `terrain_tile_grid_rasters` only if derived raster storage is requested
* write `manifest-rule.json` as the standard package recovery/control artifact
* write `tile-catalog.json`, if requested
* export RAW files, if requested
* compute SHA-256 values for exported files
* update export and validation status fields

The raster access method depends on `source_storage_mode`.

For example:

* `external_file`: read from the one registered source file
* `external_files`: read from the required registered file rows using `source_root_path` plus `relative_path`
* `virtual_mosaic`: read from the registered VRT path and verify the registered source files as needed
* `postgis_raster`: read from PostGIS raster records

The runtime georeferencing method depends on the target runtime profile.

For example:

* `unity_arcgis_maps_sdk`: write ArcGIS-compatible runtime/geospatial-location metadata
* `unity_cesium`: preserve working-CRS tile metadata, but also write Cesium-compatible longitude/latitude/height or ECEF origin metadata

In plain terms:

**Mode 3B says, “Create the tile layout and actually build the terrain package for the selected engine/runtime target.”**

#### Mode 3C: Use Existing Tile Plan to Build Raster Tiles

This operation starts from an existing tile plan instead of creating a new one.

It should ask for:

* existing tile-plan `session_id`
* new `run_id` for the derived build, if creating a new session
* target runtime profile, if not already fixed by the existing plan or if writing new runtime-facing artifacts
* whether to export RAW files
* whether to store derived raster tiles in PostGIS
* whether to generate `tile-catalog.json`
* output root folder, if exporting files

It should then:

* load the existing tile plan
* recover the original `source_dataset_id`
* recover the original `aoi_id`
* recover the workflow working CRS
* recover the existing runtime profile, if already recorded
* read source dataset metadata from `source_raster_datasets`
* check `source_storage_mode`
* identify required source files or raster records for the existing tile plan
* query relevant file rows from `source_raster_files`, if external files are involved
* verify required raster access
* verify source coverage against the existing tile plan
* compute or update runtime georeferencing metadata, if writing new artifacts
* create a new `session_id` for the derived build, if using the cleaner audit-trail model
* record `derived_from_session_id`
* realize raster tiles using the existing tile grid
* populate `terrain_tile_grid_outputs`
* populate `terrain_tile_grid_rasters` only if derived raster storage is requested
* write or copy `manifest-rule.json` for the derived run as the standard recovery/control artifact
* write `tile-catalog.json`, if requested
* export RAW files, if requested
* compute SHA-256 values for exported files
* update export and validation status fields

The user should not normally choose a different source dataset here. The existing tile plan was created against a particular source dataset and AOI. Source substitution should be treated as an advanced operation, not a normal branch.

Changing the runtime profile for an existing tile plan should be allowed only if the existing terrain-production assumptions remain valid. For example, exporting the same working-CRS tile plan with a Cesium runtime profile may be valid if the workflow can compute the required transformed georeference origin. However, it should not silently alter the authoritative tile grid.

In plain terms:

**Mode 3C says, “Use a tiling plan I already approved, but now build or export from it for a selected engine/runtime target.”**

#### Mode 3D: Export RAW Files from Stored Raster Tiles

This operation starts from derived raster tiles that already exist in `terrain_tile_grid_rasters`.

It does not need to access the original source raster.

It should ask for:

* existing `session_id` with stored raster tiles
* output root folder
* whether to generate a fresh `tile-catalog.json`
* whether to preserve the original runtime profile or write artifacts for a different compatible runtime profile

It should then:

* verify that stored derived raster tiles exist
* verify that corresponding output metadata exists
* verify that RAW encoding settings are recoverable
* verify that the output folder is writable
* recover the workflow working CRS
* recover the original runtime profile
* recover or compute runtime georeferencing metadata
* read from `terrain_tile_grid_rasters`
* export RAW files
* compute SHA-256 values
* update export status and validation status
* regenerate `tile-catalog.json` if requested and if output metadata exists
* copy or write `manifest-rule.json` for the exported package as the standard recovery/control artifact

The original `source_storage_mode` may be displayed as historical metadata, but it should not control this operation.

This operation should not require `source_raster_files` unless the user requests additional provenance reporting or wants to validate that the original source files still exist.

Changing the runtime profile during this operation should be treated as an advanced export option. It may be safe when only the runtime georeferencing metadata changes. It should not be allowed if the new runtime profile requires a different terrain grid, different RAW encoding, or different vertical convention unless the user explicitly starts a new build operation.

In plain terms:

**Mode 3D says, “The raster tiles already exist in the database; write them out as RAW files and runtime-facing metadata.”**

#### Mode 3E: Validate or Re-Export from `manifest-rule.json`

This operation uses `manifest-rule.json` as a recovery handle back into the database workflow.

It should ask for:

* path to `manifest-rule.json`

It should then:

* read the manifest
* extract `session_id`, `run_id`, `source_dataset_id`, `aoi_id`, and relevant terrain-package parameters
* extract the target engine and runtime profile
* extract the workflow working CRS
* extract runtime georeferencing metadata
* resolve the manifest against `terrain_tile_runs`
* verify that the run exists, if possible
* verify that the manifest matches the database record
* verify that the referenced `source_dataset_id` exists in `source_raster_datasets`
* check whether file-level records exist in `source_raster_files`, if external source reconstruction may be needed
* check whether `terrain_tile_grid_plan` exists
* check whether `terrain_tile_grid_outputs` exists
* check whether `terrain_tile_grid_rasters` exists
* check whether RAW files exist at the expected output path
* check whether `tile-catalog.json` exists, if expected
* check file sizes and SHA-256 values, if available
* check whether original source rasters are still accessible, if rebuilding from source is needed
* check whether the runtime georeferencing metadata is complete for the selected runtime profile

After inspection, the tool should report what actions are possible.

Possible actions include:

* validate existing package only
* regenerate `tile-catalog.json` from `terrain_tile_grid_outputs`
* regenerate JSON artifacts only, if the database run, tile plan, and output metadata are sufficient
* re-export RAW files from stored derived rasters
* rebuild or re-realize raster tiles from the original source raster, if source access is still valid
* write a fresh manifest into a new output folder
* generate runtime metadata for a compatible alternate runtime profile
* abort if the manifest cannot be matched and no safe reconstruction path exists

This branch should not normally “regenerate `manifest-rule.json`” as a routine action, because the manifest is the thing being used as the recovery handle.

However, it may copy or write a fresh manifest into a new output folder if the user is re-exporting the package.

It may also write a new manifest if the user is deliberately producing a compatible alternate runtime export, such as generating a Cesium-facing manifest from a previously ArcGIS-oriented run. In that case, the new manifest should record the original session relationship using `derived_from_session_id`.

In plain terms:

**Mode 3E says, “Given this manifest, find the corresponding database run and verify, rebuild, re-export, or adapt what can safely be reconstructed.”**

#### Mode 3F: Export Sample-Lattice Overlay from Existing Tile Plan

This operation starts from an existing tile plan and exports a diagnostic or presentation layer showing the heightmap sample lattice.

It should ask for:

* existing tile-plan `session_id`
* tile selection:

  * one `tile_id`
  * selected row and column range
  * all tiles, with warning
* output root folder
* whether to export the full sample lattice or a decimated presentation lattice
* whether to mark RAW border lines
* whether to include tile-border lines

It should then:

* load the existing tile plan from `terrain_tile_grid_plan`
* recover the associated run record from `terrain_tile_runs`
* recover heightmap resolution
* recover terrain intervals per side
* recover target sample spacing
* recover tile size
* recover workflow working CRS
* recover tile extents and tile IDs
* generate sample-lattice line geometries for the selected tile or tile subset
* mark RAW border lines where `sample_index = 0` or `sample_index = terrain_intervals_per_side`
* optionally mark tile-border lines
* write a GeoPackage artifact such as `sample_lattice_demo.gpkg`
* record enough fields for QGIS styling and presentation use

This operation should normally produce one vector line layer, for example:

* `sample_lattice_lines`

Useful fields include:

* `session_id`
* `tile_id`
* `row`
* `col`
* `line_orientation`
* `sample_index`
* `is_raw_border`
* `is_tile_border`
* `spacing_meters`

Mode 3F should not create raster tiles.

It should not export RAW files.

It should not generate `tile-catalog.json`.

It should not require access to source raster pixels.

It should not require `terrain_tile_grid_outputs`.

It should not require `terrain_tile_grid_rasters`.

It should not normally require a target runtime profile, because the sample-lattice overlay is a GIS diagnostic or presentation artifact, not a runtime-facing terrain package artifact.

This operation can become dense quickly. For example, a 1025-resolution tile has 1025 vertical sample lines and 1025 horizontal sample lines, or 2050 line features per tile. Larger heightmap resolutions and multi-tile exports can become heavy. The tool should warn before exporting a large full-resolution lattice.

For normal use, Mode 3F should be treated as a debug, validation, or presentation aid. It should not be a routine output of Mode 3A or Mode 3B.

In plain terms:

**Mode 3F says, “Using an approved tile plan, export a GIS layer that shows the heightmap sample lattice and RAW border lines for inspection or explanation.”**

#### Mode 3 database responsibilities

Mode 3 should use PostgreSQL/PostGIS to:

* create and update run records in `terrain_tile_runs`
* retrieve registered source dataset metadata from `source_raster_datasets`
* retrieve required file-level source metadata from `source_raster_files`
* retrieve registered AOI geometry from `aoi_definitions`
* check source and AOI compatibility
* establish and record the workflow working CRS
* record the selected target engine and runtime profile
* generate tile grids with PostGIS geometry operations
* populate `terrain_tile_grid_plan`
* populate `terrain_tile_grid_outputs`
* optionally populate `terrain_tile_grid_rasters`
* assign tile IDs and filenames
* compute tile extents, anchors, row and column counts, tile count, and coverage status
* store or generate the contents of `manifest-rule.json`
* store or generate the contents of `tile-catalog.json`, if requested
* maintain run status, export status, and validation status
* maintain requested-action fields and completed-state fields separately
* maintain runtime profile metadata sufficient for validation and re-export
* export optional diagnostic or presentation artifacts derived from tile plans, such as sample-lattice overlays

Mode 3 should not collapse dataset-level source metadata and file-level source metadata into one concept.

The source dataset is the named elevation source. The source files are the physical files that support that dataset.

Python should:

* prompt the user
* call database routines
* verify external file paths where appropriate
* reconstruct full paths from `source_root_path` plus file-level `relative_path`
* call GDAL/rasterio/QGIS processing where external rasters or VRTs are used
* perform or request CRS transformations needed for runtime georeferencing metadata
* create output folders
* write JSON files to disk
* export RAW files
* compute SHA-256 values where appropriate
* report validation results
* ask for path repair only when required source data is missing or unreadable
* write optional GeoPackage artifacts for inspection, validation, or presentation

For example, if the workflow working CRS is EPSG:27700 and the target runtime profile is Unity with Cesium for Unity, Python or PostgreSQL/PostGIS should compute the Cesium-compatible origin from the working-CRS package origin. The manifest should then record both the authoritative working-CRS origin and the transformed Cesium runtime origin.

The clean conceptual rule is:

**Mode 3 manages terrain package runs through separable stages: planning, raster realization, optional derived-raster storage, file export, manifest/catalog generation, runtime-profile metadata generation, validation, and optional diagnostic export. Source raster storage mode determines how elevation pixels are accessed. The source registry tables determine where dataset-level and file-level source metadata are found. The target runtime profile determines how the finished package describes its placement to an engine or SDK. None of these should define the user-facing terrain-package operation by itself.**

Mode 3 should append to `logs/mode3_terrain_package_operations.log`.

When a `session_id` exists, Mode 3 should also write a package-specific session log under the output folder.
