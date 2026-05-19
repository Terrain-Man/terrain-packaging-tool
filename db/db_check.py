# -*- coding: utf-8 -*-
"""
Created on Mon May 11 17:10:59 2026

@author: Peter Seabrook with GPT assistance
"""

"""
db_check.py

Checks whether the PostgreSQL/PostGIS database is ready for the GEOG670
terrain packaging tool.

This script does not create tables. It only verifies that db_prepare.py and
schema.sql have prepared the database correctly.

It writes:
    logs/db_check.log
    logs/db_check_reports/db_check_report_<timestamp>.csv

Recommended use from the project root:

    python db/db_check.py

Revision history:
    2026-05-11 - Initial database readiness check script.
    2026-05-12 - Internal script version 0.1.1.
                 Updated expected schema checks for the revised schema.sql:
                 added source_raster_datasets.vrt_origin and
                 source_raster_datasets_vrt_origin_chk.
                 Updated EXPECTED_SCHEMA_VERSION to 0.1.1 to match
                 terrain_schema_metadata in the revised schema.sql.
    2026-05-12 - Internal script version 0.1.2.
                 Added explicit logging of where the expected database
                 schema version came from: tool_config.yaml or the internal
                 fallback EXPECTED_SCHEMA_VERSION constant.

Notes:
    DB_CHECK_SCRIPT_VERSION is the internal version of this checking script.
    EXPECTED_SCHEMA_VERSION is the fallback expected value for the database
    schema version if config/tool_config.yaml is missing or does not define
    defaults.expected_database_schema_version. When tool_config.yaml provides
    that setting, the config value takes precedence.
"""

from pathlib import Path
from datetime import datetime
import csv
import logging
import os
import sys

try:
    import yaml
except ImportError:
    print("Missing dependency: pyyaml")
    print("Install with: pip install pyyaml")
    sys.exit(1)

try:
    import psycopg
except ImportError:
    print("Missing dependency: psycopg")
    print("Install with: pip install psycopg")
    sys.exit(1)


DB_CHECK_SCRIPT_VERSION = "0.1.2"
EXPECTED_SCHEMA_VERSION = "0.1.1"

REQUIRED_EXTENSIONS = [
    "postgis",
    "postgis_raster",
]

EXPECTED_TABLES = [
    "terrain_schema_metadata",
    "source_raster_datasets",
    "source_raster_files",
    "source_raster_payloads",
    "aoi_definitions",
    "terrain_tile_runs",
    "terrain_tile_grid_plan",
    "terrain_tile_grid_outputs",
    "terrain_tile_grid_rasters",
]

EXPECTED_COLUMNS = {
    "terrain_schema_metadata": [
        "metadata_key",
        "metadata_value",
        "updated_at",
    ],
    "source_raster_datasets": [
        "source_dataset_id",
        "source_name",
        "source_type",
        "source_storage_mode",
        "source_crs_authority",
        "source_crs_wkid",
        "source_crs_label",
        "source_linear_unit",
        "source_cell_size_x",
        "source_cell_size_y",
        "source_cell_size_unit",
        "source_nodata_value",
        "source_extent_geom",
        "source_xmin",
        "source_ymin",
        "source_xmax",
        "source_ymax",
        "source_root_path",
        "path_storage_mode",
        "primary_source_path",
        "vrt_path",
        "vrt_origin",
        "file_count",
        "has_virtual_mosaic",
        "has_postgis_raster_storage",
        "source_metadata_json",
        "provenance_note",
        "created_at",
        "updated_at",
        "registration_status",
        "validation_status",
        "last_error_message",
    ],
    "source_raster_files": [
        "source_file_id",
        "source_dataset_id",
        "filename",
        "relative_path",
        "absolute_path",
        "file_exists_at_registration",
        "file_readable_at_registration",
        "file_size_bytes",
        "file_modified_time",
        "file_sha256",
        "file_crs_authority",
        "file_crs_wkid",
        "file_crs_label",
        "file_cell_size_x",
        "file_cell_size_y",
        "file_nodata_value",
        "raster_width_pixels",
        "raster_height_pixels",
        "raster_band_count",
        "raster_dtype",
        "file_extent_geom",
        "file_xmin",
        "file_ymin",
        "file_xmax",
        "file_ymax",
        "is_part_of_virtual_mosaic",
        "is_active",
        "registration_note",
        "created_at",
        "updated_at",
        "validation_status",
        "last_error_message",
    ],
    "source_raster_payloads": [
        "source_payload_id",
        "source_dataset_id",
        "source_file_id",
        "raster_role",
        "rast",
        "source_crs_wkid",
        "source_crs_label",
        "loaded_from_path",
        "loaded_at",
        "payload_metadata_json",
        "validation_status",
        "last_error_message",
    ],
    "aoi_definitions": [
        "aoi_id",
        "aoi_name",
        "description",
        "aoi_source_type",
        "source_file_path",
        "source_layer_name",
        "source_crs_authority",
        "source_crs_wkid",
        "source_crs_label",
        "working_crs_authority",
        "working_crs_wkid",
        "working_crs_label",
        "geom_original",
        "geom",
        "was_reprojected",
        "reprojection_note",
        "transformation_metadata_json",
        "area_square_meters",
        "bbox_xmin",
        "bbox_ymin",
        "bbox_xmax",
        "bbox_ymax",
        "centroid_x",
        "centroid_y",
        "created_at",
        "updated_at",
        "validation_status",
        "last_error_message",
        "provenance_note",
    ],
    "terrain_tile_runs": [
        "session_id",
        "run_id",
        "derived_from_session_id",
        "operation_type",
        "operation_label",
        "source_manifest_path",
        "source_dataset_id",
        "aoi_id",
        "workflow_crs_authority",
        "workflow_crs_wkid",
        "workflow_crs_label",
        "workflow_linear_unit",
        "target_engine",
        "target_geospatial_runtime",
        "runtime_profile_id",
        "runtime_profile_schema_version",
        "runtime_component",
        "runtime_parent_name",
        "children_use_engine_local_offsets",
        "working_crs_origin_x",
        "working_crs_origin_y",
        "working_crs_origin_z_meters",
        "origin_anchor_corner",
        "runtime_origin_authority",
        "runtime_origin_crs_authority",
        "runtime_origin_crs_wkid",
        "runtime_origin_crs_label",
        "runtime_origin_x",
        "runtime_origin_y",
        "runtime_origin_z_meters",
        "runtime_longitude_degrees",
        "runtime_latitude_degrees",
        "runtime_ellipsoid_height_meters",
        "runtime_ecef_x_meters",
        "runtime_ecef_y_meters",
        "runtime_ecef_z_meters",
        "runtime_heading_degrees",
        "runtime_pitch_degrees",
        "runtime_roll_degrees",
        "runtime_warning_json",
        "target_cell_size",
        "heightmap_resolution",
        "terrain_intervals_per_side",
        "tile_size_meters",
        "terrain_height_meters",
        "edge_policy",
        "vertical_encoding_rule",
        "raw_bit_depth",
        "raw_data_type",
        "raw_byte_order",
        "raw_array_orientation_json",
        "nodata_handling_json",
        "sampling_model_json",
        "grid_convention_json",
        "source_access_summary_json",
        "source_coverage_summary_json",
        "output_root_folder",
        "computed_output_folder",
        "raw_output_folder",
        "log_file_path",
        "tile_plan_creation_requested",
        "tile_plan_creation_completed",
        "raster_tile_realization_requested",
        "raster_tile_realization_completed",
        "derived_raster_storage_requested",
        "derived_raster_storage_completed",
        "raw_file_export_requested",
        "raw_file_export_completed",
        "manifest_rule_generation_requested",
        "manifest_rule_generation_completed",
        "tile_catalog_generation_requested",
        "tile_catalog_generation_completed",
        "tile_grid_geopackage_export_requested",
        "tile_grid_geopackage_export_completed",
        "created_at",
        "started_at",
        "completed_at",
        "operation_status",
        "validation_status",
        "failure_reason",
        "last_error_message",
        "manifest_rule_sha256",
        "tile_catalog_sha256",
        "tile_grid_geopackage_sha256",
        "run_metadata_json",
    ],
    "terrain_tile_grid_plan": [
        "session_id",
        "tile_id",
        "row",
        "col",
        "grid_geom",
        "planned_xmin",
        "planned_ymin",
        "planned_xmax",
        "planned_ymax",
        "planned_anchor_x",
        "planned_anchor_y",
        "planned_anchor_corner",
        "working_crs_wkid",
        "working_crs_label",
        "raw_filename",
        "tif_filename",
        "edge_policy",
        "is_edge_tile",
        "planned_tile_width_meters",
        "planned_tile_height_meters",
        "aoi_intersection_geom",
        "aoi_occupied_width_meters",
        "aoi_occupied_height_meters",
        "aoi_occupied_fraction",
        "created_at",
        "plan_status",
    ],
    "terrain_tile_grid_outputs": [
        "session_id",
        "tile_id",
        "row",
        "col",
        "raw_filename",
        "raw_relative_path",
        "tif_filename",
        "tif_relative_path",
        "engine_local_x",
        "engine_local_y",
        "engine_local_z",
        "engine_terrain_size_x_meters",
        "engine_terrain_size_y_meters",
        "engine_terrain_size_z_meters",
        "working_crs_anchor_x",
        "working_crs_anchor_y",
        "working_crs_anchor_corner",
        "working_crs_xmin",
        "working_crs_ymin",
        "working_crs_xmax",
        "working_crs_ymax",
        "is_full_aoi_tile",
        "is_padded_beyond_aoi",
        "is_partial_tile",
        "aoi_occupied_width_meters",
        "aoi_occupied_height_meters",
        "aoi_occupied_fraction",
        "has_full_source_coverage",
        "contains_source_nodata",
        "source_coverage_fraction",
        "source_coverage_status",
        "tile_min_elevation_m",
        "tile_max_elevation_m",
        "tile_mean_elevation_m",
        "expected_file_size_bytes",
        "actual_file_size_bytes",
        "raw_sha256",
        "export_status",
        "validation_status",
        "seam_validation_status",
        "last_error_message",
        "created_at",
        "updated_at",
        "output_metadata_json",
        "source_contribution_json",
        "provenance_note",
    ],
    "terrain_tile_grid_rasters": [
        "session_id",
        "tile_id",
        "row",
        "col",
        "filename",
        "raster_role",
        "rast",
        "working_crs_wkid",
        "working_crs_label",
        "created_at",
        "raster_metadata_json",
    ],
}

EXPECTED_INDEXES = [
    "idx_source_raster_datasets_storage_mode",
    "idx_source_raster_datasets_validation_status",
    "idx_source_raster_datasets_extent_geom",
    "idx_source_raster_files_dataset",
    "idx_source_raster_files_active",
    "idx_source_raster_files_extent_geom",
    "idx_source_raster_payloads_dataset",
    "idx_source_raster_payloads_file",
    "idx_source_raster_payloads_rast_gist",
    "idx_aoi_definitions_geom",
    "idx_aoi_definitions_validation_status",
    "idx_terrain_tile_runs_run_id",
    "idx_terrain_tile_runs_source_dataset",
    "idx_terrain_tile_runs_aoi",
    "idx_terrain_tile_runs_operation_status",
    "idx_terrain_tile_runs_validation_status",
    "idx_terrain_tile_grid_plan_session",
    "idx_terrain_tile_grid_plan_row_col",
    "idx_terrain_tile_grid_plan_geom",
    "idx_terrain_tile_grid_plan_aoi_intersection_geom",
    "idx_terrain_tile_grid_outputs_session",
    "idx_terrain_tile_grid_outputs_row_col",
    "idx_terrain_tile_grid_outputs_export_status",
    "idx_terrain_tile_grid_outputs_validation_status",
    "idx_terrain_tile_grid_rasters_session",
    "idx_terrain_tile_grid_rasters_role",
    "idx_terrain_tile_grid_rasters_rast_gist",
]

EXPECTED_CONSTRAINTS = [
    "source_raster_datasets_storage_mode_chk",
    "source_raster_datasets_path_storage_mode_chk",
    "source_raster_datasets_vrt_origin_chk",
    "source_raster_datasets_file_count_chk",
    "source_raster_datasets_validation_status_chk",
    "source_raster_datasets_registration_status_chk",
    "source_raster_files_dataset_fk",
    "source_raster_files_file_size_chk",
    "source_raster_files_width_chk",
    "source_raster_files_height_chk",
    "source_raster_files_band_count_chk",
    "source_raster_files_validation_status_chk",
    "source_raster_payloads_dataset_fk",
    "source_raster_payloads_file_fk",
    "source_raster_payloads_validation_status_chk",
    "aoi_definitions_source_type_chk",
    "aoi_definitions_area_chk",
    "aoi_definitions_validation_status_chk",
    "terrain_tile_runs_source_dataset_fk",
    "terrain_tile_runs_aoi_fk",
    "terrain_tile_runs_derived_from_fk",
    "terrain_tile_runs_heightmap_resolution_chk",
    "terrain_tile_runs_intervals_chk",
    "terrain_tile_runs_tile_size_chk",
    "terrain_tile_runs_terrain_height_chk",
    "terrain_tile_runs_raw_bit_depth_chk",
    "terrain_tile_runs_byte_order_chk",
    "terrain_tile_runs_operation_status_chk",
    "terrain_tile_runs_validation_status_chk",
    "terrain_tile_grid_plan_run_fk",
    "terrain_tile_grid_plan_row_chk",
    "terrain_tile_grid_plan_col_chk",
    "terrain_tile_grid_plan_width_chk",
    "terrain_tile_grid_plan_height_chk",
    "terrain_tile_grid_plan_occupied_fraction_chk",
    "terrain_tile_grid_plan_status_chk",
    "terrain_tile_grid_outputs_plan_fk",
    "terrain_tile_grid_outputs_row_chk",
    "terrain_tile_grid_outputs_col_chk",
    "terrain_tile_grid_outputs_terrain_size_x_chk",
    "terrain_tile_grid_outputs_terrain_size_y_chk",
    "terrain_tile_grid_outputs_terrain_size_z_chk",
    "terrain_tile_grid_outputs_aoi_fraction_chk",
    "terrain_tile_grid_outputs_source_fraction_chk",
    "terrain_tile_grid_outputs_expected_size_chk",
    "terrain_tile_grid_outputs_actual_size_chk",
    "terrain_tile_grid_outputs_export_status_chk",
    "terrain_tile_grid_outputs_validation_status_chk",
    "terrain_tile_grid_outputs_seam_status_chk",
    "terrain_tile_grid_rasters_output_fk",
    "terrain_tile_grid_rasters_row_chk",
    "terrain_tile_grid_rasters_col_chk",
]

EXPECTED_TRIGGERS = [
    "trg_source_raster_datasets_set_updated_at",
    "trg_source_raster_files_set_updated_at",
    "trg_aoi_definitions_set_updated_at",
    "trg_terrain_tile_grid_outputs_set_updated_at",
]

CHECK_RESULTS = []


def get_project_root() -> Path:
    """
    Return the project root.

    This script is expected to live in:

        project_root/db/db_check.py
    """
    return Path(__file__).resolve().parents[1]


def configure_logging(project_root: Path) -> logging.Logger:
    """
    Configure console and file logging for database readiness checks.
    """
    logs_dir = project_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    log_path = logs_dir / "db_check.log"

    logger = logging.getLogger("db_check")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def find_config_file(project_root: Path, base_name: str) -> Path:
    """
    Find a YAML config file using either .yaml or .yml.

    Prefers .yaml if both exist.
    """
    config_dir = project_root / "config"

    yaml_path = config_dir / f"{base_name}.yaml"
    yml_path = config_dir / f"{base_name}.yml"

    if yaml_path.exists():
        return yaml_path

    if yml_path.exists():
        return yml_path

    raise FileNotFoundError(
        f"Required config file not found. Expected either:\n"
        f"  {yaml_path}\n"
        f"  {yml_path}"
    )


def read_yaml_file(path: Path) -> dict:
    """
    Read a YAML file and return its contents as a dictionary.
    """
    if not path.exists():
        raise FileNotFoundError(f"Required config file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    if data is None:
        raise ValueError(f"YAML file is empty: {path}")

    if not isinstance(data, dict):
        raise ValueError(f"YAML file must contain a top-level mapping: {path}")

    return data


def get_database_password(database_config: dict) -> str | None:
    """
    Read the database password from the configured environment variable.
    """
    database_section = database_config.get("database", {})
    password_env_var = database_section.get("password_env_var")

    if not password_env_var:
        return None

    password = os.environ.get(password_env_var)

    if password is None:
        raise RuntimeError(
            f"Database password environment variable is not set: {password_env_var}"
        )

    return password


def build_connection_info(database_config: dict) -> dict:
    """
    Build a psycopg connection dictionary from database_config.yaml.
    """
    database_section = database_config.get("database", {})
    connection_section = database_config.get("connection", {})

    required_keys = ["host", "port", "name", "user"]
    missing = [key for key in required_keys if key not in database_section]

    if missing:
        missing_text = ", ".join(missing)
        raise ValueError(f"Missing required database config keys: {missing_text}")

    application_name = connection_section.get(
        "application_name",
        "geog670_terrain_tool",
    )

    connection_info = {
        "host": database_section["host"],
        "port": int(database_section["port"]),
        "dbname": database_section["name"],
        "user": database_section["user"],
        "password": get_database_password(database_config),
        "connect_timeout": int(connection_section.get("connect_timeout_seconds", 10)),
        "application_name": f"{application_name}_db_check",
    }

    return connection_info


def get_schema_name(database_config: dict) -> str:
    """
    Return the configured PostgreSQL schema name.
    """
    schema_section = database_config.get("schema", {})
    return schema_section.get("name", "public")


def get_expected_schema_version(
    tool_config: dict | None,
    tool_config_path: Path | None = None,
) -> tuple[str, str]:
    """
    Return the expected database schema version and explain where it came from.

    Precedence:
        1. config/tool_config.yaml defaults.expected_database_schema_version
        2. Internal fallback constant EXPECTED_SCHEMA_VERSION

    Returning the source string makes version mismatches easier to diagnose.
    """
    if tool_config is None:
        return (
            EXPECTED_SCHEMA_VERSION,
            "internal fallback EXPECTED_SCHEMA_VERSION; tool_config.yaml/tool_config.yml was not found",
        )

    defaults_section = tool_config.get("defaults", {})

    if "expected_database_schema_version" in defaults_section:
        if tool_config_path is None:
            source_text = "tool_config defaults.expected_database_schema_version"
        else:
            source_text = (
                f"{tool_config_path} "
                "defaults.expected_database_schema_version"
            )

        return defaults_section["expected_database_schema_version"], source_text

    return (
        EXPECTED_SCHEMA_VERSION,
        "internal fallback EXPECTED_SCHEMA_VERSION; "
        "tool_config lacks defaults.expected_database_schema_version",
    )


def record_check_result(status: str, message: str) -> None:
    """
    Store one structured check result for CSV reporting.
    """
    CHECK_RESULTS.append(
        {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "status": status,
            "message": message,
        }
    )


def record_failure(failures: list[str], message: str, logger: logging.Logger) -> None:
    failures.append(message)
    record_check_result("FAIL", message)
    logger.error("FAIL: %s", message)


def record_warning(warnings: list[str], message: str, logger: logging.Logger) -> None:
    warnings.append(message)
    record_check_result("WARN", message)
    logger.warning("WARN: %s", message)


def record_success(message: str, logger: logging.Logger) -> None:
    record_check_result("PASS", message)
    logger.info("PASS: %s", message)


def check_connection(conn, logger: logging.Logger) -> None:
    """
    Check that a simple query works.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT current_database(), current_user;")
        database_name, user_name = cur.fetchone()

    record_success(
        f"Connected to database '{database_name}' as user '{user_name}'.",
        logger,
    )


def check_extensions(conn, failures: list[str], logger: logging.Logger) -> None:
    """
    Check required PostgreSQL extensions.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT extname FROM pg_extension;")
        installed = {row[0] for row in cur.fetchall()}

    for extension_name in REQUIRED_EXTENSIONS:
        if extension_name in installed:
            record_success(f"Extension installed: {extension_name}", logger)
        else:
            record_failure(
                failures,
                f"Required extension missing: {extension_name}",
                logger,
            )


def check_postgis_version(conn, warnings: list[str], logger: logging.Logger) -> None:
    """
    Log PostGIS version information if available.
    """
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT PostGIS_Full_Version();")
            version_text = cur.fetchone()[0]

        record_success(f"PostGIS version detected: {version_text}", logger)

    except Exception as error:
        record_warning(
            warnings,
            f"Could not read PostGIS version information: {error}",
            logger,
        )


def check_schema_metadata(
    conn,
    expected_schema_version: str,
    failures: list[str],
    logger: logging.Logger,
) -> None:
    """
    Check terrain_schema_metadata and schema_version.
    """
    query = """
        SELECT metadata_value
        FROM terrain_schema_metadata
        WHERE metadata_key = 'schema_version';
    """

    try:
        with conn.cursor() as cur:
            cur.execute(query)
            row = cur.fetchone()

    except Exception as error:
        record_failure(
            failures,
            f"Could not query terrain_schema_metadata: {error}",
            logger,
        )
        return

    if row is None:
        record_failure(
            failures,
            "terrain_schema_metadata exists but schema_version is missing.",
            logger,
        )
        return

    actual_schema_version = row[0]

    if actual_schema_version == expected_schema_version:
        record_success(f"Schema version matches expected value: {actual_schema_version}", logger)
    else:
        record_failure(
            failures,
            f"Schema version mismatch. Expected {expected_schema_version}, found {actual_schema_version}.",
            logger,
        )


def get_existing_tables(conn, schema_name: str) -> set[str]:
    """
    Return table names in the configured schema.
    """
    query = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = %s
          AND table_type = 'BASE TABLE';
    """

    with conn.cursor() as cur:
        cur.execute(query, (schema_name,))
        return {row[0] for row in cur.fetchall()}


def check_tables(
    conn,
    schema_name: str,
    failures: list[str],
    logger: logging.Logger,
) -> None:
    """
    Check that required tables exist.
    """
    existing_tables = get_existing_tables(conn, schema_name)

    for table_name in EXPECTED_TABLES:
        if table_name in existing_tables:
            record_success(f"Table exists: {schema_name}.{table_name}", logger)
        else:
            record_failure(
                failures,
                f"Required table missing: {schema_name}.{table_name}",
                logger,
            )


def get_existing_columns(conn, schema_name: str, table_name: str) -> set[str]:
    """
    Return column names for a table.
    """
    query = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = %s
          AND table_name = %s;
    """

    with conn.cursor() as cur:
        cur.execute(query, (schema_name, table_name))
        return {row[0] for row in cur.fetchall()}


def check_columns(
    conn,
    schema_name: str,
    failures: list[str],
    logger: logging.Logger,
) -> None:
    """
    Check required columns for each expected table.
    """
    existing_tables = get_existing_tables(conn, schema_name)

    for table_name, expected_columns in EXPECTED_COLUMNS.items():
        if table_name not in existing_tables:
            continue

        existing_columns = get_existing_columns(conn, schema_name, table_name)
        missing_columns = [
            column_name
            for column_name in expected_columns
            if column_name not in existing_columns
        ]

        if missing_columns:
            record_failure(
                failures,
                f"Table {schema_name}.{table_name} is missing columns: {', '.join(missing_columns)}",
                logger,
            )
        else:
            record_success(f"Required columns present for: {schema_name}.{table_name}", logger)


def get_existing_indexes(conn, schema_name: str) -> set[str]:
    """
    Return index names in the configured schema.
    """
    query = """
        SELECT indexname
        FROM pg_indexes
        WHERE schemaname = %s;
    """

    with conn.cursor() as cur:
        cur.execute(query, (schema_name,))
        return {row[0] for row in cur.fetchall()}


def check_indexes(
    conn,
    schema_name: str,
    failures: list[str],
    logger: logging.Logger,
) -> None:
    """
    Check required indexes.
    """
    existing_indexes = get_existing_indexes(conn, schema_name)

    for index_name in EXPECTED_INDEXES:
        if index_name in existing_indexes:
            record_success(f"Index exists: {index_name}", logger)
        else:
            record_failure(
                failures,
                f"Required index missing: {schema_name}.{index_name}",
                logger,
            )


def get_existing_constraints(conn, schema_name: str) -> set[str]:
    """
    Return named constraints in the configured schema.
    """
    query = """
        SELECT con.conname
        FROM pg_constraint con
        JOIN pg_namespace nsp
          ON nsp.oid = con.connamespace
        WHERE nsp.nspname = %s;
    """

    with conn.cursor() as cur:
        cur.execute(query, (schema_name,))
        return {row[0] for row in cur.fetchall()}


def check_constraints(
    conn,
    schema_name: str,
    failures: list[str],
    logger: logging.Logger,
) -> None:
    """
    Check required named constraints.
    """
    existing_constraints = get_existing_constraints(conn, schema_name)

    for constraint_name in EXPECTED_CONSTRAINTS:
        if constraint_name in existing_constraints:
            record_success(f"Constraint exists: {constraint_name}", logger)
        else:
            record_failure(
                failures,
                f"Required constraint missing: {schema_name}.{constraint_name}",
                logger,
            )


def get_existing_triggers(conn, schema_name: str) -> set[str]:
    """
    Return non-internal trigger names in the configured schema.
    """
    query = """
        SELECT trg.tgname
        FROM pg_trigger trg
        JOIN pg_class cls
          ON cls.oid = trg.tgrelid
        JOIN pg_namespace nsp
          ON nsp.oid = cls.relnamespace
        WHERE nsp.nspname = %s
          AND NOT trg.tgisinternal;
    """

    with conn.cursor() as cur:
        cur.execute(query, (schema_name,))
        return {row[0] for row in cur.fetchall()}


def check_triggers(
    conn,
    schema_name: str,
    failures: list[str],
    logger: logging.Logger,
) -> None:
    """
    Check expected updated_at triggers.
    """
    existing_triggers = get_existing_triggers(conn, schema_name)

    for trigger_name in EXPECTED_TRIGGERS:
        if trigger_name in existing_triggers:
            record_success(f"Trigger exists: {trigger_name}", logger)
        else:
            record_failure(
                failures,
                f"Required trigger missing: {schema_name}.{trigger_name}",
                logger,
            )


def check_set_updated_at_function(
    conn,
    schema_name: str,
    failures: list[str],
    logger: logging.Logger,
) -> None:
    """
    Check that the set_updated_at trigger function exists.
    """
    query = """
        SELECT 1
        FROM pg_proc proc
        JOIN pg_namespace nsp
          ON nsp.oid = proc.pronamespace
        WHERE nsp.nspname = %s
          AND proc.proname = 'set_updated_at'
        LIMIT 1;
    """

    with conn.cursor() as cur:
        cur.execute(query, (schema_name,))
        row = cur.fetchone()

    if row is None:
        record_failure(
            failures,
            f"Required trigger function missing: {schema_name}.set_updated_at",
            logger,
        )
    else:
        record_success(f"Trigger function exists: {schema_name}.set_updated_at", logger)


def write_check_report(project_root: Path, logger: logging.Logger) -> Path:
    """
    Write a fully quoted UTF-8 CSV report of database readiness checks.

    Returns:
        Path to the written CSV report.
    """
    report_dir = project_root / "logs" / "db_check_reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = report_dir / f"db_check_report_{timestamp}.csv"

    fieldnames = [
        "timestamp",
        "status",
        "message",
    ]

    with report_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
            quoting=csv.QUOTE_ALL,
            lineterminator="\n",
        )

        writer.writeheader()

        for row in CHECK_RESULTS:
            writer.writerow(row)

    logger.info("Database readiness CSV report written: %s", report_path)
    return report_path


def print_summary(failures: list[str], warnings: list[str]) -> None:
    """
    Print a simple final readiness summary.
    """
    print("\nDatabase readiness summary")
    print("--------------------------")

    if not failures and not warnings:
        print("Status: READY")
        print("No failures or warnings were found.")
        return

    if failures:
        print("Status: NOT READY")
        print(f"Failures: {len(failures)}")

        for failure in failures:
            print(f"  - {failure}")
    else:
        print("Status: READY WITH WARNINGS")

    if warnings:
        print(f"\nWarnings: {len(warnings)}")

        for warning in warnings:
            print(f"  - {warning}")


def main() -> None:
    """
    Main entry point.
    """
    project_root = get_project_root()
    logger = configure_logging(project_root)

    failures: list[str] = []
    warnings: list[str] = []

    logger.info("Starting database readiness check.")
    logger.info("db_check.py internal script version: %s", DB_CHECK_SCRIPT_VERSION)
    logger.info("Project root: %s", project_root)

    try:
        database_config_path = find_config_file(project_root, "database_config")
        database_config = read_yaml_file(database_config_path)

        tool_config_path: Path | None = None

        try:
            tool_config_path = find_config_file(project_root, "tool_config")
            tool_config = read_yaml_file(tool_config_path)
        except FileNotFoundError:
            tool_config = None
            record_warning(
                warnings,
                "tool_config.yaml/tool_config.yml not found. Using default expected schema version.",
                logger,
            )

        schema_name = get_schema_name(database_config)
        expected_schema_version, expected_schema_version_source = (
            get_expected_schema_version(tool_config, tool_config_path)
        )
        connection_info = build_connection_info(database_config)

        logger.info("Using database config: %s", database_config_path)
        logger.info("Checking schema: %s", schema_name)
        logger.info("Expected schema version: %s", expected_schema_version)
        logger.info(
            "Expected schema version source: %s",
            expected_schema_version_source,
        )

        with psycopg.connect(**connection_info) as conn:
            check_connection(conn, logger)
            check_extensions(conn, failures, logger)
            check_postgis_version(conn, warnings, logger)
            check_schema_metadata(conn, expected_schema_version, failures, logger)
            check_tables(conn, schema_name, failures, logger)
            check_columns(conn, schema_name, failures, logger)
            check_indexes(conn, schema_name, failures, logger)
            check_constraints(conn, schema_name, failures, logger)
            check_set_updated_at_function(conn, schema_name, failures, logger)
            check_triggers(conn, schema_name, failures, logger)

    except Exception as error:
        record_failure(
            failures,
            f"Database readiness check could not complete: {error}",
            logger,
        )

    print_summary(failures, warnings)

    report_path = write_check_report(project_root, logger)
    print(f"\nCSV readiness report written:\n  {report_path}")

    if failures:
        logger.error("Database readiness check failed.")
        sys.exit(1)

    logger.info("Database readiness check completed successfully.")
    print("\nDatabase readiness check completed successfully.")
    print("Next recommended step:")
    print("  python terrain_tool.py")


if __name__ == "__main__":
    main()