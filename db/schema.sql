-- schema.sql
-- GEOG670 terrain packaging workflow
-- Initial reproducible database schema draft.
--
-- Purpose:
--   This file creates the core database structure for a PostgreSQL/PostGIS-centered
--   terrain packaging workflow. It supports:
--
--     Mode 1: Register source raster datasets
--     Mode 2: Register reusable AOI definitions
--     Mode 3: Plan, realize, persist, export, validate, and re-export terrain packages
--
-- Design principle:
--   Python is the launcher and file orchestrator.
--   PostgreSQL/PostGIS is the terrain-production engine and authoritative workflow state.
--
-- Important:
--   This file is planning-level DDL. It is intended to be reviewed and revised
--   before being treated as final.
--
--   CREATE TABLE IF NOT EXISTS is useful for initial setup, but it does not modify
--   existing tables if fields are later added or changed. During development, a
--   separate reset-dev workflow may be useful after explicit confirmation.
--
-- Revision history:
--   2026-05-12:
--     - Clarified that source_raster_datasets.source_extent_geom is the
--       dataset-level bounding envelope, not a detailed multi-file coverage
--       footprint. Detailed file coverage remains in source_raster_files.
--     - Added source_raster_datasets.vrt_origin to record whether a registered
--       VRT was created by Mode 1, supplied by the user, not applicable, or
--       unknown.
--     - Clarified that source_raster_datasets.primary_source_path is
--       convenience/display metadata, not the canonical source file reference.

BEGIN;

-- ---------------------------------------------------------------------
-- Extensions
--
-- postgis provides geometry/geography support.
-- postgis_raster provides the raster type and raster functions.
--
-- The workflow can register external rasters without loading pixels into
-- PostgreSQL, but PostGIS Raster is needed if source raster payloads or
-- generated terrain-tile rasters are stored in the database.
-- ---------------------------------------------------------------------

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_raster;

-- ---------------------------------------------------------------------
-- Lightweight schema metadata
--
-- This table gives db_check.py or terrain_tool.py a simple way to verify
-- the expected schema identity and version.
-- ---------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS terrain_schema_metadata (
    metadata_key text PRIMARY KEY,
    metadata_value text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO terrain_schema_metadata (metadata_key, metadata_value)
VALUES
    ('schema_name', 'geog670_terrain_packaging_v1'),
    ('schema_version', '0.1.1')
ON CONFLICT (metadata_key)
DO UPDATE SET
    metadata_value = EXCLUDED.metadata_value,
    updated_at = now();

-- ---------------------------------------------------------------------
-- Shared updated_at trigger helper
--
-- Tables that use updated_at can attach this trigger so updates are
-- timestamped automatically.
-- ---------------------------------------------------------------------

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

-- ---------------------------------------------------------------------
-- Mode 1 source raster registry
--
-- These tables record source elevation datasets and their physical files.
-- The normal/default workflow keeps large source raster files on disk and
-- stores metadata, paths, extents, checksums, and validation state here.
--
-- source_raster_datasets = one row per named source elevation surface
-- source_raster_files    = one row per physical raster file supporting it
-- source_raster_payloads = optional PostGIS raster storage for original source pixels
--
-- Important distinction:
--   source_raster_payloads stores original registered source rasters.
--   terrain_tile_grid_rasters stores generated terrain-package raster tiles.
-- ---------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS source_raster_datasets (
    source_dataset_id text PRIMARY KEY,

    source_name text NOT NULL,
    source_type text NOT NULL,
    source_storage_mode text NOT NULL,

    source_crs_authority text,
    source_crs_wkid integer,
    source_crs_label text,
    source_linear_unit text,

    source_cell_size_x double precision,
    source_cell_size_y double precision,
    source_cell_size_unit text,
    source_nodata_value double precision,

    source_extent_geom geometry(Polygon),
    source_xmin double precision,
    source_ymin double precision,
    source_xmax double precision,
    source_ymax double precision,

    source_root_path text,
    path_storage_mode text,
    primary_source_path text,
    vrt_path text,
    vrt_origin text,

    file_count integer NOT NULL DEFAULT 0,
    has_virtual_mosaic boolean NOT NULL DEFAULT false,
    has_postgis_raster_storage boolean NOT NULL DEFAULT false,

    source_metadata_json jsonb,
    provenance_note text,

    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz,
    registration_status text NOT NULL DEFAULT 'registered',
    validation_status text NOT NULL DEFAULT 'not_checked',
    last_error_message text,

    CONSTRAINT source_raster_datasets_storage_mode_chk
        CHECK (source_storage_mode IN (
            'external_file',
            'external_files',
            'virtual_mosaic',
            'postgis_raster'
        )),

    CONSTRAINT source_raster_datasets_path_storage_mode_chk
        CHECK (
            path_storage_mode IS NULL OR
            path_storage_mode IN (
                'root_plus_relative',
                'absolute_paths_only',
                'database_raster_only',
                'not_applicable'
            )
        ),

    CONSTRAINT source_raster_datasets_vrt_origin_chk
        CHECK (
            vrt_origin IS NULL OR
            vrt_origin IN (
                'created_by_mode1',
                'user_supplied',
                'not_applicable',
                'unknown'
            )
        ),

    CONSTRAINT source_raster_datasets_file_count_chk
        CHECK (file_count >= 0),

    CONSTRAINT source_raster_datasets_validation_status_chk
        CHECK (validation_status IN (
            'not_checked',
            'passed',
            'warning',
            'failed'
        )),

    CONSTRAINT source_raster_datasets_registration_status_chk
        CHECK (registration_status IN (
            'registered',
            'updated',
            'failed',
            'archived',
            'inactive'
        ))
);

CREATE TABLE IF NOT EXISTS source_raster_files (
    source_file_id bigserial PRIMARY KEY,
    source_dataset_id text NOT NULL,

    filename text NOT NULL,
    relative_path text,
    absolute_path text,

    file_exists_at_registration boolean,
    file_readable_at_registration boolean,
    file_size_bytes bigint,
    file_modified_time timestamptz,
    file_sha256 text,

    file_crs_authority text,
    file_crs_wkid integer,
    file_crs_label text,

    file_cell_size_x double precision,
    file_cell_size_y double precision,
    file_nodata_value double precision,

    raster_width_pixels integer,
    raster_height_pixels integer,
    raster_band_count integer,
    raster_dtype text,

    file_extent_geom geometry(Polygon),
    file_xmin double precision,
    file_ymin double precision,
    file_xmax double precision,
    file_ymax double precision,

    is_part_of_virtual_mosaic boolean NOT NULL DEFAULT false,
    is_active boolean NOT NULL DEFAULT true,

    registration_note text,

    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz,
    validation_status text NOT NULL DEFAULT 'not_checked',
    last_error_message text,

    CONSTRAINT source_raster_files_dataset_fk
        FOREIGN KEY (source_dataset_id)
        REFERENCES source_raster_datasets (source_dataset_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    CONSTRAINT source_raster_files_file_size_chk
        CHECK (file_size_bytes IS NULL OR file_size_bytes >= 0),

    CONSTRAINT source_raster_files_width_chk
        CHECK (raster_width_pixels IS NULL OR raster_width_pixels > 0),

    CONSTRAINT source_raster_files_height_chk
        CHECK (raster_height_pixels IS NULL OR raster_height_pixels > 0),

    CONSTRAINT source_raster_files_band_count_chk
        CHECK (raster_band_count IS NULL OR raster_band_count > 0),

    CONSTRAINT source_raster_files_validation_status_chk
        CHECK (validation_status IN (
            'not_checked',
            'passed',
            'warning',
            'failed'
        ))
);

-- Conditional first-version table.
-- This is needed only if source_storage_mode = 'postgis_raster' is implemented.
-- It stores original registered source raster payloads, not generated terrain tiles.

CREATE TABLE IF NOT EXISTS source_raster_payloads (
    source_payload_id bigserial PRIMARY KEY,
    source_dataset_id text NOT NULL,
    source_file_id bigint,

    raster_role text NOT NULL DEFAULT 'source_raster',
    rast raster NOT NULL,

    source_crs_wkid integer,
    source_crs_label text,

    loaded_from_path text,
    loaded_at timestamptz NOT NULL DEFAULT now(),

    payload_metadata_json jsonb,
    validation_status text NOT NULL DEFAULT 'not_checked',
    last_error_message text,

    CONSTRAINT source_raster_payloads_dataset_fk
        FOREIGN KEY (source_dataset_id)
        REFERENCES source_raster_datasets (source_dataset_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    CONSTRAINT source_raster_payloads_file_fk
        FOREIGN KEY (source_file_id)
        REFERENCES source_raster_files (source_file_id)
        ON UPDATE CASCADE
        ON DELETE SET NULL,

    CONSTRAINT source_raster_payloads_validation_status_chk
        CHECK (validation_status IN (
            'not_checked',
            'passed',
            'warning',
            'failed'
        ))
);

-- ---------------------------------------------------------------------
-- Mode 2 AOI registry
--
-- AOIs are reusable project boundaries. They may originate from vector
-- files, manual bounding boxes, or registered source raster extents.
--
-- geom_original can preserve the input geometry.
-- geom stores the normalized working-CRS geometry used by later workflow stages.
-- ---------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS aoi_definitions (
    aoi_id text PRIMARY KEY,
    aoi_name text NOT NULL,
    description text,
    aoi_source_type text NOT NULL,

    source_file_path text,
    source_layer_name text,

    source_crs_authority text,
    source_crs_wkid integer,
    source_crs_label text,

    working_crs_authority text,
    working_crs_wkid integer,
    working_crs_label text,

    geom_original geometry(Geometry),
    geom geometry(Geometry) NOT NULL,

    was_reprojected boolean NOT NULL DEFAULT false,
    reprojection_note text,
    transformation_metadata_json jsonb,

    area_square_meters double precision,
    bbox_xmin double precision,
    bbox_ymin double precision,
    bbox_xmax double precision,
    bbox_ymax double precision,
    centroid_x double precision,
    centroid_y double precision,

    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz,
    validation_status text NOT NULL DEFAULT 'not_checked',
    last_error_message text,
    provenance_note text,

    CONSTRAINT aoi_definitions_source_type_chk
        CHECK (aoi_source_type IN (
            'geopackage',
            'shapefile',
            'geojson',
            'kml',
            'manual_bbox',
            'source_raster_extent',
            'other'
        )),

    CONSTRAINT aoi_definitions_area_chk
        CHECK (area_square_meters IS NULL OR area_square_meters >= 0),

    CONSTRAINT aoi_definitions_validation_status_chk
        CHECK (validation_status IN (
            'not_checked',
            'passed',
            'warning',
            'failed'
        ))
);

-- ---------------------------------------------------------------------
-- Mode 3 run/session table
--
-- terrain_tile_runs is the run-level control table for terrain-package
-- operations.
--
-- It records:
--   - source dataset and AOI selection
--   - operation type
--   - workflow CRS
--   - target engine/runtime profile
--   - terrain production parameters
--   - requested/completed stage pairs
--   - run-level artifact paths and checksums
--
-- Requested/completed pairs are intentionally mirrored:
--   raw_file_export_requested
--   raw_file_export_completed
--
-- This lets the database record intent and result separately.
-- ---------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS terrain_tile_runs (
    session_id text PRIMARY KEY,
    run_id text NOT NULL,
    derived_from_session_id text,

    operation_type text NOT NULL,
    operation_label text,
    source_manifest_path text,

    source_dataset_id text NOT NULL,
    aoi_id text NOT NULL,

    workflow_crs_authority text,
    workflow_crs_wkid integer,
    workflow_crs_label text,
    workflow_linear_unit text,

    target_engine text,
    target_geospatial_runtime text,
    runtime_profile_id text,
    runtime_profile_schema_version text,

    runtime_component text,
    runtime_parent_name text,
    children_use_engine_local_offsets boolean,

    working_crs_origin_x double precision,
    working_crs_origin_y double precision,
    working_crs_origin_z_meters double precision,
    origin_anchor_corner text,

    runtime_origin_authority text,
    runtime_origin_crs_authority text,
    runtime_origin_crs_wkid integer,
    runtime_origin_crs_label text,

    runtime_origin_x double precision,
    runtime_origin_y double precision,
    runtime_origin_z_meters double precision,
    runtime_longitude_degrees double precision,
    runtime_latitude_degrees double precision,
    runtime_ellipsoid_height_meters double precision,
    runtime_ecef_x_meters double precision,
    runtime_ecef_y_meters double precision,
    runtime_ecef_z_meters double precision,

    runtime_heading_degrees double precision,
    runtime_pitch_degrees double precision,
    runtime_roll_degrees double precision,
    runtime_warning_json jsonb,

    target_cell_size double precision,
    heightmap_resolution integer,
    terrain_intervals_per_side integer,
    tile_size_meters double precision,
    terrain_height_meters double precision,

    edge_policy text,
    vertical_encoding_rule text,
    raw_bit_depth integer,
    raw_data_type text,
    raw_byte_order text,
    raw_array_orientation_json jsonb,
    nodata_handling_json jsonb,
    sampling_model_json jsonb,
    grid_convention_json jsonb,

    source_access_summary_json jsonb,
    source_coverage_summary_json jsonb,

    output_root_folder text,
    computed_output_folder text,
    raw_output_folder text,
    log_file_path text,

    tile_plan_creation_requested boolean NOT NULL DEFAULT false,
    tile_plan_creation_completed boolean NOT NULL DEFAULT false,

    raster_tile_realization_requested boolean NOT NULL DEFAULT false,
    raster_tile_realization_completed boolean NOT NULL DEFAULT false,

    derived_raster_storage_requested boolean NOT NULL DEFAULT false,
    derived_raster_storage_completed boolean NOT NULL DEFAULT false,

    raw_file_export_requested boolean NOT NULL DEFAULT false,
    raw_file_export_completed boolean NOT NULL DEFAULT false,

    manifest_rule_generation_requested boolean NOT NULL DEFAULT false,
    manifest_rule_generation_completed boolean NOT NULL DEFAULT false,

    tile_catalog_generation_requested boolean NOT NULL DEFAULT false,
    tile_catalog_generation_completed boolean NOT NULL DEFAULT false,

    tile_grid_geopackage_export_requested boolean NOT NULL DEFAULT false,
    tile_grid_geopackage_export_completed boolean NOT NULL DEFAULT false,

    created_at timestamptz NOT NULL DEFAULT now(),
    started_at timestamptz,
    completed_at timestamptz,

    operation_status text NOT NULL DEFAULT 'planned',
    validation_status text NOT NULL DEFAULT 'not_checked',
    failure_reason text,
    last_error_message text,

    manifest_rule_sha256 text,
    tile_catalog_sha256 text,
    tile_grid_geopackage_sha256 text,

    run_metadata_json jsonb,

    CONSTRAINT terrain_tile_runs_source_dataset_fk
        FOREIGN KEY (source_dataset_id)
        REFERENCES source_raster_datasets (source_dataset_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT terrain_tile_runs_aoi_fk
        FOREIGN KEY (aoi_id)
        REFERENCES aoi_definitions (aoi_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT terrain_tile_runs_derived_from_fk
        FOREIGN KEY (derived_from_session_id)
        REFERENCES terrain_tile_runs (session_id)
        ON UPDATE CASCADE
        ON DELETE SET NULL,

    CONSTRAINT terrain_tile_runs_heightmap_resolution_chk
        CHECK (heightmap_resolution IS NULL OR heightmap_resolution > 0),

    CONSTRAINT terrain_tile_runs_intervals_chk
        CHECK (terrain_intervals_per_side IS NULL OR terrain_intervals_per_side > 0),

    CONSTRAINT terrain_tile_runs_tile_size_chk
        CHECK (tile_size_meters IS NULL OR tile_size_meters > 0),

    CONSTRAINT terrain_tile_runs_terrain_height_chk
        CHECK (terrain_height_meters IS NULL OR terrain_height_meters > 0),

    CONSTRAINT terrain_tile_runs_raw_bit_depth_chk
        CHECK (raw_bit_depth IS NULL OR raw_bit_depth IN (8, 16, 32)),

    CONSTRAINT terrain_tile_runs_byte_order_chk
        CHECK (
            raw_byte_order IS NULL OR
            raw_byte_order IN ('little_endian', 'big_endian')
        ),

    CONSTRAINT terrain_tile_runs_operation_status_chk
        CHECK (operation_status IN (
            'planned',
            'running',
            'completed',
            'failed',
            'partially_completed',
            'cancelled'
        )),

    CONSTRAINT terrain_tile_runs_validation_status_chk
        CHECK (validation_status IN (
            'not_checked',
            'passed',
            'warning',
            'failed'
        ))
);

-- ---------------------------------------------------------------------
-- Mode 3 tile plan table
--
-- terrain_tile_grid_plan stores the intended grid. It can exist without
-- realized raster tiles, without RAW exports, and without retained raster
-- payloads.
--
-- raw_filename here is an intended filename, not proof that the file exists.
-- ---------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS terrain_tile_grid_plan (
    session_id text NOT NULL,
    tile_id text NOT NULL,

    row integer NOT NULL,
    col integer NOT NULL,

    grid_geom geometry(Polygon) NOT NULL,

    planned_xmin double precision,
    planned_ymin double precision,
    planned_xmax double precision,
    planned_ymax double precision,

    planned_anchor_x double precision,
    planned_anchor_y double precision,
    planned_anchor_corner text,

    working_crs_wkid integer,
    working_crs_label text,

    raw_filename text,
    tif_filename text,

    edge_policy text,
    is_edge_tile boolean NOT NULL DEFAULT false,
    planned_tile_width_meters double precision,
    planned_tile_height_meters double precision,

    aoi_intersection_geom geometry(Geometry),
    aoi_occupied_width_meters double precision,
    aoi_occupied_height_meters double precision,
    aoi_occupied_fraction double precision,

    created_at timestamptz NOT NULL DEFAULT now(),
    plan_status text NOT NULL DEFAULT 'planned',

    PRIMARY KEY (session_id, tile_id),

    CONSTRAINT terrain_tile_grid_plan_run_fk
        FOREIGN KEY (session_id)
        REFERENCES terrain_tile_runs (session_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    CONSTRAINT terrain_tile_grid_plan_row_chk
        CHECK (row >= 0),

    CONSTRAINT terrain_tile_grid_plan_col_chk
        CHECK (col >= 0),

    CONSTRAINT terrain_tile_grid_plan_width_chk
        CHECK (planned_tile_width_meters IS NULL OR planned_tile_width_meters > 0),

    CONSTRAINT terrain_tile_grid_plan_height_chk
        CHECK (planned_tile_height_meters IS NULL OR planned_tile_height_meters > 0),

    CONSTRAINT terrain_tile_grid_plan_occupied_fraction_chk
        CHECK (
            aoi_occupied_fraction IS NULL OR
            (aoi_occupied_fraction >= 0 AND aoi_occupied_fraction <= 1)
        ),

    CONSTRAINT terrain_tile_grid_plan_status_chk
        CHECK (plan_status IN (
            'planned',
            'ready',
            'superseded',
            'failed'
        ))
);

-- ---------------------------------------------------------------------
-- Mode 3 output metadata table
--
-- terrain_tile_grid_outputs stores lightweight per-tile output metadata.
--
-- It should not store heavy raster payloads.
-- Generated raster payloads belong in terrain_tile_grid_rasters only when
-- derived raster storage is requested.
--
-- This table is the primary database source for the per-tile records in `tile-catalog.json`.
-- ---------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS terrain_tile_grid_outputs (
    session_id text NOT NULL,
    tile_id text NOT NULL,

    row integer NOT NULL,
    col integer NOT NULL,

    raw_filename text,
    raw_relative_path text,
    tif_filename text,
    tif_relative_path text,

    engine_local_x double precision,
    engine_local_y double precision,
    engine_local_z double precision,

    engine_terrain_size_x_meters double precision,
    engine_terrain_size_y_meters double precision,
    engine_terrain_size_z_meters double precision,

    working_crs_anchor_x double precision,
    working_crs_anchor_y double precision,
    working_crs_anchor_corner text,

    working_crs_xmin double precision,
    working_crs_ymin double precision,
    working_crs_xmax double precision,
    working_crs_ymax double precision,

    is_full_aoi_tile boolean,
    is_padded_beyond_aoi boolean,
    is_partial_tile boolean,

    aoi_occupied_width_meters double precision,
    aoi_occupied_height_meters double precision,
    aoi_occupied_fraction double precision,

    has_full_source_coverage boolean,
    contains_source_nodata boolean,
    source_coverage_fraction double precision,
    source_coverage_status text,

    tile_min_elevation_m double precision,
    tile_max_elevation_m double precision,
    tile_mean_elevation_m double precision,

    expected_file_size_bytes bigint,
    actual_file_size_bytes bigint,
    raw_sha256 text,

    export_status text NOT NULL DEFAULT 'not_requested',
    validation_status text NOT NULL DEFAULT 'not_checked',
    seam_validation_status text NOT NULL DEFAULT 'not_checked',
    last_error_message text,

    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz,

    output_metadata_json jsonb,
    source_contribution_json jsonb,
    provenance_note text,

    PRIMARY KEY (session_id, tile_id),

    CONSTRAINT terrain_tile_grid_outputs_plan_fk
        FOREIGN KEY (session_id, tile_id)
        REFERENCES terrain_tile_grid_plan (session_id, tile_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    CONSTRAINT terrain_tile_grid_outputs_row_chk
        CHECK (row >= 0),

    CONSTRAINT terrain_tile_grid_outputs_col_chk
        CHECK (col >= 0),

    CONSTRAINT terrain_tile_grid_outputs_terrain_size_x_chk
        CHECK (engine_terrain_size_x_meters IS NULL OR engine_terrain_size_x_meters > 0),

    CONSTRAINT terrain_tile_grid_outputs_terrain_size_y_chk
        CHECK (engine_terrain_size_y_meters IS NULL OR engine_terrain_size_y_meters > 0),

    CONSTRAINT terrain_tile_grid_outputs_terrain_size_z_chk
        CHECK (engine_terrain_size_z_meters IS NULL OR engine_terrain_size_z_meters > 0),

    CONSTRAINT terrain_tile_grid_outputs_aoi_fraction_chk
        CHECK (
            aoi_occupied_fraction IS NULL OR
            (aoi_occupied_fraction >= 0 AND aoi_occupied_fraction <= 1)
        ),

    CONSTRAINT terrain_tile_grid_outputs_source_fraction_chk
        CHECK (
            source_coverage_fraction IS NULL OR
            (source_coverage_fraction >= 0 AND source_coverage_fraction <= 1)
        ),

    CONSTRAINT terrain_tile_grid_outputs_expected_size_chk
        CHECK (expected_file_size_bytes IS NULL OR expected_file_size_bytes >= 0),

    CONSTRAINT terrain_tile_grid_outputs_actual_size_chk
        CHECK (actual_file_size_bytes IS NULL OR actual_file_size_bytes >= 0),

    CONSTRAINT terrain_tile_grid_outputs_export_status_chk
        CHECK (export_status IN (
            'not_requested',
            'pending',
            'exported',
            'failed',
            'skipped'
        )),

    CONSTRAINT terrain_tile_grid_outputs_validation_status_chk
        CHECK (validation_status IN (
            'not_checked',
            'passed',
            'warning',
            'failed'
        )),

    CONSTRAINT terrain_tile_grid_outputs_seam_status_chk
        CHECK (seam_validation_status IN (
            'not_checked',
            'passed',
            'warning',
            'failed'
        ))
);

-- ---------------------------------------------------------------------
-- Mode 3 optional generated raster payload table
--
-- terrain_tile_grid_rasters stores generated terrain-tile raster payloads.
-- It does not store original source rasters.
--
-- This table is populated only when derived raster storage is requested.
-- It enables later RAW re-export without rebuilding from the original source
-- dataset.
-- ---------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS terrain_tile_grid_rasters (
    session_id text NOT NULL,
    tile_id text NOT NULL,

    row integer NOT NULL,
    col integer NOT NULL,

    filename text,
    raster_role text NOT NULL,
    rast raster NOT NULL,

    working_crs_wkid integer,
    working_crs_label text,

    created_at timestamptz NOT NULL DEFAULT now(),
    raster_metadata_json jsonb,

    PRIMARY KEY (session_id, tile_id, raster_role),

    CONSTRAINT terrain_tile_grid_rasters_output_fk
        FOREIGN KEY (session_id, tile_id)
        REFERENCES terrain_tile_grid_outputs (session_id, tile_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    CONSTRAINT terrain_tile_grid_rasters_row_chk
        CHECK (row >= 0),

    CONSTRAINT terrain_tile_grid_rasters_col_chk
        CHECK (col >= 0)
);

-- ---------------------------------------------------------------------
-- Indexes
--
-- Ordinary B-tree indexes support lookup by IDs and status fields.
-- GiST indexes support spatial intersection and coverage checks.
--
-- The raster GiST indexes use ST_ConvexHull(rast) so raster payloads can
-- participate in spatial filtering.
-- ---------------------------------------------------------------------

-- Source raster datasets
CREATE INDEX IF NOT EXISTS idx_source_raster_datasets_storage_mode
    ON source_raster_datasets (source_storage_mode);

CREATE INDEX IF NOT EXISTS idx_source_raster_datasets_validation_status
    ON source_raster_datasets (validation_status);

CREATE INDEX IF NOT EXISTS idx_source_raster_datasets_extent_geom
    ON source_raster_datasets
    USING gist (source_extent_geom);

-- Source raster files
CREATE INDEX IF NOT EXISTS idx_source_raster_files_dataset
    ON source_raster_files (source_dataset_id);

CREATE INDEX IF NOT EXISTS idx_source_raster_files_active
    ON source_raster_files (is_active);

CREATE INDEX IF NOT EXISTS idx_source_raster_files_extent_geom
    ON source_raster_files
    USING gist (file_extent_geom);

-- Source raster payloads
CREATE INDEX IF NOT EXISTS idx_source_raster_payloads_dataset
    ON source_raster_payloads (source_dataset_id);

CREATE INDEX IF NOT EXISTS idx_source_raster_payloads_file
    ON source_raster_payloads (source_file_id);

CREATE INDEX IF NOT EXISTS idx_source_raster_payloads_rast_gist
    ON source_raster_payloads
    USING gist (ST_ConvexHull(rast));

-- AOIs
CREATE INDEX IF NOT EXISTS idx_aoi_definitions_geom
    ON aoi_definitions
    USING gist (geom);

CREATE INDEX IF NOT EXISTS idx_aoi_definitions_validation_status
    ON aoi_definitions (validation_status);

-- Runs
CREATE INDEX IF NOT EXISTS idx_terrain_tile_runs_run_id
    ON terrain_tile_runs (run_id);

CREATE INDEX IF NOT EXISTS idx_terrain_tile_runs_source_dataset
    ON terrain_tile_runs (source_dataset_id);

CREATE INDEX IF NOT EXISTS idx_terrain_tile_runs_aoi
    ON terrain_tile_runs (aoi_id);

CREATE INDEX IF NOT EXISTS idx_terrain_tile_runs_operation_status
    ON terrain_tile_runs (operation_status);

CREATE INDEX IF NOT EXISTS idx_terrain_tile_runs_validation_status
    ON terrain_tile_runs (validation_status);

-- Tile plan
CREATE INDEX IF NOT EXISTS idx_terrain_tile_grid_plan_session
    ON terrain_tile_grid_plan (session_id);

CREATE INDEX IF NOT EXISTS idx_terrain_tile_grid_plan_row_col
    ON terrain_tile_grid_plan (session_id, row, col);

CREATE INDEX IF NOT EXISTS idx_terrain_tile_grid_plan_geom
    ON terrain_tile_grid_plan
    USING gist (grid_geom);

CREATE INDEX IF NOT EXISTS idx_terrain_tile_grid_plan_aoi_intersection_geom
    ON terrain_tile_grid_plan
    USING gist (aoi_intersection_geom);

-- Tile outputs
CREATE INDEX IF NOT EXISTS idx_terrain_tile_grid_outputs_session
    ON terrain_tile_grid_outputs (session_id);

CREATE INDEX IF NOT EXISTS idx_terrain_tile_grid_outputs_row_col
    ON terrain_tile_grid_outputs (session_id, row, col);

CREATE INDEX IF NOT EXISTS idx_terrain_tile_grid_outputs_export_status
    ON terrain_tile_grid_outputs (export_status);

CREATE INDEX IF NOT EXISTS idx_terrain_tile_grid_outputs_validation_status
    ON terrain_tile_grid_outputs (validation_status);

-- Generated tile rasters
CREATE INDEX IF NOT EXISTS idx_terrain_tile_grid_rasters_session
    ON terrain_tile_grid_rasters (session_id);

CREATE INDEX IF NOT EXISTS idx_terrain_tile_grid_rasters_role
    ON terrain_tile_grid_rasters (raster_role);

CREATE INDEX IF NOT EXISTS idx_terrain_tile_grid_rasters_rast_gist
    ON terrain_tile_grid_rasters
    USING gist (ST_ConvexHull(rast));

-- ---------------------------------------------------------------------
-- updated_at triggers
-- ---------------------------------------------------------------------

DROP TRIGGER IF EXISTS trg_source_raster_datasets_set_updated_at
    ON source_raster_datasets;

CREATE TRIGGER trg_source_raster_datasets_set_updated_at
BEFORE UPDATE ON source_raster_datasets
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_source_raster_files_set_updated_at
    ON source_raster_files;

CREATE TRIGGER trg_source_raster_files_set_updated_at
BEFORE UPDATE ON source_raster_files
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_aoi_definitions_set_updated_at
    ON aoi_definitions;

CREATE TRIGGER trg_aoi_definitions_set_updated_at
BEFORE UPDATE ON aoi_definitions
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_terrain_tile_grid_outputs_set_updated_at
    ON terrain_tile_grid_outputs;

CREATE TRIGGER trg_terrain_tile_grid_outputs_set_updated_at
BEFORE UPDATE ON terrain_tile_grid_outputs
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

-- ---------------------------------------------------------------------
-- Database metadata comments
--
-- COMMENT ON statements are stored inside PostgreSQL as table/column
-- metadata. They are visible through database inspection tools such as
-- pgAdmin properties panels and through metadata queries.
-- ---------------------------------------------------------------------

COMMENT ON TABLE terrain_schema_metadata IS
'Lightweight schema metadata table used by setup and readiness-check scripts to verify schema identity and version.';

COMMENT ON COLUMN terrain_schema_metadata.metadata_key IS
'Metadata key, such as schema_name or schema_version.';
COMMENT ON COLUMN terrain_schema_metadata.metadata_value IS
'Metadata value associated with metadata_key.';
COMMENT ON COLUMN terrain_schema_metadata.updated_at IS
'Timestamp of the last update to this metadata value.';

-- Source raster dataset comments

COMMENT ON TABLE source_raster_datasets IS
'Dataset-level registry for named source elevation surfaces registered by Mode 1. One row represents a logical source dataset selected later by source_dataset_id.';

COMMENT ON COLUMN source_raster_datasets.source_dataset_id IS
'Stable user-facing identifier for a registered source elevation dataset.';
COMMENT ON COLUMN source_raster_datasets.source_name IS
'Human-readable name for the source dataset.';
COMMENT ON COLUMN source_raster_datasets.source_type IS
'Source elevation type, such as DTM, DSM, DEM, bathymetry, or other.';
COMMENT ON COLUMN source_raster_datasets.source_storage_mode IS
'Controls how Mode 3 accesses source elevation pixels. Expected values include external_file, external_files, virtual_mosaic, and postgis_raster.';
COMMENT ON COLUMN source_raster_datasets.source_crs_authority IS
'CRS authority for the source dataset, usually EPSG.';
COMMENT ON COLUMN source_raster_datasets.source_crs_wkid IS
'Numeric CRS identifier for the source dataset, such as 27700.';
COMMENT ON COLUMN source_raster_datasets.source_crs_label IS
'Human-readable CRS label, such as EPSG:27700.';
COMMENT ON COLUMN source_raster_datasets.source_linear_unit IS
'Linear unit of the source CRS, such as meter.';
COMMENT ON COLUMN source_raster_datasets.source_cell_size_x IS
'Nominal source raster cell size in the X direction.';
COMMENT ON COLUMN source_raster_datasets.source_cell_size_y IS
'Nominal source raster cell size in the Y direction.';
COMMENT ON COLUMN source_raster_datasets.source_cell_size_unit IS
'Unit for source_cell_size_x and source_cell_size_y.';
COMMENT ON COLUMN source_raster_datasets.source_nodata_value IS
'NoData value reported for the source dataset, if known.';
COMMENT ON COLUMN source_raster_datasets.source_extent_geom IS
'Dataset-level bounding envelope polygon for the registered source dataset, in the source/workflow CRS. For multi-file datasets, detailed source coverage is represented by source_raster_files.file_extent_geom records rather than by this dataset-level envelope.';
COMMENT ON COLUMN source_raster_datasets.source_root_path IS
'Dataset-level root folder used with file-level relative_path values to reconstruct portable source file paths.';
COMMENT ON COLUMN source_raster_datasets.path_storage_mode IS
'Path storage strategy, such as root_plus_relative, absolute_paths_only, database_raster_only, or not_applicable.';
COMMENT ON COLUMN source_raster_datasets.primary_source_path IS
'Convenience/display path for a single-file external source dataset. The canonical source file reference is the related source_raster_files row, normally reconstructed from source_raster_datasets.source_root_path plus source_raster_files.relative_path, or from source_raster_files.absolute_path when absolute-path storage is explicitly used.';
COMMENT ON COLUMN source_raster_datasets.vrt_path IS
'Path to a registered virtual mosaic, such as a GDAL VRT, when source_storage_mode = virtual_mosaic.';
COMMENT ON COLUMN source_raster_datasets.vrt_origin IS
'Origin of the registered virtual mosaic path when source_storage_mode = virtual_mosaic. Expected values include created_by_mode1, user_supplied, not_applicable, and unknown.';
COMMENT ON COLUMN source_raster_datasets.file_count IS
'Number of registered physical source files associated with this source dataset.';
COMMENT ON COLUMN source_raster_datasets.has_virtual_mosaic IS
'True if the dataset has an associated virtual mosaic such as a VRT.';
COMMENT ON COLUMN source_raster_datasets.has_postgis_raster_storage IS
'True if original source raster pixels have been loaded into PostGIS.';
COMMENT ON COLUMN source_raster_datasets.source_metadata_json IS
'Flexible dataset-level JSONB metadata that does not yet require dedicated columns.';
COMMENT ON COLUMN source_raster_datasets.provenance_note IS
'Human-readable provenance note for the source dataset.';
COMMENT ON COLUMN source_raster_datasets.registration_status IS
'Registration lifecycle status for the source dataset.';
COMMENT ON COLUMN source_raster_datasets.validation_status IS
'Current validation status for the source dataset.';
COMMENT ON COLUMN source_raster_datasets.last_error_message IS
'Most recent human-readable error message associated with this source dataset.';

-- Source raster file comments

COMMENT ON TABLE source_raster_files IS
'File-level registry for physical source raster files that support a source raster dataset. One row per registered file.';

COMMENT ON COLUMN source_raster_files.source_file_id IS
'Generated primary key for a registered source raster file.';
COMMENT ON COLUMN source_raster_files.source_dataset_id IS
'Foreign key to the source_raster_datasets row that this file supports.';
COMMENT ON COLUMN source_raster_files.filename IS
'Filename of the physical source raster file.';
COMMENT ON COLUMN source_raster_files.relative_path IS
'File path relative to source_raster_datasets.source_root_path. Preferred for portable registration.';
COMMENT ON COLUMN source_raster_files.absolute_path IS
'Absolute path to the source raster file when absolute-path storage is explicitly selected or needed.';
COMMENT ON COLUMN source_raster_files.file_exists_at_registration IS
'True if the file existed when Mode 1 registered or checked it.';
COMMENT ON COLUMN source_raster_files.file_readable_at_registration IS
'True if the file was readable when Mode 1 registered or checked it.';
COMMENT ON COLUMN source_raster_files.file_sha256 IS
'SHA-256 checksum of the source file when computed.';
COMMENT ON COLUMN source_raster_files.file_extent_geom IS
'File-level raster footprint or bounding polygon used for coverage checks and required-file selection.';
COMMENT ON COLUMN source_raster_files.is_part_of_virtual_mosaic IS
'True if this source file participates in a registered virtual mosaic such as a VRT.';
COMMENT ON COLUMN source_raster_files.is_active IS
'True if this registered source file is active for current workflow use.';
COMMENT ON COLUMN source_raster_files.registration_note IS
'Human-readable note about this file registration.';
COMMENT ON COLUMN source_raster_files.validation_status IS
'Current validation status for this source file.';
COMMENT ON COLUMN source_raster_files.last_error_message IS
'Most recent human-readable error message associated with this source file.';

-- Source raster payload comments

COMMENT ON TABLE source_raster_payloads IS
'Conditional table for original source raster payloads loaded into PostGIS when source_storage_mode = postgis_raster. This table stores source rasters, not generated terrain tiles.';

COMMENT ON COLUMN source_raster_payloads.source_payload_id IS
'Generated primary key for an original source raster payload stored in PostGIS.';
COMMENT ON COLUMN source_raster_payloads.source_dataset_id IS
'Foreign key to the registered source dataset represented by this raster payload.';
COMMENT ON COLUMN source_raster_payloads.source_file_id IS
'Optional foreign key to the source file from which this raster payload was loaded.';
COMMENT ON COLUMN source_raster_payloads.raster_role IS
'Role of the source raster payload, such as source_raster, source_tile, source_mosaic, or test_payload.';
COMMENT ON COLUMN source_raster_payloads.rast IS
'Original source raster payload stored as a PostGIS raster.';
COMMENT ON COLUMN source_raster_payloads.loaded_from_path IS
'Path from which the source raster payload was loaded, if applicable.';
COMMENT ON COLUMN source_raster_payloads.payload_metadata_json IS
'Flexible JSONB metadata about the stored source raster payload.';

-- AOI comments

COMMENT ON TABLE aoi_definitions IS
'Registry of reusable AOI definitions created by Mode 2. AOIs are selected later by aoi_id.';

COMMENT ON COLUMN aoi_definitions.aoi_id IS
'Stable user-facing identifier for a registered AOI.';
COMMENT ON COLUMN aoi_definitions.aoi_name IS
'Human-readable name for the AOI.';
COMMENT ON COLUMN aoi_definitions.aoi_source_type IS
'Source type for the AOI, such as geopackage, shapefile, geojson, kml, manual_bbox, or source_raster_extent.';
COMMENT ON COLUMN aoi_definitions.source_file_path IS
'Path to the source vector file when the AOI was imported from a file.';
COMMENT ON COLUMN aoi_definitions.source_layer_name IS
'Layer name selected from a multi-layer source such as a GeoPackage.';
COMMENT ON COLUMN aoi_definitions.source_crs_label IS
'CRS label for the AOI as originally supplied.';
COMMENT ON COLUMN aoi_definitions.working_crs_label IS
'CRS label for the normalized AOI geometry used by the workflow.';
COMMENT ON COLUMN aoi_definitions.geom_original IS
'Optional original AOI geometry before transformation or normalization.';
COMMENT ON COLUMN aoi_definitions.geom IS
'Normalized AOI geometry used for terrain-package planning and coverage checks.';
COMMENT ON COLUMN aoi_definitions.was_reprojected IS
'True if the AOI was transformed from source CRS to workflow working CRS.';
COMMENT ON COLUMN aoi_definitions.reprojection_note IS
'Human-readable explanation of AOI reprojection or CRS handling.';
COMMENT ON COLUMN aoi_definitions.transformation_metadata_json IS
'Flexible JSONB metadata about CRS transformation, geometry repair, or AOI normalization.';
COMMENT ON COLUMN aoi_definitions.area_square_meters IS
'AOI area computed in the workflow working CRS.';
COMMENT ON COLUMN aoi_definitions.provenance_note IS
'Human-readable provenance note for the AOI definition.';

-- Terrain run comments

COMMENT ON TABLE terrain_tile_runs IS
'Run/session-level control table for Mode 3 terrain package operations. Records selected source, AOI, runtime profile, requested stages, completed stages, status, and run-level artifact checksums.';

COMMENT ON COLUMN terrain_tile_runs.session_id IS
'Unique identifier for a specific terrain-package operation/session.';
COMMENT ON COLUMN terrain_tile_runs.run_id IS
'User-facing run identifier. Multiple sessions may derive from or relate to the same run_id.';
COMMENT ON COLUMN terrain_tile_runs.derived_from_session_id IS
'Optional pointer to an earlier session when this run reuses, derives from, validates, or re-exports a previous terrain-package operation.';
COMMENT ON COLUMN terrain_tile_runs.operation_type IS
'Machine-readable Mode 3 operation type, such as plan_only or create_tile_plan_and_build_raster_tiles.';
COMMENT ON COLUMN terrain_tile_runs.operation_label IS
'Human-readable operation label for reports, manifests, and logs.';
COMMENT ON COLUMN terrain_tile_runs.source_manifest_path IS
'Path to manifest-rule.json when Mode 3E uses a manifest as an input recovery handle.';
COMMENT ON COLUMN terrain_tile_runs.workflow_crs_label IS
'Authoritative workflow CRS used for tile planning, tile extents, raster realization, and package geometry.';
COMMENT ON COLUMN terrain_tile_runs.target_engine IS
'Target engine family for runtime-facing metadata, such as unity or unreal.';
COMMENT ON COLUMN terrain_tile_runs.target_geospatial_runtime IS
'Selected geospatial runtime or SDK profile, such as arcgis_maps_sdk_for_unity or cesium_for_unity.';
COMMENT ON COLUMN terrain_tile_runs.runtime_profile_id IS
'Runtime profile identifier used to determine engine-facing placement metadata.';
COMMENT ON COLUMN terrain_tile_runs.runtime_component IS
'Expected engine-side component or georeference object, such as ArcGISLocation or CesiumGeoreference.';
COMMENT ON COLUMN terrain_tile_runs.runtime_parent_name IS
'Intended name for the runtime parent or georeference object that receives terrain tile children.';
COMMENT ON COLUMN terrain_tile_runs.children_use_engine_local_offsets IS
'True if child terrain tiles are placed using engine-local offsets from the runtime parent or georeference origin.';
COMMENT ON COLUMN terrain_tile_runs.working_crs_origin_x IS
'Package origin X coordinate in the authoritative workflow working CRS.';
COMMENT ON COLUMN terrain_tile_runs.working_crs_origin_y IS
'Package origin Y coordinate in the authoritative workflow working CRS.';
COMMENT ON COLUMN terrain_tile_runs.runtime_origin_authority IS
'Describes how runtime origin coordinates are represented, such as working_crs_direct, longitude_latitude_height, or ecef.';
COMMENT ON COLUMN terrain_tile_runs.runtime_longitude_degrees IS
'Runtime origin longitude in degrees when the selected runtime profile requires geographic coordinates.';
COMMENT ON COLUMN terrain_tile_runs.runtime_latitude_degrees IS
'Runtime origin latitude in degrees when the selected runtime profile requires geographic coordinates.';
COMMENT ON COLUMN terrain_tile_runs.runtime_ecef_x_meters IS
'Runtime origin ECEF X coordinate in meters when the selected runtime profile uses ECEF.';
COMMENT ON COLUMN terrain_tile_runs.runtime_warning_json IS
'JSONB array or object containing warnings about runtime georeferencing assumptions or transformations.';
COMMENT ON COLUMN terrain_tile_runs.target_cell_size IS
'Target terrain sample spacing or source sampling size used for package generation.';
COMMENT ON COLUMN terrain_tile_runs.heightmap_resolution IS
'Heightmap samples per side for the engine terrain tile, such as 4097.';
COMMENT ON COLUMN terrain_tile_runs.terrain_intervals_per_side IS
'Number of intervals between heightmap samples, usually heightmap_resolution minus one.';
COMMENT ON COLUMN terrain_tile_runs.tile_size_meters IS
'Ground size of one terrain tile in meters.';
COMMENT ON COLUMN terrain_tile_runs.terrain_height_meters IS
'Vertical terrain height range used for normalized engine heightmap encoding.';
COMMENT ON COLUMN terrain_tile_runs.edge_policy IS
'Policy for handling AOI edges when the AOI does not divide evenly into full engine terrain tiles.';
COMMENT ON COLUMN terrain_tile_runs.vertical_encoding_rule IS
'Rule for converting real elevation values into the exported heightmap encoding.';
COMMENT ON COLUMN terrain_tile_runs.raw_byte_order IS
'Byte order for RAW output, such as little_endian or big_endian.';
COMMENT ON COLUMN terrain_tile_runs.raw_array_orientation_json IS
'JSONB metadata describing sample order inside RAW files so they are not flipped or mirrored on import.';
COMMENT ON COLUMN terrain_tile_runs.nodata_handling_json IS
'JSONB metadata describing how source NoData and padding are handled before engine export.';
COMMENT ON COLUMN terrain_tile_runs.sampling_model_json IS
'JSONB metadata describing how source raster cells are sampled or resampled into engine heightmap samples.';
COMMENT ON COLUMN terrain_tile_runs.grid_convention_json IS
'JSONB metadata describing how tile rows and columns map to working CRS axes and engine-local axes.';
COMMENT ON COLUMN terrain_tile_runs.source_access_summary_json IS
'JSONB summary of source accessibility checks for the run.';
COMMENT ON COLUMN terrain_tile_runs.source_coverage_summary_json IS
'JSONB summary of source coverage checks for the AOI or tile grid.';
COMMENT ON COLUMN terrain_tile_runs.output_root_folder IS
'User-selected or configured root folder for terrain package output.';
COMMENT ON COLUMN terrain_tile_runs.computed_output_folder IS
'Computed output folder for this specific run/session.';
COMMENT ON COLUMN terrain_tile_runs.raw_output_folder IS
'Folder where RAW terrain tile files are written.';
COMMENT ON COLUMN terrain_tile_runs.log_file_path IS
'Path to the package-specific session log, if created.';

COMMENT ON COLUMN terrain_tile_runs.tile_plan_creation_requested IS
'Requested-action field: true if the run should create or use a tile plan.';
COMMENT ON COLUMN terrain_tile_runs.tile_plan_creation_completed IS
'Completed-state field: true if tile plan creation or recovery completed successfully.';
COMMENT ON COLUMN terrain_tile_runs.raster_tile_realization_requested IS
'Requested-action field: true if the run should create raster tile products from source data.';
COMMENT ON COLUMN terrain_tile_runs.raster_tile_realization_completed IS
'Completed-state field: true if raster tile realization completed successfully.';
COMMENT ON COLUMN terrain_tile_runs.derived_raster_storage_requested IS
'Requested-action field: true if the run should store generated terrain-tile raster products in PostGIS.';
COMMENT ON COLUMN terrain_tile_runs.derived_raster_storage_completed IS
'Completed-state field: true if generated terrain-tile raster products were successfully stored in PostGIS.';
COMMENT ON COLUMN terrain_tile_runs.raw_file_export_requested IS
'Requested-action field: true if the run should export RAW terrain files.';
COMMENT ON COLUMN terrain_tile_runs.raw_file_export_completed IS
'Completed-state field: true if RAW terrain files were successfully exported.';
COMMENT ON COLUMN terrain_tile_runs.manifest_rule_generation_requested IS
'Requested-action field: true if the run should generate, copy, or write manifest-rule.json.';
COMMENT ON COLUMN terrain_tile_runs.manifest_rule_generation_completed IS
'Completed-state field: true if manifest-rule.json was successfully generated, copied, or written.';
COMMENT ON COLUMN terrain_tile_runs.tile_catalog_generation_requested IS
'Requested-action field: true if the run should generate tile-catalog.json.';
COMMENT ON COLUMN terrain_tile_runs.tile_catalog_generation_completed IS
'Completed-state field: true if tile-catalog.json was successfully generated.';
COMMENT ON COLUMN terrain_tile_runs.tile_grid_geopackage_export_requested IS
'Requested-action field: true if the run should export a GeoPackage tile grid.';
COMMENT ON COLUMN terrain_tile_runs.tile_grid_geopackage_export_completed IS
'Completed-state field: true if the GeoPackage tile grid was successfully exported.';

COMMENT ON COLUMN terrain_tile_runs.operation_status IS
'Overall lifecycle state of the run/session.';
COMMENT ON COLUMN terrain_tile_runs.validation_status IS
'Overall validation result for the run/session or exported package.';
COMMENT ON COLUMN terrain_tile_runs.failure_reason IS
'Short machine-readable or semi-structured reason for failure or partial completion.';
COMMENT ON COLUMN terrain_tile_runs.last_error_message IS
'Most recent human-readable error message associated with the run/session.';
COMMENT ON COLUMN terrain_tile_runs.manifest_rule_sha256 IS
'SHA-256 checksum of manifest-rule.json when computed.';
COMMENT ON COLUMN terrain_tile_runs.tile_catalog_sha256 IS
'SHA-256 checksum of tile-catalog.json when computed.';
COMMENT ON COLUMN terrain_tile_runs.tile_grid_geopackage_sha256 IS
'SHA-256 checksum of tile_grid.gpkg when computed.';
COMMENT ON COLUMN terrain_tile_runs.run_metadata_json IS
'Flexible JSONB run-level metadata that does not yet require dedicated columns.';

-- Tile plan comments

COMMENT ON TABLE terrain_tile_grid_plan IS
'Planned terrain tile grid generated for a Mode 3 run/session. This table records intended tile geometry and filenames, not proof of realized output.';

COMMENT ON COLUMN terrain_tile_grid_plan.session_id IS
'Foreign key to the terrain_tile_runs session that owns this planned tile.';
COMMENT ON COLUMN terrain_tile_grid_plan.tile_id IS
'Tile identifier, usually based on row and column, such as r0_c0.';
COMMENT ON COLUMN terrain_tile_grid_plan.row IS
'Tile row index in the package grid.';
COMMENT ON COLUMN terrain_tile_grid_plan.col IS
'Tile column index in the package grid.';
COMMENT ON COLUMN terrain_tile_grid_plan.grid_geom IS
'Planned tile polygon in the workflow working CRS.';
COMMENT ON COLUMN terrain_tile_grid_plan.planned_anchor_x IS
'Planned tile anchor X coordinate in the workflow working CRS.';
COMMENT ON COLUMN terrain_tile_grid_plan.planned_anchor_y IS
'Planned tile anchor Y coordinate in the workflow working CRS.';
COMMENT ON COLUMN terrain_tile_grid_plan.planned_anchor_corner IS
'Tile corner used as the planned anchor, such as southwest.';
COMMENT ON COLUMN terrain_tile_grid_plan.raw_filename IS
'Intended RAW filename for this tile. This does not prove the file has been exported.';
COMMENT ON COLUMN terrain_tile_grid_plan.tif_filename IS
'Optional intended GeoTIFF or intermediate raster filename for this tile.';
COMMENT ON COLUMN terrain_tile_grid_plan.edge_policy IS
'Edge policy used when planning this tile.';
COMMENT ON COLUMN terrain_tile_grid_plan.is_edge_tile IS
'True if the planned tile lies on the edge of the AOI-enclosing grid.';
COMMENT ON COLUMN terrain_tile_grid_plan.aoi_intersection_geom IS
'Geometry representing the portion of the AOI intersecting this planned tile.';
COMMENT ON COLUMN terrain_tile_grid_plan.aoi_occupied_fraction IS
'Fraction of the planned tile occupied by the AOI.';
COMMENT ON COLUMN terrain_tile_grid_plan.plan_status IS
'Status of the planned tile record.';

-- Tile output comments

COMMENT ON TABLE terrain_tile_grid_outputs IS
'Lightweight per-tile output metadata for realized or exported terrain tiles. This table is the primary database source for tile-catalog.json and does not store raster payloads.';

COMMENT ON COLUMN terrain_tile_grid_outputs.raw_filename IS
'RAW filename for the realized or exported terrain tile.';
COMMENT ON COLUMN terrain_tile_grid_outputs.raw_relative_path IS
'Relative path to the RAW file from the package output folder.';
COMMENT ON COLUMN terrain_tile_grid_outputs.engine_local_x IS
'Engine-local X offset for the terrain tile relative to the runtime parent or georeference origin.';
COMMENT ON COLUMN terrain_tile_grid_outputs.engine_local_y IS
'Engine-local Y offset for the terrain tile. Usually zero because elevation is encoded in the heightmap.';
COMMENT ON COLUMN terrain_tile_grid_outputs.engine_local_z IS
'Engine-local Z offset for the terrain tile relative to the runtime parent or georeference origin.';
COMMENT ON COLUMN terrain_tile_grid_outputs.engine_terrain_size_x_meters IS
'Engine terrain object size in the X direction.';
COMMENT ON COLUMN terrain_tile_grid_outputs.engine_terrain_size_y_meters IS
'Engine terrain vertical size or height range.';
COMMENT ON COLUMN terrain_tile_grid_outputs.engine_terrain_size_z_meters IS
'Engine terrain object size in the Z direction.';
COMMENT ON COLUMN terrain_tile_grid_outputs.working_crs_anchor_x IS
'Tile anchor X coordinate in the authoritative workflow working CRS.';
COMMENT ON COLUMN terrain_tile_grid_outputs.working_crs_anchor_y IS
'Tile anchor Y coordinate in the authoritative workflow working CRS.';
COMMENT ON COLUMN terrain_tile_grid_outputs.working_crs_anchor_corner IS
'Tile corner used as the working CRS anchor.';
COMMENT ON COLUMN terrain_tile_grid_outputs.working_crs_xmin IS
'Minimum X coordinate of the realized tile extent in the workflow working CRS.';
COMMENT ON COLUMN terrain_tile_grid_outputs.working_crs_ymin IS
'Minimum Y coordinate of the realized tile extent in the workflow working CRS.';
COMMENT ON COLUMN terrain_tile_grid_outputs.working_crs_xmax IS
'Maximum X coordinate of the realized tile extent in the workflow working CRS.';
COMMENT ON COLUMN terrain_tile_grid_outputs.working_crs_ymax IS
'Maximum Y coordinate of the realized tile extent in the workflow working CRS.';
COMMENT ON COLUMN terrain_tile_grid_outputs.is_full_aoi_tile IS
'True if the AOI occupies the full tile footprint.';
COMMENT ON COLUMN terrain_tile_grid_outputs.is_padded_beyond_aoi IS
'True if this tile includes padding beyond the AOI.';
COMMENT ON COLUMN terrain_tile_grid_outputs.is_partial_tile IS
'True if the tile is not fully occupied by AOI content or source coverage.';
COMMENT ON COLUMN terrain_tile_grid_outputs.source_coverage_status IS
'Coverage status of source data for this realized tile.';
COMMENT ON COLUMN terrain_tile_grid_outputs.tile_min_elevation_m IS
'Minimum elevation in meters for this tile after realization.';
COMMENT ON COLUMN terrain_tile_grid_outputs.tile_max_elevation_m IS
'Maximum elevation in meters for this tile after realization.';
COMMENT ON COLUMN terrain_tile_grid_outputs.expected_file_size_bytes IS
'Expected RAW file size based on resolution, bit depth, and band count.';
COMMENT ON COLUMN terrain_tile_grid_outputs.actual_file_size_bytes IS
'Actual exported RAW file size when checked.';
COMMENT ON COLUMN terrain_tile_grid_outputs.raw_sha256 IS
'SHA-256 checksum of the exported RAW file when computed.';
COMMENT ON COLUMN terrain_tile_grid_outputs.export_status IS
'Export status for this tile.';
COMMENT ON COLUMN terrain_tile_grid_outputs.validation_status IS
'Validation status for this tile.';
COMMENT ON COLUMN terrain_tile_grid_outputs.seam_validation_status IS
'Validation status for tile edge continuity with neighboring tiles.';
COMMENT ON COLUMN terrain_tile_grid_outputs.output_metadata_json IS
'Flexible JSONB output metadata that does not yet require dedicated columns.';
COMMENT ON COLUMN terrain_tile_grid_outputs.source_contribution_json IS
'Temporary JSONB source contribution metadata until a dedicated terrain_tile_source_contributions table is needed.';
COMMENT ON COLUMN terrain_tile_grid_outputs.provenance_note IS
'Human-readable provenance note for this tile output.';

-- Generated tile raster comments

COMMENT ON TABLE terrain_tile_grid_rasters IS
'Optional heavy storage for generated terrain-tile raster payloads created by Mode 3. This table does not store original source rasters.';

COMMENT ON COLUMN terrain_tile_grid_rasters.session_id IS
'Foreign key to the terrain_tile_runs session that owns this generated raster tile.';
COMMENT ON COLUMN terrain_tile_grid_rasters.tile_id IS
'Tile identifier matching terrain_tile_grid_outputs.';
COMMENT ON COLUMN terrain_tile_grid_rasters.raster_role IS
'Role of the generated raster payload, such as realized_height_tile, normalized_uint16_tile, intermediate_float_tile, or debug_tile.';
COMMENT ON COLUMN terrain_tile_grid_rasters.rast IS
'Generated terrain-tile raster payload stored as a PostGIS raster.';
COMMENT ON COLUMN terrain_tile_grid_rasters.raster_metadata_json IS
'Flexible JSONB metadata about the generated raster payload.';

COMMIT;