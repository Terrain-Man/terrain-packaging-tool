
## 5. Appendices

### 5.1 Appendix A: Database Table Plan

This appendix lists the planned database tables for the first implementation. The field lists are planning-level schema notes, not final SQL DDL.

#### Table list condensed

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

#### Table list in detail

This appendix lists planned database tables and fields at the schema-planning level. It is **not final SQL DDL**. Field names may still be refined before implementation.

##### Core first-version tables

###### `source_raster_datasets`

Registry of source elevation raster datasets.

One row per registered source dataset. Stores dataset identity, source type, source storage mode, source CRS, cell size, NoData value, dataset extent, source root path, VRT path if applicable, provenance, and dataset-level metadata.

This table represents the named source elevation surface selected later by `source_dataset_id`.

For external raster datasets, this table stores the dataset-level facts. Physical file-level facts are stored separately in `source_raster_files`.

Planned fields:

```text
source_dataset_id
source_name
source_type
source_storage_mode

source_crs_authority
source_crs_wkid
source_crs_label
source_linear_unit

source_cell_size_x
source_cell_size_y
source_cell_size_unit
source_nodata_value

source_extent_geom
source_xmin
source_ymin
source_xmax
source_ymax

source_root_path
path_storage_mode
primary_source_path
vrt_path
vrt_origin

file_count
has_virtual_mosaic
has_postgis_raster_storage

source_metadata_json
provenance_note

created_at
updated_at
registration_status
validation_status
last_error_message
```

Notes:

* `source_storage_mode` values may include `external_file`, `external_files`, `virtual_mosaic`, and `postgis_raster`.
* `path_storage_mode` values may include `root_plus_relative`, `absolute_paths_only`, and `database_raster_only`.
* `source_metadata_json` can store flexible dataset-level metadata that does not need a dedicated column yet.

---

###### `source_raster_files`

File-level registry for external raster datasets.

One row per registered source raster file. Used for `external_file`, `external_files`, and `virtual_mosaic` source storage modes. Stores filename, relative path, optional absolute path, file extent, CRS, cell size, NoData value, dimensions, checksum, and readability/validation status.

For a single-file source dataset, this table still has one row.

For tiled or multi-file source datasets, this table has one row per registered source raster file.

This table is used by Mode 3 to identify which registered source files are required for a selected AOI or tile grid.

Planned fields:

```text
source_file_id
source_dataset_id

filename
relative_path
absolute_path

file_exists_at_registration
file_readable_at_registration
file_size_bytes
file_modified_time
file_sha256

file_crs_authority
file_crs_wkid
file_crs_label

file_cell_size_x
file_cell_size_y
file_nodata_value

raster_width_pixels
raster_height_pixels
raster_band_count
raster_dtype

file_extent_geom
file_xmin
file_ymin
file_xmax
file_ymax

is_part_of_virtual_mosaic
is_active

registration_note

created_at
updated_at
validation_status
last_error_message
```

Notes:

* `source_file_id` can be a generated key.
* `source_dataset_id` should reference `source_raster_datasets(source_dataset_id)`.
* `absolute_path` may be null when the preferred `source_root_path + relative_path` model is used.
* `is_active` allows a file record to remain in the registry while being excluded from current use if necessary.

---

###### `aoi_definitions`

Registry of reusable AOIs.

Stores AOI ID, name, source type, source CRS, working CRS, original geometry if preserved, normalized working geometry, area, bounding box, transformation metadata, and provenance.

This table represents the reusable project boundaries selected later by `aoi_id`.

Planned fields:

```text
aoi_id
aoi_name
description
aoi_source_type

source_file_path
source_layer_name

source_crs_authority
source_crs_wkid
source_crs_label

working_crs_authority
working_crs_wkid
working_crs_label

geom_original
geom

was_reprojected
reprojection_note
transformation_metadata_json

area_square_meters
bbox_xmin
bbox_ymin
bbox_xmax
bbox_ymax
centroid_x
centroid_y

created_at
updated_at
validation_status
last_error_message
provenance_note
```

Notes:

* `geom` should be the normalized AOI geometry in the workflow working CRS.
* `geom_original` is optional but useful when the AOI was imported or transformed.
* `aoi_source_type` values may include `geopackage`, `shapefile`, `geojson`, `kml`, `manual_bbox`, and `source_raster_extent`.

---

###### `terrain_tile_runs`

One row per terrain-package operation/session.

Stores `run_id`, `session_id`, source dataset, AOI, operation type, production parameters, workflow CRS, target engine/runtime profile, output folder, run status, requested-action fields, completed-state fields, and run-level artifact checksums.

This table records both the user/workflow intent and the actual completed state of a Mode 3 operation.

Planned fields:

```text
session_id
run_id
derived_from_session_id

operation_type
operation_label
source_manifest_path

source_dataset_id
aoi_id

workflow_crs_authority
workflow_crs_wkid
workflow_crs_label
workflow_linear_unit

target_engine
target_geospatial_runtime
runtime_profile_id
runtime_profile_schema_version

runtime_component
runtime_parent_name
children_use_engine_local_offsets

working_crs_origin_x
working_crs_origin_y
working_crs_origin_z_meters
origin_anchor_corner

runtime_origin_authority
runtime_origin_crs_authority
runtime_origin_crs_wkid
runtime_origin_crs_label

runtime_origin_x
runtime_origin_y
runtime_origin_z_meters
runtime_longitude_degrees
runtime_latitude_degrees
runtime_ellipsoid_height_meters
runtime_ecef_x_meters
runtime_ecef_y_meters
runtime_ecef_z_meters

runtime_heading_degrees
runtime_pitch_degrees
runtime_roll_degrees
runtime_warning_json

target_cell_size
heightmap_resolution
terrain_intervals_per_side
tile_size_meters
terrain_height_meters

edge_policy
vertical_encoding_rule
raw_bit_depth
raw_data_type
raw_byte_order
raw_array_orientation_json
nodata_handling_json
sampling_model_json
grid_convention_json

source_access_summary_json
source_coverage_summary_json

output_root_folder
computed_output_folder
raw_output_folder
log_file_path

tile_plan_creation_requested
tile_plan_creation_completed

raster_tile_realization_requested
raster_tile_realization_completed

derived_raster_storage_requested
derived_raster_storage_completed

raw_file_export_requested
raw_file_export_completed

manifest_rule_generation_requested
manifest_rule_generation_completed

tile_catalog_generation_requested
tile_catalog_generation_completed

tile_grid_geopackage_export_requested
tile_grid_geopackage_export_completed

created_at
started_at
completed_at

operation_status
validation_status
failure_reason
last_error_message

manifest_rule_sha256
tile_catalog_sha256
tile_grid_geopackage_sha256

run_metadata_json
```

Notes:

* `derived_raster_storage_requested` means the workflow should store generated terrain-tile raster products in PostGIS.
* `derived_raster_storage_completed` means those generated terrain-tile raster products were successfully stored.
* These are not original source rasters. They are derived raster tiles created by Mode 3.
* `source_manifest_path` is mainly relevant for Mode 3E, where `manifest-rule.json` is used as an input recovery handle.
* `operation_status` might include values such as `planned`, `running`, `completed`, `failed`, `partially_completed`, or `cancelled`.
* `validation_status` might include values such as `not_checked`, `passed`, `warning`, or `failed`.

---

###### `terrain_tile_grid_plan`

One row per planned terrain tile.

Stores the vector grid generated from `ST_SquareGrid`, including row/column structure, tile IDs, planned working-CRS extents, anchors, intended filenames, tile size, and edge-policy information.

This table is about the **intended grid**, not necessarily realized output.

A tile plan can exist without raster tiles, without RAW files, and without output metadata beyond the planned records.

Planned fields:

```text
session_id
tile_id

row
col

grid_geom

planned_xmin
planned_ymin
planned_xmax
planned_ymax

planned_anchor_x
planned_anchor_y
planned_anchor_corner

working_crs_wkid
working_crs_label

raw_filename
tif_filename

edge_policy
is_edge_tile
planned_tile_width_meters
planned_tile_height_meters

aoi_intersection_geom
aoi_occupied_width_meters
aoi_occupied_height_meters
aoi_occupied_fraction

created_at
plan_status
```

Notes:

* `grid_geom` stores the planned tile polygon in the workflow working CRS.
* `aoi_intersection_geom` is useful for edge tiles and AOI coverage reporting.
* `raw_filename` is an intended filename at this stage, not proof that the file exists.

---

###### `terrain_tile_grid_outputs`

One row per realized/exported terrain tile.

Stores lightweight output metadata such as filenames, engine-local positions, working-CRS extents, padding status, source coverage, AOI coverage, elevation statistics, expected file size, actual file size, checksums, and export/validation status.

This table should use engine-neutral terminology.

This table is likely the main database source for `tile-catalog.json`.

It should not store heavy raster payloads.

Planned fields:

```text
session_id
tile_id

row
col

raw_filename
raw_relative_path
tif_filename
tif_relative_path

engine_local_x
engine_local_y
engine_local_z

engine_terrain_size_x_meters
engine_terrain_size_y_meters
engine_terrain_size_z_meters

working_crs_anchor_x
working_crs_anchor_y
working_crs_anchor_corner

working_crs_xmin
working_crs_ymin
working_crs_xmax
working_crs_ymax

is_full_aoi_tile
is_padded_beyond_aoi
is_partial_tile

aoi_occupied_width_meters
aoi_occupied_height_meters
aoi_occupied_fraction

has_full_source_coverage
contains_source_nodata
source_coverage_fraction
source_coverage_status

tile_min_elevation_m
tile_max_elevation_m
tile_mean_elevation_m

expected_file_size_bytes
actual_file_size_bytes
raw_sha256

export_status
validation_status
seam_validation_status
last_error_message

created_at
updated_at

output_metadata_json
source_contribution_json
provenance_note
```

Notes:

* `engine_local_x`, `engine_local_y`, and `engine_local_z` replace earlier Unity-specific naming.
* `working_crs_*` fields replace older ambiguous terms like `projected_*` or `geospatial_*`.
* `source_contribution_json` may temporarily store which source files contributed to a tile before a dedicated `terrain_tile_source_contributions` table exists.

---

###### `terrain_tile_grid_rasters`

Optional heavy raster storage for generated terrain-tile rasters.

Stores actual PostGIS raster tile objects only when the run-level setting requests derived raster storage in the database.

This table stores generated terrain-tile rasters, not original source rasters.

Planned fields:

```text
session_id
tile_id

row
col

filename
raster_role

rast

working_crs_wkid
working_crs_label

created_at
raster_metadata_json
```

Notes:

* `raster_role` may include values such as `realized_height_tile`, `normalized_uint16_tile`, `intermediate_float_tile`, or `debug_tile`.
* If `derived_raster_storage_requested = false`, this table should have no rows for that session.
* If `derived_raster_storage_requested = true` and `derived_raster_storage_completed = true`, this table should contain the stored generated raster tiles for that session.
* This table exists so the workflow can later re-export RAW files from stored generated tile rasters without rebuilding them from the original source dataset.

---

##### Conditional first-version table

###### `source_raster_payloads`

Conditional table for original source raster payloads loaded into PostGIS.

This table is only needed if `postgis_raster` source storage is implemented in the first version.

It should store original registered source raster payloads loaded into PostGIS. It should remain separate from `terrain_tile_grid_rasters`, because the two tables represent different things:

* `source_raster_payloads` stores original source raster payloads
* `terrain_tile_grid_rasters` stores generated terrain-tile raster payloads derived from source data

If `postgis_raster` remains deferred or experimental, this table can be deferred as well.

Planned fields:

```text
source_payload_id
source_dataset_id
source_file_id

raster_role
rast

source_crs_wkid
source_crs_label

loaded_from_path
loaded_at

payload_metadata_json
validation_status
last_error_message
```

Notes:

* `source_file_id` may be null if the payload was not loaded from a file-level registry entry.
* `raster_role` might distinguish source tiles, source mosaic payloads, or test payloads.
* This table is not required if the first version only registers external source rasters and does not load original source pixels into PostGIS.

---

##### Optional/helper tables for later versions

###### `terrain_run_artifacts`

Optional artifact tracking table.

Can be added later if artifact tracking becomes too complex for `terrain_tile_runs` and `terrain_tile_grid_outputs`.

For the first implementation, artifact paths and run-level checksums can remain in `terrain_tile_runs`, while per-tile RAW file metadata can remain in `terrain_tile_grid_outputs`.

Planned fields:

```text
artifact_id
session_id

artifact_type
artifact_relative_path
artifact_absolute_path

file_size_bytes
sha256

created_at
validation_status

artifact_metadata_json
```

---

###### `terrain_runtime_profiles`

Optional normalized runtime-profile table.

Can be added later if target engine/runtime profiles become numerous or complex.

For the first implementation, runtime profile values can remain in `terrain_tile_runs` and supporting JSONB metadata fields.

Planned fields:

```text
runtime_profile_id
target_engine
target_geospatial_runtime

profile_name
engine_component

supports_working_crs_direct
requires_transformed_runtime_origin
preferred_origin_authority

axis_convention_json
profile_metadata_json

created_at
updated_at
is_active
```

---

###### `terrain_validation_events`

Optional validation history table.

Can be added later if validation becomes multi-stage, repeated, or historically important.

For the first implementation, current validation state can remain in:

* `terrain_tile_runs`
* `terrain_tile_grid_outputs`

A future validation-events table could record each validation pass separately.

Planned fields:

```text
validation_event_id
session_id
tile_id

validation_scope
validation_type

validator_name
validator_version

started_at
completed_at

validation_status
warning_count
error_count
summary_message

validation_metadata_json
```

Notes:

* `tile_id` may be null for run-level validation events.
* `validation_scope` could distinguish run-level, tile-level, file-level, catalog-level, or seam-level validation.

---

###### `terrain_tile_source_contributions`

Optional per-tile source provenance table.

Can be added later if detailed provenance is needed for which source raster files contributed to each realized terrain tile.

This may be useful for multi-file source datasets where one terrain tile is assembled from several registered source raster files.

For the first implementation, this information can remain in `terrain_tile_grid_outputs.source_contribution_json`, optional `tile-catalog.json` provenance fields, or be omitted if not needed.

Planned fields:

```text
session_id
tile_id

source_dataset_id
source_file_id

contribution_role
contribution_fraction

source_window_json
processing_note

created_at
```

---

###### `terrain_tile_export_events`

Optional export history table, more speculative than others.

Can be added later if repeated exports from the same stored raster session become common and need to be tracked separately.

For the first implementation, export status can remain in:

* `terrain_tile_runs`
* `terrain_tile_grid_outputs`
* optional artifact metadata

This table is not required unless the workflow needs a durable history of multiple exports from the same run/session.

Planned fields:

```text
export_event_id
session_id

export_root_folder
runtime_profile_id

raw_file_count
manifest_rule_sha256
tile_catalog_sha256

started_at
completed_at
export_status
last_error_message

export_metadata_json
```

---