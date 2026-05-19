# -*- coding: utf-8 -*-
"""
terrain_tool.py

GEOG670 terrain packaging workflow tool.

Current implementation scope:
    - Shared script skeleton
    - Database/config/logging helpers
    - Lightweight database readiness check
    - Mode 1, first branch only:
        Register one external raster file as source_storage_mode = 'external_file'
    - Mode 2, SHP and Geopackage only

Not yet implemented:
    - Mode 1 multi-file registration
    - Mode 1 virtual_mosaic registration / VRT creation
    - Mode 1 postgis_raster payload loading
    - Mode 2 AOI registration for: GeoJSON, KML, Manual bounding box coordinates,
        Source raster extent (derived from a registered `source_dataset_id`)
    - Mode 3 terrain package operations

Revision history:
    2026-05-12:
        Initial terrain_tool.py implementation for Mode 1 single-file
        external raster registration. Uses source_raster_datasets and
        source_raster_files. Assumes database schema version 0.1.1.

    2026-05-12:
        Revision 0.1.1. 
        Added CrsMetadata dataclass so get_crs_metadata() returns named
        CRS fields instead of a positional tuple. Renamed the local CRS
        warning list inside get_crs_metadata() to crs_warnings for
        clarity.
        
    2026-05-14
        Revision 0.1.2 
        Multiple changes to function register_single_external_file()
        based on initial testing. Added import re and checks to ensure
        source_dataset_id and source_name are checked more robustly 
        on initial entry. Added further explanation for user in some
        sections that were ambiguous, such as prompt to choose, which
        now prompts to choose number. Repeats some selections back to
        user.
        Other major change was to open the main connection with autocommit
        enabled, while still using explicit transactions for writes.
        Otherwise, after writing new entry to database, user must quit
        the terrain_tool script before they can actually see it in the database
        such as with pgadmin. autocommit ensures that SELECT readiness checks
        do not leave an implicit outer transaction open which would then
        remain open after the entire operation was complete.
        
    2026-05-15
        Revision 0.2.0
        Added basic mode 2 functionality with SHP and Geopackage. Reorganized
        initial table checking to better reflect dependencies and be more human
        readable, and also permit usage of some tools if there are missing tables
        so long as the tables needed for that tool are present.
        Reorganized metadata and CRS pulling, renamed get_crs_metadata() to 
        get_raster_crs_metadata().
        Added logging for mode 2.
        
    2026-05-15
        Revision 0.2.1
        Changed AOI SQL command to cast geometry-text placeholders explicitly 
        as text due to error "could not determine data type of parameter $13"
        
    2026-05-17
        Revision 0.3.0
        Added basic Mode 3A functionality to generate manifest-rule.json and 
        tile_grid_plan.gpkg.
        

Recommended use from the project root:
    python terrain_tool.py
"""

from __future__ import annotations

#Added with initial implementation of Mode 1A: register single raster file
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import logging
import os
import sys
import re #import regex for python, regular expression

#Added with initial implementation of Mode 2A: register AOI from SHP file
import geopandas as gpd #standard abbreviation for geopandas is gpd
from shapely.ops import unary_union #we need to ensure we get unary_union, 
#and simply importing all of shapely might not do that
from shapely.geometry import MultiPolygon, Polygon
#from shapely import make_valid


#Added with initial implementation of Mode 3A: create tile plan only
import math
import json
from typing import Any

#Added with initial implementation of Mode 1A: register single raster file
try:
    import yaml
except ImportError:
    print("Missing dependency: pyyaml")
    print("Install with: pip install pyyaml")
    sys.exit(1)

#Added with initial implementation of Mode 1A: register single raster file
#however, import Jsonb was not needed until initial implementation of Mode 3A
try:
    import psycopg
    from psycopg import sql
    from psycopg.types.json import Jsonb
except ImportError:
    print("Missing dependency: psycopg")
    print("Install with: pip install psycopg")
    sys.exit(1)

#Added with initial implementation of Mode 1A: register single raster file
try:
    import rasterio
except ImportError:
    print("Missing dependency: rasterio")
    print("Install with: conda install -c conda-forge rasterio")
    sys.exit(1)

#Added with initial implementation of Mode 1A: register single raster file
try:
    from pyproj import CRS as PyprojCRS
except ImportError:
    print("Missing dependency: pyproj")
    print("Install with: conda install -c conda-forge pyproj")
    sys.exit(1)


TERRAIN_TOOL_SCRIPT_VERSION = "0.3.0"
EXPECTED_SCHEMA_VERSION_FALLBACK = "0.1.1"

REQUIRED_BASE_TABLES = [
    "terrain_schema_metadata",
]

REQUIRED_MODE1_TABLES = [
    "source_raster_datasets",
    "source_raster_files",
]
REQUIRED_MODE2_TABLES = [
    "aoi_definitions"
]

REQUIRED_MODE3A_TABLES = [
    "terrain_tile_runs",
    "terrain_tile_grid_plan",
]

REQUIRED_FOR_MODE1 = (
    REQUIRED_BASE_TABLES
    + REQUIRED_MODE1_TABLES
)

REQUIRED_FOR_MODE2 = (
    REQUIRED_BASE_TABLES
    + REQUIRED_MODE2_TABLES
)

REQUIRED_FOR_MODE2_WITH_SOURCE_LOOKUP = (
    REQUIRED_BASE_TABLES
    + REQUIRED_MODE1_TABLES
    + REQUIRED_MODE2_TABLES
)

REQUIRED_MODE3A_TABLES = [
    "terrain_tile_runs",
    "terrain_tile_grid_plan",
]

REQUIRED_FOR_MODE3A = (
    REQUIRED_BASE_TABLES
    + REQUIRED_MODE1_TABLES
    + REQUIRED_MODE2_TABLES
    + REQUIRED_MODE3A_TABLES
)

SOURCE_STORAGE_MODE_EXTERNAL_FILE = "external_file"
PATH_STORAGE_MODE_ROOT_PLUS_RELATIVE = "root_plus_relative"
AOI_SOURCE_TYPE_SHAPEFILE = "shapefile"


#Added with initial implementation of Mode 3A: create tile plan only
#operation constants for Mode 3.  The SUFFIXES one is important
#for generating session IDs that properly distinguish between operation_type,
#which is a field in the table "terrain_tile_runs".
MODE3_OPERATION_CREATE_TILE_PLAN_ONLY = "create_tile_plan_only"
MODE3_OPERATION_SESSION_SUFFIXES = {
    MODE3_OPERATION_CREATE_TILE_PLAN_ONLY: "plan",
}

#Added with initial implementation of Mode 3A: create tile plan only
#for the first implementation, these two profile IDs resolve to:
#unity_arcgis_maps_sdk:
#  target_engine = unity
#  target_geospatial_runtime = arcgis_maps_sdk_for_unity
#
#unity_cesium:
#  target_engine = unity
#  target_geospatial_runtime = cesium_for_unity
#
#Later, constants for Unreal or other runtimes can be added as needed
RUNTIME_PROFILE_UNITY_ARCGIS = "unity_arcgis_maps_sdk"
RUNTIME_PROFILE_UNITY_CESIUM = "unity_cesium"


#Added with initial implementation of Mode 3A: create tile plan only
#tile-size strategy constants
#Purpose:
#Use the same tile-size strategy values in:
#  tool_config.yaml
#  config validation
#  Mode 3A tile-size computation
#  confirmation summaries
#  terrain_tile_runs.run_metadata_json or sampling_model_json
#  manifest-rule.json

#heightmap_resolution + target_sample_spacing determine tile size
#
#Example:
#  heightmap_resolution = 1025
#  target_sample_spacing = 1.0 m
#  terrain_intervals = 1024
#  tile_size = 1024 m
TILE_SIZE_STRATEGY_DERIVE_FROM_HEIGHTMAP_AND_SPACING = (
    "derive_from_heightmap_resolution_and_target_sample_spacing"
)

#heightmap_resolution + explicit tile size determine target sample spacing
#
#Example:
#  heightmap_resolution = 1025
#  explicit_tile_size = 1000 m
#  terrain_intervals = 1024
#  target_sample_spacing = 1000 / 1024
TILE_SIZE_STRATEGY_EXPLICIT_TILE_SIZE = "explicit_tile_size_meters"

#Added with initial implementation of Mode 3A: create tile plan only
#sampling relationship constants.
#conservative_oversampling is equivalent to upsampling in sampling-density 
#terms, but the label is used here to make clear that no additional measured 
#terrain detail is being claimed.
SAMPLING_RELATIONSHIP_SOURCE_RESOLUTION_MATCH = "source_resolution_match"
SAMPLING_RELATIONSHIP_CONSERVATIVE_OVERSAMPLING = "conservative_oversampling"
SAMPLING_RELATIONSHIP_DOWNSAMPLING = "downsampling"
SAMPLING_SEVERITY_NONE = "none"
SAMPLING_SEVERITY_SLIGHT = "slight"
SAMPLING_SEVERITY_MODERATE = "moderate"
SAMPLING_SEVERITY_STRONG = "strong"

#Added with initial implementation of Mode 3A: create tile plan only
#grid policy constants for Mode 3
GRID_ANCHOR_POLICY_SNAP_TO_SOURCE = "snap_to_source_raster_grid"
GRID_ANCHOR_POLICY_AOI_SOUTHWEST = "anchor_to_aoi_southwest"

SNAP_REFERENCE_SOURCE_CELL_EDGES = "source_raster_cell_edges"

EDGE_POLICY_CEIL_TO_FULL_TILES = "ceil_to_full_tiles"

#Added with initial implementation of Mode 3A: create tile plan only
#tile-grid convention constants for Mode 3
GRID_ORIGIN_CORNER_SOUTHWEST = "southwest"
TILE_ANCHOR_CORNER_SOUTHWEST = "southwest"

ROW_INCREASES_TOWARD_NORTH = "north"
COL_INCREASES_TOWARD_EAST = "east"

TILE_TRAVERSAL_ROW_MAJOR_SW_TO_NE = "row_major_west_to_east_south_to_north"

#Added with initial implementation of Mode 1A: register single raster file
#This uses regex to define a pattern which specifies the following:
#- must start with a lowercase letter
#- must contain lowercase letters, numbers, underscores, and hyphens
#- must be 3 to 80 characters long
STABLE_IDENTIFIER_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{2,79}$")

#Added with initial implementation of Mode 1A: register single raster file
@dataclass
class AppConfig:
    project_root: Path
    database_config_path: Path
    tool_config_path: Path | None
    database_config: dict[str, Any]
    tool_config: dict[str, Any] | None
    schema_name: str
    expected_schema_version: str
    expected_schema_version_source: str
    logs_root: Path

#Added with initial implementation of Mode 1A: register single raster file
@dataclass
class RasterMetadata:
    path: Path
    filename: str
    source_root_path: Path
    relative_path: Path
    primary_source_path: Path
    file_size_bytes: int
    file_modified_time_utc: datetime
    file_sha256: str | None
    crs_authority: str | None
    crs_wkid: int | None
    crs_label: str | None
    linear_unit: str | None
    cell_size_x: float
    cell_size_y: float
    cell_size_unit: str | None
    nodata_value: float | None
    width_pixels: int
    height_pixels: int
    band_count: int
    dtype: str
    xmin: float
    ymin: float
    xmax: float
    ymax: float
    warnings: list[str]

#Added with first revision of Mode 1A: register single raster file
@dataclass
class CrsMetadata:
    authority: str | None
    wkid: int | None
    label: str | None
    linear_unit: str | None
    warnings: list[str]

#Added with initial implementation of Mode 2A: register AOI from SHP file
@dataclass
class AoiMetadata:
    source_file_path: Path
    source_layer_name: str | None

    source_crs_authority: str | None
    source_crs_wkid: int | None
    source_crs_label: str | None

    working_crs_authority: str | None
    working_crs_wkid: int | None
    working_crs_label: str | None

    geom_original_wkt: str | None
    geom_wkt: str

    was_reprojected: bool
    reprojection_note: str | None
    transformation_metadata_json: dict[str, Any]

    area_square_meters: float | None
    bbox_xmin: float
    bbox_ymin: float
    bbox_xmax: float
    bbox_ymax: float
    centroid_x: float
    centroid_y: float

    warnings: list[str]

#Added with initial implementation of Mode 3A: create tile plan only
#These may seem redundant at first given that they mirror
#some earlier mode dataclasses, but that is important for separating categories
#to better troubleshoot or debug, as mode 3 can get complex quickly
@dataclass
class Mode3SourceDataset:
    source_dataset_id: str
    source_name: str
    source_type: str
    source_storage_mode: str

    source_crs_authority: str | None
    source_crs_wkid: int | None
    source_crs_label: str | None
    source_linear_unit: str | None

    source_cell_size_x: float
    source_cell_size_y: float
    source_cell_size_unit: str | None
    source_nodata_value: float | None

    source_xmin: float
    source_ymin: float
    source_xmax: float
    source_ymax: float

    source_root_path: str | None
    path_storage_mode: str | None
    primary_source_path: str | None

    file_count: int | None
    validation_status: str | None

#Added with initial implementation of Mode 3A: create tile plan only
@dataclass
class Mode3AoiDefinition:
    aoi_id: str
    aoi_name: str

    working_crs_authority: str | None
    working_crs_wkid: int | None
    working_crs_label: str | None

    bbox_xmin: float
    bbox_ymin: float
    bbox_xmax: float
    bbox_ymax: float

    area_square_meters: float | None
    validation_status: str | None

#Added with initial implementation of Mode 3A: create tile plan only
@dataclass
class Mode3ASettings:
    heightmap_resolution: int
    target_sample_spacing_meters: float
    tile_size_strategy: str
    explicit_tile_size_meters: float | None

    edge_policy: str

    grid_anchor_policy: str
    snap_reference: str
    snap_min_direction: str
    snap_max_direction: str
    aoi_enclosure_policy: str

    runtime_profile_id: str
    target_engine: str
    target_geospatial_runtime: str

    output_root_folder: Path | None

    generate_manifest_rule: bool
    generate_tile_catalog: bool
    export_tile_grid_geopackage: bool

    require_confirmation_for_unsnapped_grid: bool
    warn_when_grid_not_snapped_to_source: bool
    warn_when_target_spacing_exceeds_source_cell_size: bool
    note_when_target_spacing_is_finer_than_source_cell_size: bool

#Added with initial implementation of Mode 3A: create tile plan only
@dataclass
class Mode3AComputedPlan:
    session_id: str

    terrain_intervals_per_side: int
    tile_size_meters: float
    target_sample_spacing_meters: float
    sampling_classification: str
    sampling_spacing_difference_meters: float
    sampling_spacing_percent_difference: float
    sampling_severity: str

    grid_xmin: float
    grid_ymin: float
    grid_xmax: float
    grid_ymax: float

    rows: int
    cols: int
    tile_count: int

    working_crs_wkid: int
    working_crs_label: str

    warnings: list[str]

# ---------------------------------------------------------------------
# Project, config, and logging helpers
# ---------------------------------------------------------------------


def get_project_root() -> Path:
    """
    Return the project root.

    terrain_tool.py is expected to live directly in the project root.
    """
    return Path(__file__).resolve().parent


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


def read_yaml_file(path: Path) -> dict[str, Any]:
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


def get_schema_name(database_config: dict[str, Any]) -> str:
    """
    Return the configured PostgreSQL schema name.
    """
    schema_section = database_config.get("schema", {})
    return schema_section.get("name", "public")


def get_expected_schema_version(
    tool_config: dict[str, Any] | None,
    tool_config_path: Path | None,
) -> tuple[str, str]:
    """
    Return expected database schema version and a description of its source.
    """
    if tool_config is None:
        return (
            EXPECTED_SCHEMA_VERSION_FALLBACK,
            "internal fallback EXPECTED_SCHEMA_VERSION_FALLBACK; tool_config.yaml not found",
        )

    defaults_section = tool_config.get("defaults", {})

    if "expected_database_schema_version" in defaults_section:
        return (
            str(defaults_section["expected_database_schema_version"]),
            f"{tool_config_path} defaults.expected_database_schema_version",
        )

    return (
        EXPECTED_SCHEMA_VERSION_FALLBACK,
        "internal fallback EXPECTED_SCHEMA_VERSION_FALLBACK; "
        "tool_config lacks defaults.expected_database_schema_version",
    )


def get_logs_root(project_root: Path, tool_config: dict[str, Any] | None) -> Path:
    """
    Return the logs root from tool_config.yaml, defaulting to project_root/logs.
    """
    if tool_config is None:
        return project_root / "logs"

    paths_section = tool_config.get("paths", {})
    logs_root_value = paths_section.get("logs_root", "logs")
    logs_root_path = Path(logs_root_value)

    if logs_root_path.is_absolute():
        return logs_root_path

    return project_root / logs_root_path


def load_app_config() -> AppConfig:
    """
    Load database_config.yaml and optional tool_config.yaml.
    """
    project_root = get_project_root()

    database_config_path = find_config_file(project_root, "database_config")
    database_config = read_yaml_file(database_config_path)

    try:
        tool_config_path = find_config_file(project_root, "tool_config")
        tool_config = read_yaml_file(tool_config_path)
    except FileNotFoundError:
        tool_config_path = None
        tool_config = None

    schema_name = get_schema_name(database_config)
    expected_version, expected_version_source = get_expected_schema_version(
        tool_config,
        tool_config_path,
    )
    logs_root = get_logs_root(project_root, tool_config)

    return AppConfig(
        project_root=project_root,
        database_config_path=database_config_path,
        tool_config_path=tool_config_path,
        database_config=database_config,
        tool_config=tool_config,
        schema_name=schema_name,
        expected_schema_version=expected_version,
        expected_schema_version_source=expected_version_source,
        logs_root=logs_root,
    )

#This function sets up the script’s logging system.
#It creates loggers that can write messages both to the console and to log files.
#each logging.Logger is a separate log channel
def configure_logging(app_config: AppConfig
) -> tuple[
    logging.Logger, 
    logging.Logger, 
    logging.Logger,
    logging.Logger
    ]:
    """
    Configure general, Mode 1, Mode 2, and Mode 3 loggers.
    """
    #create log folder and parents if needed, but do not error if not needed
    app_config.logs_root.mkdir(parents=True, exist_ok=True)

    #check tool_config.yaml for logging level, defaulting to INFO if not found
    log_level_name = "INFO"
    if app_config.tool_config is not None:
        log_level_name = str(
            app_config.tool_config.get("logging", {}).get("level", "INFO")
        ).upper()

    #convert text "INFO" into python's logging constant: logging.INFO
    log_level = getattr(logging, log_level_name, logging.INFO)

    #define log message format
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )

    #create logger "terrain_tool" and clear old handlers to avoid repeated messages
    general_logger = logging.getLogger("terrain_tool")
    general_logger.setLevel(log_level)
    general_logger.handlers.clear()

    #create console handler so that general_logger prints messages to console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    general_logger.addHandler(console_handler)

    #create file handler to that general logger writes to logs\terrain_tool.log
    general_log_path = app_config.logs_root / "terrain_tool.log"
    general_file_handler = logging.FileHandler(general_log_path, encoding="utf-8")
    general_file_handler.setFormatter(formatter)
    general_logger.addHandler(general_file_handler)

    #create Mode 1 logger.  'propagate = False' prevents duplication of
    #Mode 1 log messages in general_logger
    mode1_logger = logging.getLogger("terrain_tool.mode1")
    mode1_logger.setLevel(log_level)
    mode1_logger.handlers.clear()
    mode1_logger.propagate = False

    mode1_console_handler = logging.StreamHandler()
    mode1_console_handler.setFormatter(formatter)
    mode1_logger.addHandler(mode1_console_handler)

    mode1_log_path = app_config.logs_root / "mode1_raster_registration.log"
    mode1_file_handler = logging.FileHandler(mode1_log_path, encoding="utf-8")
    mode1_file_handler.setFormatter(formatter)
    mode1_logger.addHandler(mode1_file_handler)

    mode2_logger = logging.getLogger("terrain_tool.mode2")
    mode2_logger.setLevel(log_level)
    mode2_logger.handlers.clear()
    mode2_logger.propagate = False

    mode2_console_handler = logging.StreamHandler()
    mode2_console_handler.setFormatter(formatter)
    mode2_logger.addHandler(mode2_console_handler)

    mode2_log_path = app_config.logs_root / "mode2_aoi_registration.log"
    mode2_file_handler = logging.FileHandler(mode2_log_path, encoding="utf-8")
    mode2_file_handler.setFormatter(formatter)
    mode2_logger.addHandler(mode2_file_handler)
    
    mode3_logger = logging.getLogger("terrain_tool.mode3")
    mode3_logger.setLevel(log_level)
    mode3_logger.handlers.clear()
    mode3_logger.propagate = False

    mode3_console_handler = logging.StreamHandler()
    mode3_console_handler.setFormatter(formatter)
    mode3_logger.addHandler(mode3_console_handler)

    mode3_log_path = app_config.logs_root / "mode3_terrain_package_operations.log"
    mode3_file_handler = logging.FileHandler(mode3_log_path, encoding="utf-8")
    mode3_file_handler.setFormatter(formatter)
    mode3_logger.addHandler(mode3_file_handler)

    return general_logger, mode1_logger, mode2_logger, mode3_logger


# ---------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------

#Part of initial build
def get_database_password(database_config: dict[str, Any]) -> str | None:
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

#Part of initial build
def build_connection_info(database_config: dict[str, Any]) -> dict[str, Any]:
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

    return {
        "host": database_section["host"],
        "port": int(database_section["port"]),
        "dbname": database_section["name"],
        "user": database_section["user"],
        "password": get_database_password(database_config),
        "connect_timeout": int(connection_section.get("connect_timeout_seconds", 10)),
        "application_name": f"{application_name}_terrain_tool",
    }

#Part of initial build
def qualified_table(schema_name: str, table_name: str) -> sql.Composed:
    """
    Return a safely quoted schema-qualified table identifier.
    """
    return sql.Identifier(schema_name, table_name)

#Part of initial build
def table_exists(conn: psycopg.Connection, schema_name: str, table_name: str) -> bool:
    """
    Check whether a table exists in the configured schema.
    """
    query = """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = %s
              AND table_name = %s
              AND table_type = 'BASE TABLE'
        );
    """
    with conn.cursor() as cur:
        cur.execute(query, (schema_name, table_name))
        return bool(cur.fetchone()[0])

#Part of initial build
def check_required_tables(
    conn: psycopg.Connection,
    schema_name: str,
    required_tables: list[str],
    context_label: str,
) -> None:
    """
    Check that required tables exist for a specific startup or mode context.
    """
    missing_tables = [
        table_name
        for table_name in required_tables
        if not table_exists(conn, schema_name, table_name)
    ]

    if missing_tables:
        missing_text = ", ".join(missing_tables)
        raise RuntimeError(
            f"Database schema is missing required tables for {context_label}: "
            f"{missing_text}\n\n"
            "Run:\n"
            "  python db/db_prepare.py\n"
            "  python db/db_check.py\n"
            "Then restart terrain_tool.py."
        )

#Part of initial build
def get_database_schema_version(
    conn: psycopg.Connection,
    schema_name: str,
) -> str | None:
    """
    Read schema_version from terrain_schema_metadata.
    """
    table = qualified_table(schema_name, "terrain_schema_metadata")
    query = sql.SQL(
        """
        SELECT metadata_value
        FROM {table}
        WHERE metadata_key = 'schema_version';
        """
    ).format(table=table)

    with conn.cursor() as cur:
        cur.execute(query)
        row = cur.fetchone()

    if row is None:
        return None

    return row[0]

#Part of initial build
def run_startup_readiness_check(
    conn: psycopg.Connection,
    app_config: AppConfig,
    logger: logging.Logger,
) -> None:
    """
    Perform startup readiness check for terrain_tool.py.

    This checks only database connection context, base schema metadata,
    and schema version. Mode-specific table checks happen when entering
    each mode.
    """
    logger.info("Running terrain_tool.py startup database readiness check.")
    logger.info("Checking schema: %s", app_config.schema_name)
    logger.info("Expected schema version: %s", app_config.expected_schema_version)
    logger.info(
        "Expected schema version source: %s",
        app_config.expected_schema_version_source,
    )

    check_required_tables(
        conn=conn,
        schema_name=app_config.schema_name,
        required_tables=REQUIRED_BASE_TABLES,
        context_label="terrain_tool.py startup",
    )

    actual_version = get_database_schema_version(conn, app_config.schema_name)

    if actual_version is None:
        raise RuntimeError(
            "terrain_schema_metadata exists, but schema_version is missing.\n\n"
            "Run:\n"
            "  python db/db_prepare.py\n"
            "  python db/db_check.py"
        )

    if actual_version != app_config.expected_schema_version:
        raise RuntimeError(
            "Database schema version mismatch.\n\n"
            f"Expected: {app_config.expected_schema_version}\n"
            f"Actual:   {actual_version}\n\n"
            "Run python db/db_check.py for a full report."
        )

    logger.info("Startup database readiness check passed.")

#Added with initial implementation of Mode 1A: register single raster file
#check if a source dataset ID being input at creation stage in Mode 1 already exists
def source_dataset_exists(
    conn: psycopg.Connection,
    schema_name: str,
    source_dataset_id: str,
) -> bool:
    """
    Return True if source_dataset_id already exists.
    """
    table = qualified_table(schema_name, "source_raster_datasets")
    query = sql.SQL(
        """
        SELECT EXISTS (
            SELECT 1
            FROM {table}
            WHERE source_dataset_id = %s
        );
        """
    ).format(table=table)

    with conn.cursor() as cur:
        cur.execute(query, (source_dataset_id,))
        return bool(cur.fetchone()[0])

#Added with initial implementation of Mode 1A: register single raster file
#check if a source dataset name being input at creation stage in Mode 1 already exists
def source_name_exists(
    conn: psycopg.Connection,
    schema_name: str,
    source_name: str,
) -> bool:
    """
    Return True if a source dataset display name already exists.

    This is only used for a human-facing warning. Duplicate source_name
    values are allowed. The unique database key is source_dataset_id.
    """
    table = qualified_table(schema_name, "source_raster_datasets")
    query = sql.SQL(
        """
        SELECT EXISTS (
            SELECT 1
            FROM {table}
            WHERE lower(btrim(source_name)) = lower(btrim(%s))
        );
        """
    ).format(table=table)

    with conn.cursor() as cur:
        cur.execute(query, (source_name,))
        return bool(cur.fetchone()[0])

#Added with initial implementation of Mode 2A: register AOI from SHP file
#check if an AOI ID being input at creation stage in Mode 2 already exists
def aoi_exists(
    conn: psycopg.Connection,
    schema_name: str,
    aoi_id: str,
) -> bool:
    """
    Return True if aoi_id already exists.
    """
    table = qualified_table(schema_name, "aoi_definitions")
    query = sql.SQL(
        """
        SELECT EXISTS (
            SELECT 1
            FROM {table}
            WHERE aoi_id = %s
        );
        """
    ).format(table=table)

    with conn.cursor() as cur:
        cur.execute(query, (aoi_id,))
        return bool(cur.fetchone()[0])

#Added with initial implementation of Mode 2A: register AOI from SHP file
#check if an AOI name being input at creation stage in Mode 2 already exists
def aoi_name_exists(
    conn: psycopg.Connection,
    schema_name: str,
    aoi_name: str,
) -> bool:
    """
    Return True if an AOI display name already exists.

    This is only used for a human-facing warning. Duplicate aoi_name
    values are allowed. The unique database key is aoi_id.
    """
    table = qualified_table(schema_name, "aoi_definitions")
    query = sql.SQL(
        """
        SELECT EXISTS (
            SELECT 1
            FROM {table}
            WHERE lower(btrim(aoi_name)) = lower(btrim(%s))
        );
        """
    ).format(table=table)

    with conn.cursor() as cur:
        cur.execute(query, (aoi_name,))
        return bool(cur.fetchone()[0])

#Added with initial implementation of Mode 2A: register AOI from SHP file
#this pulls the registered source CRS from a raster in case an AOI needs to be
#transformed or reprojected to use it as the working CRS
def get_registered_source_dataset_crs(
    conn: psycopg.Connection,
    schema_name: str,
    source_dataset_id: str,
) -> CrsMetadata | None:
    """
    Return CRS metadata for a registered source raster dataset.

    Used when Mode 2 should transform an AOI into the same working CRS
    as a registered source dataset.
    """
    table = qualified_table(schema_name, "source_raster_datasets")
    query = sql.SQL(
        """
        SELECT
            source_crs_authority,
            source_crs_wkid,
            source_crs_label,
            source_linear_unit
        FROM {table}
        WHERE source_dataset_id = %s;
        """
    ).format(table=table)

    with conn.cursor() as cur:
        cur.execute(query, (source_dataset_id,))
        row = cur.fetchone()

    if row is None:
        return None

    authority, wkid, label, linear_unit = row

    return CrsMetadata(
        authority=authority,
        wkid=wkid,
        label=label,
        linear_unit=linear_unit,
        warnings=[],
    )

#Added with initial implementation of Mode 1A: register single raster file
#modified during Mode 3A test to present user with Source ID rather than 
#just ID
def list_source_datasets(
    conn: psycopg.Connection,
    schema_name: str,
) -> None:
    """
    Print a simple list of registered source datasets.
    """
    table = qualified_table(schema_name, "source_raster_datasets")
    query = sql.SQL(
        """
        SELECT
            source_dataset_id,
            source_name,
            source_type,
            source_storage_mode,
            source_crs_label,
            file_count,
            validation_status,
            created_at
        FROM {table}
        ORDER BY created_at DESC, source_dataset_id;
        """
    ).format(table=table)

    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()

    if not rows:
        print("\nNo source raster datasets are currently registered.\n")
        return

    print("\nRegistered source raster datasets:")
    print("-" * 96)
    for row in rows:
        (
            dataset_id,
            name,
            source_type,
            storage_mode,
            crs_label,
            file_count,
            validation_status,
            created_at,
        ) = row
        print(f"\nSource ID:  {dataset_id}\n")
        print(f"Name:       {name}")
        print(f"Type:       {source_type}")
        print(f"Storage:    {storage_mode}")
        print(f"CRS:        {crs_label}")
        print(f"Files:      {file_count}")
        print(f"Validation: {validation_status}")
        print(f"Created:    {created_at}")
        print("-" * 96)

#Added with initial implementation of Mode 2A: register AOI from SHP file
#modified during Mode 3A test to present user with AOI ID rather than just ID
def list_aoi_definitions(
    conn: psycopg.Connection,
    schema_name: str,
) -> None:
    """
    Print a simple list of registered AOI definitions.
    """
    table = qualified_table(schema_name, "aoi_definitions")
    query = sql.SQL(
        """
        SELECT
            aoi_id,
            aoi_name,
            aoi_source_type,
            working_crs_label,
            area_square_meters,
            validation_status,
            created_at
        FROM {table}
        ORDER BY created_at DESC, aoi_id;
        """
    ).format(table=table)

    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()

    if not rows:
        print("\nNo AOI definitions are currently registered.\n")
        return

    print("\nRegistered AOI definitions:")
    print("-" * 96)
    for row in rows:
        (
            aoi_id,
            name,
            source_type,
            working_crs_label,
            area_square_meters,
            validation_status,
            created_at,
        ) = row

        print(f"\nAOI ID:      {aoi_id}\n")
        print(f"Name:        {name}")
        print(f"Source type: {source_type}")
        print(f"Working CRS: {working_crs_label}")
        print(f"Area m²:     {area_square_meters}")
        print(f"Validation:  {validation_status}")
        print(f"Created:     {created_at}")
        print("-" * 96)

#Added with initial implementation of Mode 3A: create tile plan only
#this is a coercion helper to catch missing or malformed values early
def require_float(
    value: Any,
    field_name: str,
    record_label: str,
) -> float:
    """
    Convert a required numeric database value to float.

    Raises a clear error if the database value is missing.
    """
    if value is None:
        raise ValueError(
            f"{record_label} is missing required numeric field: {field_name}"
        )

    return float(value)

#Added with initial implementation of Mode 3A: create tile plan only
#this is a coercion helper to catch missing or malformed values early
def optional_float(value: Any) -> float | None:
    """
    Convert an optional numeric database value to float.
    """
    if value is None:
        return None

    return float(value)

#Added with initial implementation of Mode 3A: create tile plan only
#this is to prevent accidental reuse of a run_id. Not unlike the helpers 
#to prevent reuse of a source_dataset_id (Mode 1) or aoi_id (Mode 2).
def run_id_exists(
    conn: psycopg.Connection,
    schema_name: str,
    run_id: str,
) -> bool:
    """
    Return True if run_id already exists in terrain_tile_runs.

    Mode 3A uses run_id as a human-facing run label. For this first
    implementation, require it to be unique so the audit trail remains clear.
    """
    table = qualified_table(schema_name, "terrain_tile_runs")
    query = sql.SQL(
        """
        SELECT EXISTS (
            SELECT 1
            FROM {table}
            WHERE run_id = %s
        );
        """
    ).format(table=table)

    with conn.cursor() as cur:
        cur.execute(query, (run_id,))
        return bool(cur.fetchone()[0])

#Added with initial implementation of Mode 3A: create tile plan only
#this is to prevent accidental reuse of a session_id. Unlike the other IDs, 
#session_id is generated by the system every time a session is run.  So this 
#checks computer, not human, input.
def session_id_exists(
    conn: psycopg.Connection,
    schema_name: str,
    session_id: str,
) -> bool:
    """
    Return True if session_id already exists in terrain_tile_runs.

    session_id is the durable operation/session key used to connect
    terrain_tile_runs to terrain_tile_grid_plan and later Mode 3 tables.
    """
    table = qualified_table(schema_name, "terrain_tile_runs")
    query = sql.SQL(
        """
        SELECT EXISTS (
            SELECT 1
            FROM {table}
            WHERE session_id = %s
        );
        """
    ).format(table=table)

    with conn.cursor() as cur:
        cur.execute(query, (session_id,))
        return bool(cur.fetchone()[0])

#Added with initial implementation of Mode 3A: create tile plan only
#This distinguishes between both timing and type of runs
def generate_available_mode3_session_id(
    conn: psycopg.Connection,
    schema_name: str,
    run_id: str,
    operation_type: str,
    max_attempts: int = 999,
) -> str:
    """
    Generate an available Mode 3 session_id from a run_id and operation_type.

    The operation_type is mapped to a short session suffix so the stored
    session_id remains readable without repeating the full operation string.

    Example for create_tile_plan_only:
        <run_id>_plan_001
        <run_id>_plan_002
        <run_id>_plan_003
    """
    if operation_type not in MODE3_OPERATION_SESSION_SUFFIXES:
        supported_operation_types = ", ".join(
            sorted(MODE3_OPERATION_SESSION_SUFFIXES)
        )
        raise ValueError(
            f"Unsupported Mode 3 operation_type for session_id generation: "
            f"{operation_type!r}. Supported operation types: "
            f"{supported_operation_types}"
        )

    session_suffix = MODE3_OPERATION_SESSION_SUFFIXES[operation_type]

    for index in range(1, max_attempts + 1):
        candidate_session_id = f"{run_id}_{session_suffix}_{index:03d}"

        if not session_id_exists(
            conn=conn,
            schema_name=schema_name,
            session_id=candidate_session_id,
        ):
            return candidate_session_id

    raise RuntimeError(
        f"Could not generate an available Mode 3 session_id for "
        f"run_id={run_id!r}, operation_type={operation_type!r} "
        f"after {max_attempts} attempts."
    )

#Added with initial implementation of Mode 3A: create tile plan only
#Some Mode 3 workflows will need stricter checks, but this is the base.
def read_mode3_source_dataset(
    conn: psycopg.Connection,
    schema_name: str,
    source_dataset_id: str,
) -> Mode3SourceDataset | None:
    """
    Read the selected source dataset metadata needed by Mode 3 workflows.

    Mode 3 workflows begin from registered source_dataset_id values, not
    arbitrary raster files. This helper reads dataset-level source facts from
    source_raster_datasets. Branches that need raster pixels perform additional
    source-file or raster-payload checks separately.
    """
    table = qualified_table(schema_name, "source_raster_datasets")
    query = sql.SQL(
        """
        SELECT
            source_dataset_id,
            source_name,
            source_type,
            source_storage_mode,

            source_crs_authority,
            source_crs_wkid,
            source_crs_label,
            source_linear_unit,

            source_cell_size_x,
            source_cell_size_y,
            source_cell_size_unit,
            source_nodata_value,

            source_xmin,
            source_ymin,
            source_xmax,
            source_ymax,

            source_root_path,
            path_storage_mode,
            primary_source_path,

            file_count,
            validation_status
        FROM {table}
        WHERE source_dataset_id = %s;
        """
    ).format(table=table)

    with conn.cursor() as cur:
        cur.execute(query, (source_dataset_id,))
        row = cur.fetchone()

    if row is None:
        return None

    (
        source_dataset_id,
        source_name,
        source_type,
        source_storage_mode,

        source_crs_authority,
        source_crs_wkid,
        source_crs_label,
        source_linear_unit,

        source_cell_size_x,
        source_cell_size_y,
        source_cell_size_unit,
        source_nodata_value,

        source_xmin,
        source_ymin,
        source_xmax,
        source_ymax,

        source_root_path,
        path_storage_mode,
        primary_source_path,

        file_count,
        validation_status,
    ) = row

    record_label = f"Source dataset {source_dataset_id!r}"

    return Mode3SourceDataset(
        source_dataset_id=source_dataset_id,
        source_name=source_name,
        source_type=source_type,
        source_storage_mode=source_storage_mode,

        source_crs_authority=source_crs_authority,
        source_crs_wkid=source_crs_wkid,
        source_crs_label=source_crs_label,
        source_linear_unit=source_linear_unit,

        source_cell_size_x=require_float(
            source_cell_size_x,
            "source_cell_size_x",
            record_label,
        ),
        source_cell_size_y=require_float(
            source_cell_size_y,
            "source_cell_size_y",
            record_label,
        ),
        source_cell_size_unit=source_cell_size_unit,
        source_nodata_value=optional_float(source_nodata_value),

        source_xmin=require_float(source_xmin, "source_xmin", record_label),
        source_ymin=require_float(source_ymin, "source_ymin", record_label),
        source_xmax=require_float(source_xmax, "source_xmax", record_label),
        source_ymax=require_float(source_ymax, "source_ymax", record_label),

        source_root_path=source_root_path,
        path_storage_mode=path_storage_mode,
        primary_source_path=primary_source_path,

        file_count=None if file_count is None else int(file_count),
        validation_status=validation_status,
    )

#Added with initial implementation of Mode 3A: create tile plan only
def read_mode3_aoi_definition(
    conn: psycopg.Connection,
    schema_name: str,
    aoi_id: str,
) -> Mode3AoiDefinition | None:
    """
    Read the selected AOI metadata needed by Mode 3 workflows.

    Mode 3 workflows begin from registered aoi_id values, not arbitrary AOI
    files. This helper reads AOI-level facts from aoi_definitions. Branches
    that need full geometry operations can use aoi_definitions.geom directly
    in PostGIS queries.
    """
    table = qualified_table(schema_name, "aoi_definitions")
    query = sql.SQL(
        """
        SELECT
            aoi_id,
            aoi_name,

            working_crs_authority,
            working_crs_wkid,
            working_crs_label,

            bbox_xmin,
            bbox_ymin,
            bbox_xmax,
            bbox_ymax,

            area_square_meters,
            validation_status
        FROM {table}
        WHERE aoi_id = %s;
        """
    ).format(table=table)

    with conn.cursor() as cur:
        cur.execute(query, (aoi_id,))
        row = cur.fetchone()

    if row is None:
        return None

    (
        aoi_id,
        aoi_name,

        working_crs_authority,
        working_crs_wkid,
        working_crs_label,

        bbox_xmin,
        bbox_ymin,
        bbox_xmax,
        bbox_ymax,

        area_square_meters,
        validation_status,
    ) = row

    record_label = f"AOI {aoi_id!r}"

    return Mode3AoiDefinition(
        aoi_id=aoi_id,
        aoi_name=aoi_name,

        working_crs_authority=working_crs_authority,
        working_crs_wkid=working_crs_wkid,
        working_crs_label=working_crs_label,

        bbox_xmin=require_float(bbox_xmin, "bbox_xmin", record_label),
        bbox_ymin=require_float(bbox_ymin, "bbox_ymin", record_label),
        bbox_xmax=require_float(bbox_xmax, "bbox_xmax", record_label),
        bbox_ymax=require_float(bbox_ymax, "bbox_ymax", record_label),

        area_square_meters=optional_float(area_square_meters),
        validation_status=validation_status,
    )

#Added with initial implementation of Mode 3A: create tile plan only
#For Mode 3A, partial overlap is not necessarily fatal because Mode 3A 
#is only planning. It can still say, “Here is the grid that would be needed 
#to cover this AOI.” But the warning is important because Mode 3B, 
#which actually builds raster tiles, should be stricter by default.
def extents_overlap_with_positive_area(
    xmin_a: float,
    ymin_a: float,
    xmax_a: float,
    ymax_a: float,
    xmin_b: float,
    ymin_b: float,
    xmax_b: float,
    ymax_b: float,
) -> bool:
    """
    Return True if two bounding boxes overlap with positive area.

    Boundary-only contact means the extents touch at an edge or corner
    but share zero area. That can matter for adjacency or seam checks,
    but it is not sufficient for Mode 3 terrain planning or source-
    coverage checks.
    """
    return not (
        xmax_a <= xmin_b
        or xmin_a >= xmax_b
        or ymax_a <= ymin_b
        or ymin_a >= ymax_b
    )

#Added with initial implementation of Mode 3A: create tile plan only
def extent_a_contains_extent_b(
    xmin_a: float,
    ymin_a: float,
    xmax_a: float,
    ymax_a: float,
    xmin_b: float,
    ymin_b: float,
    xmax_b: float,
    ymax_b: float,
) -> bool:
    """
    Return True if bounding box A fully contains bounding box B.
    """
    return (
        xmin_a <= xmin_b
        and ymin_a <= ymin_b
        and xmax_a >= xmax_b
        and ymax_a >= ymax_b
    )

#Added with initial implementation of Mode 3A: create tile plan only
#These checks may seem redundantly basic, since data is validated on entry
#in Modes 1 and 2.  However, the records created for those entries may have
#changed in some way since that time due to various factors, so it is wise
#to do a "trust but verify" set of checks here.
#Mode 3A checks are actually less strict than 3B and onwards, so they will
#have their own checking functions.
def check_mode3a_source_aoi_compatibility(
    source: Mode3SourceDataset,
    aoi: Mode3AoiDefinition,
) -> tuple[list[str], list[str]]:
    """
    Check whether the selected source dataset and AOI are compatible enough
    for Mode 3A tile planning.

    Returns:
        (fatal_errors, warnings)

    Fatal errors should stop Mode 3A.
    Warnings should be shown in the confirmation summary.

    First-pass rule:
        CRS mismatch is fatal. Mode 2 is where AOIs are normalized.
        Mode 3A should not silently reproject or reinterpret coordinates.
    """
    fatal_errors: list[str] = []
    warnings: list[str] = []

    # CRS checks.
    if source.source_crs_wkid is None:
        fatal_errors.append(
            f"Source dataset {source.source_dataset_id!r} has no source_crs_wkid."
        )

    if aoi.working_crs_wkid is None:
        fatal_errors.append(
            f"AOI {aoi.aoi_id!r} has no working_crs_wkid."
        )

    if (
        source.source_crs_wkid is not None
        and aoi.working_crs_wkid is not None
        and source.source_crs_wkid != aoi.working_crs_wkid
    ):
        fatal_errors.append(
            "Source CRS and AOI working CRS do not match. "
            f"Source CRS: {source.source_crs_label}; "
            f"AOI working CRS: {aoi.working_crs_label}. "
            "Mode 3A will not reproject AOI geometry. "
            "Re-register or transform the AOI in Mode 2."
        )

    # Source cell-size checks.
    if source.source_cell_size_x <= 0:
        fatal_errors.append(
            f"Source dataset {source.source_dataset_id!r} has invalid "
            f"source_cell_size_x={source.source_cell_size_x}."
        )

    if source.source_cell_size_y <= 0:
        fatal_errors.append(
            f"Source dataset {source.source_dataset_id!r} has invalid "
            f"source_cell_size_y={source.source_cell_size_y}."
        )

    if (
        source.source_cell_size_x > 0
        and source.source_cell_size_y > 0
        and abs(source.source_cell_size_x - source.source_cell_size_y) > 1e-9
    ):
        warnings.append(
            "Source cell size x and y differ. "
            f"x={source.source_cell_size_x}, y={source.source_cell_size_y}. "
            "Mode 3A can still plan a square terrain grid, but later raster realization "
            "will need deliberate resampling behavior."
        )

    # Source extent checks.
    if source.source_xmin >= source.source_xmax:
        fatal_errors.append(
            f"Source dataset {source.source_dataset_id!r} has invalid x extent: "
            f"xmin={source.source_xmin}, xmax={source.source_xmax}."
        )

    if source.source_ymin >= source.source_ymax:
        fatal_errors.append(
            f"Source dataset {source.source_dataset_id!r} has invalid y extent: "
            f"ymin={source.source_ymin}, ymax={source.source_ymax}."
        )

    # AOI bbox checks.
    if aoi.bbox_xmin >= aoi.bbox_xmax:
        fatal_errors.append(
            f"AOI {aoi.aoi_id!r} has invalid x bbox: "
            f"xmin={aoi.bbox_xmin}, xmax={aoi.bbox_xmax}."
        )

    if aoi.bbox_ymin >= aoi.bbox_ymax:
        fatal_errors.append(
            f"AOI {aoi.aoi_id!r} has invalid y bbox: "
            f"ymin={aoi.bbox_ymin}, ymax={aoi.bbox_ymax}."
        )

    # Only do spatial bbox relationship checks if extents are basically valid.
    if not fatal_errors:
        overlaps_source = extents_overlap_with_positive_area(
            xmin_a=source.source_xmin,
            ymin_a=source.source_ymin,
            xmax_a=source.source_xmax,
            ymax_a=source.source_ymax,
            xmin_b=aoi.bbox_xmin,
            ymin_b=aoi.bbox_ymin,
            xmax_b=aoi.bbox_xmax,
            ymax_b=aoi.bbox_ymax,
        )

        if not overlaps_source:
            fatal_errors.append(
                "AOI bbox does not overlap the selected source dataset extent "
                "with positive area."
            )
        else:
            aoi_fully_inside_source = extent_a_contains_extent_b(
                xmin_a=source.source_xmin,
                ymin_a=source.source_ymin,
                xmax_a=source.source_xmax,
                ymax_a=source.source_ymax,
                xmin_b=aoi.bbox_xmin,
                ymin_b=aoi.bbox_ymin,
                xmax_b=aoi.bbox_xmax,
                ymax_b=aoi.bbox_ymax,
            )

            if not aoi_fully_inside_source:
                warnings.append(
                    "AOI bbox extends partly outside the selected source dataset extent. "
                    "Mode 3A can create a plan, but later raster realization should fail "
                    "or require an explicit outside-source coverage policy."
                )

    # Existing registration validation statuses.
    if source.validation_status not in {None, "passed"}:
        warnings.append(
            f"Source dataset validation_status is {source.validation_status!r}."
        )

    if aoi.validation_status not in {None, "passed"}:
        warnings.append(
            f"AOI validation_status is {aoi.validation_status!r}."
        )

    return fatal_errors, warnings


# ---------------------------------------------------------------------
# Config interpretation helpers
# ---------------------------------------------------------------------
#this section added with initial implementation of 
#Mode 3A: create tile plan only

#Added with initial implementation of Mode 3A: create tile plan only
#added for Mode 3A but used in 3B and onward, therefore separate from overall
#helper load_mode3a_settings_from_config()
def resolve_mode3_runtime_profile(
    runtime_profile_id: str,
) -> tuple[str, str]:
    """
    Resolve a runtime profile ID into target engine/runtime labels.

    This keeps the first implementation simple. If runtime profiles become
    more complex later, this can be replaced by reading richer profile
    definitions from tool_config.yaml or a database table.
    """
    if runtime_profile_id == RUNTIME_PROFILE_UNITY_ARCGIS:
        return "unity", "arcgis_maps_sdk_for_unity"

    if runtime_profile_id == RUNTIME_PROFILE_UNITY_CESIUM:
        return "unity", "cesium_for_unity"

    raise ValueError(
        f"Unsupported runtime_profile_id: {runtime_profile_id!r}"
    )

#Added with initial implementation of Mode 3A: create tile plan only
def require_config_section(
    tool_config: dict[str, Any],
    section_name: str,
) -> dict[str, Any]:
    """
    Return a required top-level config section.

    Raises a clear error if the section is missing or not a dictionary.
    """
    section = tool_config.get(section_name)

    if not isinstance(section, dict):
        raise ValueError(
            f"tool_config.yaml is missing required section {section_name!r}, "
            "or that section is not a mapping."
        )

    return section

#Added with initial implementation of Mode 3A: create tile plan only
def require_config_value(
    section: dict[str, Any],
    key: str,
    section_name: str,
) -> Any:
    """
    Return a required config value from a section.

    Raises a clear error if the key is missing.
    """
    if key not in section:
        raise ValueError(
            f"tool_config.yaml section {section_name!r} is missing "
            f"required key {key!r}."
        )

    return section[key]

#Added with initial implementation of Mode 3A: create tile plan only
#main Mode 3A config loader
def load_mode3a_settings_from_config(
    app_config: AppConfig,
) -> Mode3ASettings:
    """
    Load initial Mode 3A settings from tool_config.yaml.

    This helper reads durable defaults from config and returns the resolved
    settings for a Mode 3A plan-only run. It does not prompt the user and
    does not compute tile rows, columns, or extents.

    Mode 3A enforces plan-only scope:
        - generate_tile_catalog is forced to False
        - RAW export is handled later as requested=False
        - derived raster storage is handled later as requested=False
    """
    mode3_config = require_config_section(
        tool_config=app_config.tool_config,
        section_name="mode3",
    )

    runtime_config = require_config_section(
        tool_config=app_config.tool_config,
        section_name="runtime_profiles",
    )

    heightmap_resolution = int(
        require_config_value(
            mode3_config,
            "default_heightmap_resolution",
            "mode3",
        )
    )

    target_sample_spacing_meters = float(
        require_config_value(
            mode3_config,
            "default_target_sample_spacing_meters",
            "mode3",
        )
    )

    tile_size_strategy = str(
        require_config_value(
            mode3_config,
            "default_tile_size_strategy",
            "mode3",
        )
    )

    explicit_tile_size_raw = mode3_config.get("default_tile_size_meters")
    explicit_tile_size_meters = (
        None
        if explicit_tile_size_raw is None
        else float(explicit_tile_size_raw)
    )

    edge_policy = str(
        require_config_value(
            mode3_config,
            "default_edge_policy",
            "mode3",
        )
    )

    grid_anchor_policy = str(
        require_config_value(
            mode3_config,
            "default_grid_anchor_policy",
            "mode3",
        )
    )

    snap_reference = str(
        require_config_value(
            mode3_config,
            "default_snap_reference",
            "mode3",
        )
    )

    snap_min_direction = str(
        require_config_value(
            mode3_config,
            "default_snap_min_direction",
            "mode3",
        )
    )

    snap_max_direction = str(
        require_config_value(
            mode3_config,
            "default_snap_max_direction",
            "mode3",
        )
    )

    aoi_enclosure_policy = str(
        require_config_value(
            mode3_config,
            "default_aoi_enclosure_policy",
            "mode3",
        )
    )

    runtime_profile_id = str(
        require_config_value(
            runtime_config,
            "default_profile_id",
            "runtime_profiles",
        )
    )

    target_engine, target_geospatial_runtime = resolve_mode3_runtime_profile(
        runtime_profile_id=runtime_profile_id,
    )

    output_root_raw = mode3_config.get("default_output_root_folder")
    output_root_folder = (
        None
        if output_root_raw in {None, ""}
        else Path(str(output_root_raw))
    )

    generate_manifest_rule = bool(
        mode3_config.get("default_generate_manifest_rule", True)
    )

    # Mode 3A is plan-only. Do not generate tile-catalog.json here,
    # even if a broader config default is accidentally set to true.
    generate_tile_catalog = False

    export_tile_grid_geopackage = bool(
        mode3_config.get("default_export_tile_grid_geopackage", True)
    )

    require_confirmation_for_unsnapped_grid = bool(
        mode3_config.get("require_confirmation_for_unsnapped_grid", True)
    )

    warn_when_grid_not_snapped_to_source = bool(
        mode3_config.get("warn_when_grid_not_snapped_to_source", True)
    )

    warn_when_target_spacing_exceeds_source_cell_size = bool(
        mode3_config.get(
            "warn_when_target_spacing_exceeds_source_cell_size",
            True,
        )
    )

    note_when_target_spacing_is_finer_than_source_cell_size = bool(
        mode3_config.get(
            "note_when_target_spacing_is_finer_than_source_cell_size",
            True,
        )
    )

    if heightmap_resolution <= 1:
        raise ValueError(
            "Mode 3A config error: default_heightmap_resolution must be "
            f"greater than 1, got {heightmap_resolution}."
        )

    if target_sample_spacing_meters <= 0:
        raise ValueError(
            "Mode 3A config error: default_target_sample_spacing_meters "
            f"must be positive, got {target_sample_spacing_meters}."
        )

    supported_tile_size_strategies = {
        TILE_SIZE_STRATEGY_DERIVE_FROM_HEIGHTMAP_AND_SPACING,
        TILE_SIZE_STRATEGY_EXPLICIT_TILE_SIZE,
    }

    if tile_size_strategy not in supported_tile_size_strategies:
        raise ValueError(
            "Mode 3A config error: unsupported default_tile_size_strategy "
            f"{tile_size_strategy!r}. Supported values: "
            f"{sorted(supported_tile_size_strategies)}"
        )

    if (
        tile_size_strategy == TILE_SIZE_STRATEGY_EXPLICIT_TILE_SIZE
        and (
            explicit_tile_size_meters is None
            or explicit_tile_size_meters <= 0
        )
    ):
        raise ValueError(
            "Mode 3A config error: default_tile_size_strategy is "
            f"{TILE_SIZE_STRATEGY_EXPLICIT_TILE_SIZE!r}, so "
            "default_tile_size_meters must be present and positive."
        )

    supported_grid_anchor_policies = {
        GRID_ANCHOR_POLICY_SNAP_TO_SOURCE,
        GRID_ANCHOR_POLICY_AOI_SOUTHWEST,
    }

    if grid_anchor_policy not in supported_grid_anchor_policies:
        raise ValueError(
            "Mode 3A config error: unsupported default_grid_anchor_policy "
            f"{grid_anchor_policy!r}. Supported values: "
            f"{sorted(supported_grid_anchor_policies)}"
        )

    if snap_reference != SNAP_REFERENCE_SOURCE_CELL_EDGES:
        raise ValueError(
            "Mode 3A config error: unsupported default_snap_reference "
            f"{snap_reference!r}. Supported value: "
            f"{SNAP_REFERENCE_SOURCE_CELL_EDGES!r}"
        )

    if edge_policy != EDGE_POLICY_CEIL_TO_FULL_TILES:
        raise ValueError(
            "Mode 3A config error: unsupported default_edge_policy "
            f"{edge_policy!r}. Supported value: "
            f"{EDGE_POLICY_CEIL_TO_FULL_TILES!r}"
        )

    return Mode3ASettings(
        heightmap_resolution=heightmap_resolution,
        target_sample_spacing_meters=target_sample_spacing_meters,
        tile_size_strategy=tile_size_strategy,
        explicit_tile_size_meters=explicit_tile_size_meters,

        edge_policy=edge_policy,

        grid_anchor_policy=grid_anchor_policy,
        snap_reference=snap_reference,
        snap_min_direction=snap_min_direction,
        snap_max_direction=snap_max_direction,
        aoi_enclosure_policy=aoi_enclosure_policy,

        runtime_profile_id=runtime_profile_id,
        target_engine=target_engine,
        target_geospatial_runtime=target_geospatial_runtime,

        output_root_folder=output_root_folder,

        generate_manifest_rule=generate_manifest_rule,
        generate_tile_catalog=generate_tile_catalog,
        export_tile_grid_geopackage=export_tile_grid_geopackage,

        require_confirmation_for_unsnapped_grid=(
            require_confirmation_for_unsnapped_grid
        ),
        warn_when_grid_not_snapped_to_source=(
            warn_when_grid_not_snapped_to_source
        ),
        warn_when_target_spacing_exceeds_source_cell_size=(
            warn_when_target_spacing_exceeds_source_cell_size
        ),
        note_when_target_spacing_is_finer_than_source_cell_size=(
            note_when_target_spacing_is_finer_than_source_cell_size
        ),
    )

# ---------------------------------------------------------------------
# Prompt helpers
# ---------------------------------------------------------------------

#added in initial build
def prompt_nonempty(prompt_text: str) -> str:
    """
    Prompt until the user enters non-empty text.
    """
    while True:
        value = input(prompt_text).strip()
        if value:
            return value
        print("Please enter a value.")

#added in initial build
def prompt_optional(prompt_text: str) -> str | None:
    """
    Prompt for optional text.
    """
    value = input(prompt_text).strip()
    if not value:
        return None
    return value

#added in initial build
def prompt_yes_no(prompt_text: str, default: bool | None = None) -> bool:
    """
    Prompt for yes/no.
    """
    if default is True:
        suffix = " [Y/n]: "
    elif default is False:
        suffix = " [y/N]: "
    else:
        suffix = " [y/n]: "

    while True:
        value = input(prompt_text + suffix).strip().lower()

        if not value and default is not None:
            return default

        if value in {"y", "yes"}:
            return True

        if value in {"n", "no"}:
            return False

        print("Please enter yes or no.")

#added in initial build
def prompt_choice(prompt_text: str, choices: list[tuple[str, str]]) -> str:
    """
    Prompt for a numbered choice.

    choices is a list of (key, label) tuples.
    Returns the selected key.
    """
    while True:
        print(f"\n{prompt_text}")
        for index, (_key, label) in enumerate(choices, start=1):
            print(f"  {index}. {label}")

        value = input("Choose an option number: ").strip()

        if not value.isdigit():
            print("Please enter a number from the list.")
            continue

        index = int(value)
        if 1 <= index <= len(choices):
            return choices[index - 1][0]

        print("Choice out of range.")

#added in initial build
def normalize_path_input(path_text: str) -> Path:
    """
    Normalize a path typed or pasted into the console.
    """
    cleaned = path_text.strip().strip('"').strip("'")
    return Path(cleaned).expanduser()

#added in initial build
def prompt_existing_file(prompt_text: str) -> Path:
    """
    Prompt until the user enters an existing file path.
    """
    while True:
        path = normalize_path_input(input(prompt_text).strip())

        if not path.exists():
            print(f"File does not exist: {path}")
            continue

        if not path.is_file():
            print(f"Path is not a file: {path}")
            continue

        return path.resolve(strict=True)

#Added with initial implementation of Mode 2A: register AOI from SHP file
def get_missing_shapefile_sidecars(shp_path: Path) -> list[Path]:
    """
    Return required shapefile sidecar paths that are missing.

    The user provides the .shp path, but a normal shapefile also needs
    matching .shx and .dbf files. For this workflow, .prj is also required
    because Mode 2 must know the AOI source CRS.
    """
    required_suffixes = [".shp", ".shx", ".dbf", ".prj"]

    missing_paths: list[Path] = []

    for suffix in required_suffixes:
        sidecar_path = shp_path.with_suffix(suffix)
        if not sidecar_path.exists():
            missing_paths.append(sidecar_path)

    return missing_paths

#Added with initial implementation of Mode 2A: register AOI from SHP file
def prompt_existing_shapefile(prompt_text: str) -> Path:
    """
    Prompt until the user enters an existing .shp path with required sidecars.

    Required:
        .shp
        .shx
        .dbf
        .prj

    The .prj file is required for this workflow because Mode 2 must know
    the AOI source CRS before it can store or transform the AOI safely.
    """
    while True:
        shp_path = prompt_existing_file(prompt_text)

        if shp_path.suffix.lower() != ".shp":
            print(
                f"\nThe selected file is not a .shp file: {shp_path}\n"
                "Please enter the path to the shapefile's .shp component.\n"
            )
            continue

        missing_paths = get_missing_shapefile_sidecars(shp_path)

        if missing_paths:
            print("\nThis shapefile is missing required sidecar files:")
            for missing_path in missing_paths:
                print(f"  - {missing_path}")

            print(
                "\nA shapefile normally requires matching .shp, .shx, and .dbf files.\n"
                "This workflow also requires a .prj file so the AOI CRS can be read safely.\n"
            )
            continue

        return shp_path

#Added with initial implementation of Mode 1A: register single raster file
def prompt_source_type() -> str:
    """
    Prompt for source elevation type.
    """
    choice = prompt_choice(
        "Source type",
        [
            ("DTM", "DTM - bare-earth digital terrain model"),
            ("DSM", "DSM - top-of-surface digital surface model"),
            ("DEM", "DEM - generic/unspecified digital elevation model"),
            ("bathymetry", "Bathymetry - underwater elevation/depth model"),
            ("other", "Other"),
        ],
    )

    if choice == "other":
        return prompt_nonempty("Enter source type label: ")

    return choice

#Added with initial implementation of Mode 3A: create tile plan only
def prompt_new_mode3_run_id(
    conn: psycopg.Connection,
    schema_name: str,
) -> str:
    """
    Prompt for a new Mode 3 run_id.

    run_id is a human-facing run label. For the first implementation,
    require it to be unique in terrain_tile_runs so the audit trail remains
    clear.
    """
    while True:
        run_id = prompt_nonempty(
            "Enter new Mode 3 run_id, for example pyp_test_001: "
        )

        if not STABLE_IDENTIFIER_PATTERN.match(run_id):
            print(
                "\nInvalid run_id.\n"
                "Use 3–80 characters. Start with a lowercase letter.\n"
                "Allowed characters: lowercase letters, numbers, underscores, hyphens.\n"
            )
            continue

        if run_id_exists(
            conn=conn,
            schema_name=schema_name,
            run_id=run_id,
        ):
            print(
                f"\nA Mode 3 run already exists with run_id={run_id!r}.\n"
                "Please choose a new run_id.\n"
            )
            continue

        return run_id

#Added with initial implementation of Mode 3A: create tile plan only
#Note that the user should not enter a raster path here. The point of this
#script and the database system is to provide them with a list from which to 
#select
def prompt_existing_source_dataset_id_for_mode3(
    conn: psycopg.Connection,
    schema_name: str,
) -> str:
    """
    Prompt for an existing source_dataset_id for Mode 3.

    Mode 3 uses registered source datasets. It does not ask for arbitrary
    raster files.
    """
    show_list = prompt_yes_no(
        "List registered source raster datasets?",
        default=True,
    )

    if show_list:
        list_source_datasets(conn, schema_name)

    #Modified during initial 3A testing to use human readable name as well as 
    #variable name
    while True:
        source_dataset_id = prompt_nonempty(
            "Enter Source ID (source_dataset_id) for this Mode 3 run: "
        )

        if not STABLE_IDENTIFIER_PATTERN.match(source_dataset_id):
            print(
                "\nInvalid source_dataset_id format.\n"
                "Use 3–80 characters. Start with a lowercase letter.\n"
                "Allowed characters: lowercase letters, numbers, underscores, hyphens.\n"
            )
            continue

        if not source_dataset_exists(
            conn=conn,
            schema_name=schema_name,
            source_dataset_id=source_dataset_id,
        ):
            print(
                f"\nNo registered source dataset found with "
                f"source_dataset_id={source_dataset_id!r}.\n"
            )

            show_list_again = prompt_yes_no(
                "List registered source raster datasets again?",
                default=True,
            )
            if show_list_again:
                list_source_datasets(conn, schema_name)

            continue

        return source_dataset_id

#Added with initial implementation of Mode 3A: create tile plan only
#As above, the user should not need to enter a path here. The point of this
#script and the database system is to provide them with a list from which to 
#select
def prompt_existing_aoi_id_for_mode3(
    conn: psycopg.Connection,
    schema_name: str,
) -> str:
    """
    Prompt for an existing aoi_id for Mode 3.

    Mode 3 uses registered AOI definitions. It does not ask for arbitrary
    AOI files.
    """
    show_list = prompt_yes_no(
        "List registered AOI definitions?",
        default=True,
    )

    if show_list:
        list_aoi_definitions(conn, schema_name)

    #Modified during initial 3A testing to use human readable name as well as 
    #variable name
    while True:
        aoi_id = prompt_nonempty(
            "Enter AOI ID (aoi_id) for this Mode 3 run: "
        )

        if not STABLE_IDENTIFIER_PATTERN.match(aoi_id):
            print(
                "\nInvalid aoi_id format.\n"
                "Use 3–80 characters. Start with a lowercase letter.\n"
                "Allowed characters: lowercase letters, numbers, underscores, hyphens.\n"
            )
            continue

        if not aoi_exists(
            conn=conn,
            schema_name=schema_name,
            aoi_id=aoi_id,
        ):
            print(
                f"\nNo registered AOI found with aoi_id={aoi_id!r}.\n"
            )

            show_list_again = prompt_yes_no(
                "List registered AOI definitions again?",
                default=True,
            )
            if show_list_again:
                list_aoi_definitions(conn, schema_name)

            continue

        return aoi_id

#Added with initial implementation of Mode 3A: create tile plan only
#Permits the user to change a subset of settings or proceed or cancel
def prompt_mode3a_summary_choice() -> str:
    """
    Prompt for the user's decision after the Mode 3A confirmation summary.

    Returns one of:
        accept
        sampling
        grid
        runtime
        outputs
        cancel
    """
    return prompt_choice(
        "Accept these Mode 3A settings?",
        [
            ("accept", "Accept and create tile plan"),
            ("sampling", "Change terrain sampling / tile size"),
            ("grid", "Change grid snapping / origin policy"),
            ("runtime", "Change runtime profile"),
            ("outputs", "Change output artifact settings"),
            ("cancel", "Cancel Mode 3A"),
        ],
    )


# ---------------------------------------------------------------------
# CRS metadata helpers
# ---------------------------------------------------------------------

#Added with initial implementation of Mode 1A: register single raster file
#Mode 1 raster registration method for pulling CRS
def get_raster_crs_metadata(rasterio_crs: rasterio.crs.CRS | None) -> CrsMetadata:
    """
    Convert rasterio CRS object into authority, WKID, label, linear unit, warnings.
    """
    crs_warnings: list[str] = []

    if rasterio_crs is None:
        return CrsMetadata(
            authority=None,
            wkid=None,
            label=None,
            linear_unit=None,
            warnings=["Raster has no CRS."],
        )

    authority: str | None = None
    wkid: int | None = None
    label: str | None = None
    linear_unit: str | None = None

    try:
        authority_tuple = rasterio_crs.to_authority()
    except Exception:
        authority_tuple = None

    if authority_tuple is not None:
        authority = authority_tuple[0]
        try:
            wkid = int(authority_tuple[1])
        except (TypeError, ValueError):
            wkid = None

    if authority is not None and wkid is not None:
        label = f"{authority}:{wkid}"
    else:
        label = rasterio_crs.to_string()
        crs_warnings.append(
            "Raster CRS did not resolve cleanly to an authority/WKID. "
            "Geometry will be stored with SRID 0 unless a later workflow supplies one."
        )

    try:
        pyproj_crs = PyprojCRS.from_wkt(rasterio_crs.to_wkt())
        if pyproj_crs.axis_info:
            linear_unit = pyproj_crs.axis_info[0].unit_name
    except Exception as error:
        crs_warnings.append(f"Could not read CRS unit from pyproj: {error}")

    if linear_unit is None:
        crs_warnings.append("Could not determine CRS linear/angular unit.")

    return CrsMetadata(
        authority=authority,
        wkid=wkid,
        label=label,
        linear_unit=linear_unit,
        warnings=crs_warnings,
    )

#Added with initial implementation of Mode 2A: register AOI from SHP file
#Mode 2 AOI registration method for pulling CRS
def get_vector_crs_metadata(vector_crs: Any) -> CrsMetadata:
    """
    Convert a GeoPandas / pyproj CRS value into authority, WKID, label,
    linear unit, and warnings.

    GeoPandas normally stores CRS information as a pyproj-compatible CRS
    object in gdf.crs. This helper normalizes that CRS into the same
    CrsMetadata dataclass used by raster CRS handling.
    """
    crs_warnings: list[str] = []

    if vector_crs is None:
        return CrsMetadata(
            authority=None,
            wkid=None,
            label=None,
            linear_unit=None,
            warnings=["Vector layer has no CRS."],
        )

    authority: str | None = None
    wkid: int | None = None
    label: str | None = None
    linear_unit: str | None = None

    try:
        pyproj_crs = PyprojCRS.from_user_input(vector_crs)
    except Exception as error:
        return CrsMetadata(
            authority=None,
            wkid=None,
            label=None,
            linear_unit=None,
            warnings=[f"Could not interpret vector CRS with pyproj: {error}"],
        )

    try:
        authority_tuple = pyproj_crs.to_authority()
    except Exception:
        authority_tuple = None

    if authority_tuple is not None:
        authority = authority_tuple[0]

        try:
            wkid = int(authority_tuple[1])
        except (TypeError, ValueError):
            wkid = None

    if authority is not None and wkid is not None:
        label = f"{authority}:{wkid}"
    else:
        label = pyproj_crs.to_string()
        crs_warnings.append(
            "Vector CRS did not resolve cleanly to an authority/WKID. "
            "Geometry will be stored with SRID 0 unless a working CRS is supplied."
        )

    try:
        if pyproj_crs.axis_info:
            linear_unit = pyproj_crs.axis_info[0].unit_name
    except Exception as error:
        crs_warnings.append(f"Could not read vector CRS unit from pyproj: {error}")

    if linear_unit is None:
        crs_warnings.append("Could not determine vector CRS linear/angular unit.")

    return CrsMetadata(
        authority=authority,
        wkid=wkid,
        label=label,
        linear_unit=linear_unit,
        warnings=crs_warnings,
    )


# ---------------------------------------------------------------------
# Raster metadata and checksum helpers
# ---------------------------------------------------------------------

#added with initial build
def compute_sha256(path: Path, chunk_size_bytes: int = 8 * 1024 * 1024) -> str:
    """
    Compute SHA-256 for a file using chunked reads.

    Chunking keeps memory use small even for large raster files. It does not
    avoid disk I/O; the whole file still has to be read.
    """
    sha256 = hashlib.sha256()

    with path.open("rb") as file:
        while True:
            chunk = file.read(chunk_size_bytes)
            if not chunk:
                break
            sha256.update(chunk)

    return sha256.hexdigest()

#Added with initial implementation of Mode 1A: register single raster file
def read_single_raster_metadata(
    raster_path: Path,
    compute_checksum: bool,
) -> RasterMetadata:
    """
    Read metadata for one raster file intended for external_file registration.
    """
    warnings: list[str] = []

    stat_info = raster_path.stat()
    file_size_bytes = stat_info.st_size
    file_modified_time_utc = datetime.fromtimestamp(
        stat_info.st_mtime,
        tz=timezone.utc,
    )

    source_root_path = raster_path.parent
    relative_path = Path(raster_path.name)
    primary_source_path = raster_path

    file_sha256 = None
    if compute_checksum:
        file_sha256 = compute_sha256(raster_path)

    with rasterio.open(raster_path) as src:
        raster_crs_metadata = get_raster_crs_metadata(src.crs)
        warnings.extend(raster_crs_metadata.warnings)

        transform = src.transform
        cell_size_x = abs(float(transform.a))
        cell_size_y = abs(float(transform.e))
        cell_size_unit = raster_crs_metadata.linear_unit

        if src.crs is None:
            warnings.append("Raster has no CRS. Registration should not proceed.")

        if (
            raster_crs_metadata.linear_unit is not None
            and raster_crs_metadata.linear_unit.lower() not in {"metre", "meter"}
        ):
            warnings.append(
                f"Raster CRS unit appears to be '{raster_crs_metadata.linear_unit}', not meter. "
                "This may be valid for source registration, but later terrain operations "
                "will need deliberate CRS/unit handling."
            )

        bounds = src.bounds
        nodata_value = None if src.nodata is None else float(src.nodata)

        metadata = RasterMetadata(
            path=raster_path,
            filename=raster_path.name,
            source_root_path=source_root_path,
            relative_path=relative_path,
            primary_source_path=primary_source_path,
            file_size_bytes=file_size_bytes,
            file_modified_time_utc=file_modified_time_utc,
            file_sha256=file_sha256,
            crs_authority=raster_crs_metadata.authority,
            crs_wkid=raster_crs_metadata.wkid,
            crs_label=raster_crs_metadata.label,
            linear_unit=raster_crs_metadata.linear_unit,
            cell_size_x=cell_size_x,
            cell_size_y=cell_size_y,
            cell_size_unit=cell_size_unit,
            nodata_value=nodata_value,
            width_pixels=int(src.width),
            height_pixels=int(src.height),
            band_count=int(src.count),
            dtype=str(src.dtypes[0]) if src.dtypes else "unknown",
            xmin=float(bounds.left),
            ymin=float(bounds.bottom),
            xmax=float(bounds.right),
            ymax=float(bounds.top),
            warnings=warnings,
        )

    return metadata

# ---------------------------------------------------------------------
# Vector / AOI metadata helpers
# ---------------------------------------------------------------------

#Added with initial implementation of Mode 2A: register AOI from SHP file
def read_shapefile_aoi_metadata(
    shapefile_path: Path,
    working_crs_input: Any | None,
) -> AoiMetadata:
    """
    Read, validate, normalize, and optionally reproject one shapefile AOI.

    Parameters:
        shapefile_path:
            Path to the .shp file. Required sidecars should already have been
            checked by prompt_existing_shapefile().

        working_crs_input:
            CRS to use for the normalized AOI geometry. This can be something
            pyproj understands, such as "EPSG:27700" or a pyproj CRS object.

            If None, the shapefile's source CRS is used as the working CRS.

    First-pass behavior:
        - Reject empty files.
        - Reject files with no readable CRS.
        - Reject non-polygon geometry.
        - Reject invalid geometry rather than repairing silently.
        - Combine multiple polygons into one AOI geometry.
        - Store original geometry WKT and working geometry WKT.
    """
    warnings: list[str] = []

    try:
        gdf = gpd.read_file(shapefile_path)
    except Exception as error:
        raise ValueError(f"Could not read shapefile with GeoPandas: {error}") from error

    if gdf.empty:
        raise ValueError("Shapefile contains no features.")

    if gdf.crs is None:
        raise ValueError(
            "Shapefile has no readable CRS. "
            "A .prj file is required, or the CRS must be supplied explicitly."
        )

    source_crs_metadata = get_vector_crs_metadata(gdf.crs)

    if source_crs_metadata.label is None:
        raise ValueError(
            "Shapefile CRS could not be interpreted well enough for AOI registration."
        )

    try:
        source_pyproj_crs = PyprojCRS.from_user_input(gdf.crs)
    except Exception as error:
        raise ValueError(f"Could not normalize shapefile CRS with pyproj: {error}") from error

    if working_crs_input is None:
        working_pyproj_crs = source_pyproj_crs
    else:
        try:
            working_pyproj_crs = PyprojCRS.from_user_input(working_crs_input)
        except Exception as error:
            raise ValueError(f"Could not interpret selected working CRS: {error}") from error

    working_crs_metadata = get_vector_crs_metadata(working_pyproj_crs)

    if working_crs_metadata.label is None:
        raise ValueError(
            "Working CRS could not be interpreted well enough for AOI registration."
        )

    # Ensure there is an active geometry column.
    try:
        geometry_series = gdf.geometry
    except Exception as error:
        raise ValueError(f"Shapefile has no usable geometry column: {error}") from error

    if geometry_series is None:
        raise ValueError("Shapefile has no geometry column.")

    # Drop null or empty geometries.
    nonempty_mask = geometry_series.notna() & ~geometry_series.is_empty
    dropped_count = int((~nonempty_mask).sum())

    if dropped_count > 0:
        warnings.append(
            f"Dropped {dropped_count} null or empty geometries before AOI normalization."
        )

    gdf = gdf.loc[nonempty_mask].copy()

    if gdf.empty:
        raise ValueError("Shapefile has no non-empty geometries after filtering.")

    # First pass: AOIs must be polygon or multipolygon only.
    geometry_types = set(gdf.geometry.geom_type.unique())
    allowed_geometry_types = {"Polygon", "MultiPolygon"}
    disallowed_geometry_types = sorted(geometry_types - allowed_geometry_types)

    if disallowed_geometry_types:
        raise ValueError(
            "AOI shapefile must contain only Polygon or MultiPolygon geometry. "
            f"Found disallowed geometry types: {', '.join(disallowed_geometry_types)}"
        )

    invalid_count = int((~gdf.geometry.is_valid).sum())

    if invalid_count > 0:
        raise ValueError(
            f"AOI shapefile contains {invalid_count} invalid geometries. "
            "First implementation rejects invalid geometry rather than repairing it silently."
        )

    # Combine all polygon features into one AOI geometry.
    try:
        source_geom = unary_union(list(gdf.geometry))
    except Exception as error:
        raise ValueError(f"Could not combine shapefile geometries into one AOI: {error}") from error

    if source_geom.is_empty:
        raise ValueError("Combined AOI geometry is empty.")

    if not isinstance(source_geom, (Polygon, MultiPolygon)):
        raise ValueError(
            "Combined AOI geometry is not Polygon or MultiPolygon. "
            f"Result type was: {source_geom.geom_type}"
        )

    if not source_geom.is_valid:
        raise ValueError(
            "Combined AOI geometry is invalid. "
            "First implementation rejects invalid geometry rather than repairing it silently."
        )

    geom_original_wkt = source_geom.wkt

    was_reprojected = not source_pyproj_crs.equals(working_pyproj_crs)

    if was_reprojected:
        try:
            working_gdf = gpd.GeoDataFrame(
                {"geometry": [source_geom]},
                geometry="geometry",
                crs=source_pyproj_crs,
            ).to_crs(working_pyproj_crs)
        except Exception as error:
            raise ValueError(f"Could not reproject AOI to working CRS: {error}") from error

        working_geom = working_gdf.geometry.iloc[0]
        reprojection_note = (
            f"AOI transformed from {source_crs_metadata.label} "
            f"to {working_crs_metadata.label} using GeoPandas.to_crs()."
        )
    else:
        working_geom = source_geom
        reprojection_note = "AOI source CRS and working CRS are the same; no reprojection performed."

    if working_geom.is_empty:
        raise ValueError("Working AOI geometry is empty after CRS handling.")

    if not isinstance(working_geom, (Polygon, MultiPolygon)):
        raise ValueError(
            "Working AOI geometry is not Polygon or MultiPolygon. "
            f"Result type was: {working_geom.geom_type}"
        )

    if not working_geom.is_valid:
        raise ValueError(
            "Working AOI geometry is invalid after CRS handling. "
            "First implementation rejects invalid geometry rather than repairing it silently."
        )

    minx, miny, maxx, maxy = working_geom.bounds
    centroid = working_geom.centroid

    area_square_meters: float | None

    if (
        working_crs_metadata.linear_unit is not None
        and working_crs_metadata.linear_unit.lower() in {"metre", "meter"}
    ):
        area_square_meters = float(working_geom.area)
    else:
        area_square_meters = None
        warnings.append(
            "Working CRS unit is not meter/metre or could not be determined. "
            "area_square_meters was left as None."
        )

    transformation_metadata_json = {
        "source_crs_authority": source_crs_metadata.authority,
        "source_crs_wkid": source_crs_metadata.wkid,
        "source_crs_label": source_crs_metadata.label,
        "working_crs_authority": working_crs_metadata.authority,
        "working_crs_wkid": working_crs_metadata.wkid,
        "working_crs_label": working_crs_metadata.label,
        "was_reprojected": was_reprojected,
        "method": "geopandas.to_crs" if was_reprojected else "none",
    }

    warnings.extend(source_crs_metadata.warnings)
    warnings.extend(working_crs_metadata.warnings)

    return AoiMetadata(
        source_file_path=shapefile_path,
        source_layer_name=shapefile_path.stem,
        source_crs_authority=source_crs_metadata.authority,
        source_crs_wkid=source_crs_metadata.wkid,
        source_crs_label=source_crs_metadata.label,
        working_crs_authority=working_crs_metadata.authority,
        working_crs_wkid=working_crs_metadata.wkid,
        working_crs_label=working_crs_metadata.label,
        geom_original_wkt=geom_original_wkt,
        geom_wkt=working_geom.wkt,
        was_reprojected=was_reprojected,
        reprojection_note=reprojection_note,
        transformation_metadata_json=transformation_metadata_json,
        area_square_meters=area_square_meters,
        bbox_xmin=float(minx),
        bbox_ymin=float(miny),
        bbox_xmax=float(maxx),
        bbox_ymax=float(maxy),
        centroid_x=float(centroid.x),
        centroid_y=float(centroid.y),
        warnings=warnings,
    )

# ---------------------------------------------------------------------
# Mode 3A tile-plan computation helpers
# ---------------------------------------------------------------------

#Added with initial implementation of Mode 3A: create tile plan only
def compute_terrain_sample_structure(
    settings: Mode3ASettings,
) -> tuple[int, float, float]:
    """
    Compute terrain interval count, tile size, and target sample spacing.

    Returns:
        terrain_intervals_per_side
        tile_size_meters
        target_sample_spacing_meters
    """
    terrain_intervals_per_side = settings.heightmap_resolution - 1

    if terrain_intervals_per_side <= 0:
        raise ValueError(
            "heightmap_resolution must be greater than 1. "
            f"Got {settings.heightmap_resolution}."
        )

    if (
        settings.tile_size_strategy
        == TILE_SIZE_STRATEGY_DERIVE_FROM_HEIGHTMAP_AND_SPACING
    ):
        tile_size_meters = (
            terrain_intervals_per_side
            * settings.target_sample_spacing_meters
        )
        target_sample_spacing_meters = settings.target_sample_spacing_meters

    elif settings.tile_size_strategy == TILE_SIZE_STRATEGY_EXPLICIT_TILE_SIZE:
        if settings.explicit_tile_size_meters is None:
            raise ValueError(
                "explicit_tile_size_meters is required when tile_size_strategy "
                f"is {TILE_SIZE_STRATEGY_EXPLICIT_TILE_SIZE!r}."
            )

        tile_size_meters = settings.explicit_tile_size_meters
        target_sample_spacing_meters = (
            tile_size_meters / terrain_intervals_per_side
        )

    else:
        raise ValueError(
            f"Unsupported tile_size_strategy: {settings.tile_size_strategy!r}"
        )

    if tile_size_meters <= 0:
        raise ValueError(
            f"Computed tile_size_meters must be positive. Got {tile_size_meters}."
        )

    if target_sample_spacing_meters <= 0:
        raise ValueError(
            "Computed target_sample_spacing_meters must be positive. "
            f"Got {target_sample_spacing_meters}."
        )

    return (
        terrain_intervals_per_side,
        tile_size_meters,
        target_sample_spacing_meters,
    )

#Added with initial implementation of Mode 3A: create tile plan only
#This does not indicate severity of oversampling or downsampling; a subsequent
#function compute_sampling_spacing_metrics() will do that
def classify_sampling_relationship(
    source_cell_size: float,
    target_sample_spacing: float,
    tolerance: float = 1e-9,
) -> str:
    """
    Classify the relationship between source raster cell size and target
    terrain sample spacing.

    Returns one of:
        source_resolution_match
        conservative_oversampling
        downsampling
    """
    if target_sample_spacing > source_cell_size + tolerance:
        return SAMPLING_RELATIONSHIP_DOWNSAMPLING

    if target_sample_spacing < source_cell_size - tolerance:
        return SAMPLING_RELATIONSHIP_CONSERVATIVE_OVERSAMPLING

    return SAMPLING_RELATIONSHIP_SOURCE_RESOLUTION_MATCH

def compute_sampling_spacing_metrics(
    source_cell_size: float,
    target_sample_spacing: float,
) -> tuple[float, float, str]:
    """
    Compute spacing difference, percent difference, and severity label.

    Returns:
        spacing_difference_meters
        spacing_percent_difference
        sampling_severity

    Interpretation:
        spacing_difference_meters > 0:
            target spacing is coarser than source spacing

        spacing_difference_meters < 0:
            target spacing is finer than source spacing

        spacing_difference_meters == 0:
            target spacing matches source spacing
    """
    if source_cell_size <= 0:
        raise ValueError(
            f"source_cell_size must be positive. Got {source_cell_size}."
        )

    if target_sample_spacing <= 0:
        raise ValueError(
            "target_sample_spacing must be positive. "
            f"Got {target_sample_spacing}."
        )

    spacing_difference_meters = target_sample_spacing - source_cell_size

    spacing_percent_difference = (
        spacing_difference_meters / source_cell_size
    ) * 100.0

    absolute_percent_difference = abs(spacing_percent_difference)

    if absolute_percent_difference <= 0.01:
        sampling_severity = SAMPLING_SEVERITY_NONE
    elif absolute_percent_difference <= 5.0:
        sampling_severity = SAMPLING_SEVERITY_SLIGHT
    elif absolute_percent_difference <= 25.0:
        sampling_severity = SAMPLING_SEVERITY_MODERATE
    else:
        sampling_severity = SAMPLING_SEVERITY_STRONG

    return (
        spacing_difference_meters,
        spacing_percent_difference,
        sampling_severity,
    )

#Added with initial implementation of Mode 3A: create tile plan only
#For Mode 3A, the default grid origin should snap to the source raster grid, 
#not simply to the AOI southwest corner.
def floor_to_lattice(
    value: float,
    origin: float,
    spacing: float,
    tolerance: float = 1e-9,
) -> float:
    """
    Snap value down to the nearest lattice coordinate at or below value.

    The lattice is defined by:
        origin + n * spacing

    A small tolerance prevents tiny floating-point noise from snapping one
    interval too far downward when value is already effectively on the lattice.
    """
    if spacing <= 0:
        raise ValueError(f"Lattice spacing must be positive. Got {spacing}.")

    quotient = (value - origin) / spacing
    snapped_index = math.floor(quotient + tolerance)

    return origin + snapped_index * spacing

def ceil_positive_ratio(
    numerator: float,
    denominator: float,
    tolerance: float = 1e-9,
) -> int:
    """
    Return ceil(numerator / denominator) for positive planning dimensions.

    A small tolerance prevents tiny floating-point noise from creating an
    unnecessary extra tile.
    """
    if numerator <= 0:
        raise ValueError(f"Numerator must be positive. Got {numerator}.")

    if denominator <= 0:
        raise ValueError(f"Denominator must be positive. Got {denominator}.")

    return int(math.ceil((numerator / denominator) - tolerance))

#Added with initial implementation of Mode 3A: create tile plan only
#For first implementation, only `ceil_to_full_tiles` is supported as the 
#edge policy.
#All tile grids are understood to start counting in the southwest corner and
#to proceed to the right (east) until the first row is complete, and then to
#start again on the west just above the initial tile and count rightward again
#and so on.  This may be adjustable but ordinarily is the default.
#
#Regardless of the engine or runtime.  The JSON that accompanies any tile
#output will inform a script within the engine and that engine specific
#script will then present it to the engine as appropriate.
def compute_mode3a_grid_extent(
    source: Mode3SourceDataset,
    aoi: Mode3AoiDefinition,
    tile_size_meters: float,
    settings: Mode3ASettings,
) -> tuple[float, float, float, float, int, int]:
    """
    Compute the enclosing Mode 3A tile grid extent.

    Returns:
        grid_xmin
        grid_ymin
        grid_xmax
        grid_ymax
        rows
        cols
    """
    if settings.edge_policy != EDGE_POLICY_CEIL_TO_FULL_TILES:
        raise ValueError(
            f"Unsupported edge_policy for Mode 3A: {settings.edge_policy!r}"
        )

    if settings.grid_anchor_policy == GRID_ANCHOR_POLICY_SNAP_TO_SOURCE:
        if settings.snap_reference != SNAP_REFERENCE_SOURCE_CELL_EDGES:
            raise ValueError(
                f"Unsupported snap_reference for Mode 3A: "
                f"{settings.snap_reference!r}"
            )

        grid_xmin = floor_to_lattice(
            value=aoi.bbox_xmin,
            origin=source.source_xmin,
            spacing=source.source_cell_size_x,
        )
        grid_ymin = floor_to_lattice(
            value=aoi.bbox_ymin,
            origin=source.source_ymin,
            spacing=source.source_cell_size_y,
        )

    elif settings.grid_anchor_policy == GRID_ANCHOR_POLICY_AOI_SOUTHWEST:
        grid_xmin = aoi.bbox_xmin
        grid_ymin = aoi.bbox_ymin

    else:
        raise ValueError(
            f"Unsupported grid_anchor_policy for Mode 3A: "
            f"{settings.grid_anchor_policy!r}"
        )

    cols = ceil_positive_ratio(
        numerator=aoi.bbox_xmax - grid_xmin,
        denominator=tile_size_meters,
    )
    rows = ceil_positive_ratio(
        numerator=aoi.bbox_ymax - grid_ymin,
        denominator=tile_size_meters,
    )

    grid_xmax = grid_xmin + cols * tile_size_meters
    grid_ymax = grid_ymin + rows * tile_size_meters

    return grid_xmin, grid_ymin, grid_xmax, grid_ymax, rows, cols

#Added with initial implementation of Mode 3A: create tile plan only
def collect_mode3a_plan_warnings(
    source: Mode3SourceDataset,
    settings: Mode3ASettings,
    sampling_classification: str,
    target_sample_spacing_meters: float,
    sampling_spacing_percent_difference: float,
    sampling_severity: str,
) -> list[str]:
    """
    Collect warnings based on Mode 3A settings and computed sampling
    relationship.

    These warnings describe the sampling/grid plan. They do not inspect
    actual elevation values.
    """
    warnings: list[str] = []

    if (
        sampling_classification == SAMPLING_RELATIONSHIP_DOWNSAMPLING
        and settings.warn_when_target_spacing_exceeds_source_cell_size
    ):
        warnings.append(
            "Target sample spacing is coarser than source cell size. "
            f"Source cell size x={source.source_cell_size_x}, "
            f"target sample spacing={target_sample_spacing_meters}. "
            f"Spacing difference={sampling_spacing_percent_difference:.6f}%; "
            f"severity={sampling_severity}. "
            "This may discard source sampling detail."
        )

    if (
        sampling_classification
        == SAMPLING_RELATIONSHIP_CONSERVATIVE_OVERSAMPLING
        and settings.note_when_target_spacing_is_finer_than_source_cell_size
    ):
        warnings.append(
            "Target sample spacing is finer than source cell size. "
            f"Source cell size x={source.source_cell_size_x}, "
            f"target sample spacing={target_sample_spacing_meters}. "
            f"Spacing difference={sampling_spacing_percent_difference:.6f}%; "
            f"severity={sampling_severity}. "
            "This is conservative oversampling, not additional measured detail."
        )

    if (
        settings.grid_anchor_policy != GRID_ANCHOR_POLICY_SNAP_TO_SOURCE
        and settings.warn_when_grid_not_snapped_to_source
    ):
        warnings.append(
            "Tile grid is not snapped to the source raster grid. "
            "This can make the terrain sampling lattice less directly aligned "
            "with the source DEM cell structure."
        )

    return warnings

#Added with initial implementation of Mode 3A: create tile plan only
def compute_mode3a_plan(
    conn: psycopg.Connection,
    schema_name: str,
    run_id: str,
    source: Mode3SourceDataset,
    aoi: Mode3AoiDefinition,
    settings: Mode3ASettings,
) -> Mode3AComputedPlan:
    """
    Compute the complete Mode 3A tile-plan summary.

    This function performs planning calculations only. It does not prompt the
    user, write database records, export files, or create artifacts.
    """
    session_id = generate_available_mode3_session_id(
        conn=conn,
        schema_name=schema_name,
        run_id=run_id,
        operation_type=MODE3_OPERATION_CREATE_TILE_PLAN_ONLY,
    )

    (
        terrain_intervals_per_side,
        tile_size_meters,
        target_sample_spacing_meters,
    ) = compute_terrain_sample_structure(settings)

    sampling_classification = classify_sampling_relationship(
        source_cell_size=source.source_cell_size_x,
        target_sample_spacing=target_sample_spacing_meters,
    )

    (
        sampling_spacing_difference_meters,
        sampling_spacing_percent_difference,
        sampling_severity,
    ) = compute_sampling_spacing_metrics(
        source_cell_size=source.source_cell_size_x,
        target_sample_spacing=target_sample_spacing_meters,
    )

    (
        grid_xmin,
        grid_ymin,
        grid_xmax,
        grid_ymax,
        rows,
        cols,
    ) = compute_mode3a_grid_extent(
        source=source,
        aoi=aoi,
        tile_size_meters=tile_size_meters,
        settings=settings,
    )

    tile_count = rows * cols

    warnings = collect_mode3a_plan_warnings(
        source=source,
        settings=settings,
        sampling_classification=sampling_classification,
        target_sample_spacing_meters=target_sample_spacing_meters,
        sampling_spacing_percent_difference=sampling_spacing_percent_difference,
        sampling_severity=sampling_severity,
    )

    if aoi.working_crs_wkid is None:
        raise ValueError(
            f"AOI {aoi.aoi_id!r} has no working_crs_wkid."
        )

    return Mode3AComputedPlan(
        session_id=session_id,

        terrain_intervals_per_side=terrain_intervals_per_side,
        tile_size_meters=tile_size_meters,
        target_sample_spacing_meters=target_sample_spacing_meters,
        sampling_classification=sampling_classification,
        sampling_spacing_difference_meters=sampling_spacing_difference_meters,
        sampling_spacing_percent_difference=sampling_spacing_percent_difference,
        sampling_severity=sampling_severity,

        grid_xmin=grid_xmin,
        grid_ymin=grid_ymin,
        grid_xmax=grid_xmax,
        grid_ymax=grid_ymax,

        rows=rows,
        cols=cols,
        tile_count=tile_count,

        working_crs_wkid=aoi.working_crs_wkid,
        working_crs_label=aoi.working_crs_label or "",

        warnings=warnings,
    )

# ---------------------------------------------------------------------
# Mode 1 database write helpers
# ---------------------------------------------------------------------


def insert_external_file_dataset(
    conn: psycopg.Connection,
    schema_name: str,
    source_dataset_id: str,
    source_name: str,
    source_type: str,
    metadata: RasterMetadata,
    provenance_note: str | None,
    checksum_requested: bool,
) -> None:
    """
    Insert one source_raster_datasets row and one source_raster_files row.
    """
    validation_status = "warning" if metadata.warnings else "passed"
    srid_for_geometry = metadata.crs_wkid if metadata.crs_wkid is not None else 0

    source_metadata_json = {
        "registered_by": "terrain_tool.py",
        "terrain_tool_script_version": TERRAIN_TOOL_SCRIPT_VERSION,
        "mode": "mode1_single_file_external_file",
        "checksum_requested": checksum_requested,
        "checksum_computed": metadata.file_sha256 is not None,
        "warnings": metadata.warnings,
    }

    dataset_table = qualified_table(schema_name, "source_raster_datasets")
    file_table = qualified_table(schema_name, "source_raster_files")

    dataset_insert = sql.SQL(
        """
        INSERT INTO {dataset_table} (
            source_dataset_id,
            source_name,
            source_type,
            source_storage_mode,
            source_crs_authority,
            source_crs_wkid,
            source_crs_label,
            source_linear_unit,
            source_cell_size_x,
            source_cell_size_y,
            source_cell_size_unit,
            source_nodata_value,
            source_extent_geom,
            source_xmin,
            source_ymin,
            source_xmax,
            source_ymax,
            source_root_path,
            path_storage_mode,
            primary_source_path,
            vrt_path,
            vrt_origin,
            file_count,
            has_virtual_mosaic,
            has_postgis_raster_storage,
            source_metadata_json,
            provenance_note,
            registration_status,
            validation_status,
            last_error_message
        )
        VALUES (
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            ST_MakeEnvelope(%s, %s, %s, %s, %s),
            %s, %s, %s, %s,
            %s, %s, %s,
            NULL,
            %s,
            1,
            false,
            false,
            %s,
            %s,
            'registered',
            %s,
            NULL
        );
        """
    ).format(dataset_table=dataset_table)

    file_insert = sql.SQL(
        """
        INSERT INTO {file_table} (
            source_dataset_id,
            filename,
            relative_path,
            absolute_path,
            file_exists_at_registration,
            file_readable_at_registration,
            file_size_bytes,
            file_modified_time,
            file_sha256,
            file_crs_authority,
            file_crs_wkid,
            file_crs_label,
            file_cell_size_x,
            file_cell_size_y,
            file_nodata_value,
            raster_width_pixels,
            raster_height_pixels,
            raster_band_count,
            raster_dtype,
            file_extent_geom,
            file_xmin,
            file_ymin,
            file_xmax,
            file_ymax,
            is_part_of_virtual_mosaic,
            is_active,
            registration_note,
            validation_status,
            last_error_message
        )
        VALUES (
            %s, %s, %s, NULL,
            true, true,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s, %s,
            ST_MakeEnvelope(%s, %s, %s, %s, %s),
            %s, %s, %s, %s,
            false,
            true,
            %s,
            %s,
            NULL
        );
        """
    ).format(file_table=file_table)

    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute(
                dataset_insert,
                (
                    source_dataset_id,
                    source_name,
                    source_type,
                    SOURCE_STORAGE_MODE_EXTERNAL_FILE,
                    metadata.crs_authority,
                    metadata.crs_wkid,
                    metadata.crs_label,
                    metadata.linear_unit,
                    metadata.cell_size_x,
                    metadata.cell_size_y,
                    metadata.cell_size_unit,
                    metadata.nodata_value,
                    metadata.xmin,
                    metadata.ymin,
                    metadata.xmax,
                    metadata.ymax,
                    srid_for_geometry,
                    metadata.xmin,
                    metadata.ymin,
                    metadata.xmax,
                    metadata.ymax,
                    str(metadata.source_root_path),
                    PATH_STORAGE_MODE_ROOT_PLUS_RELATIVE,
                    str(metadata.primary_source_path),
                    "not_applicable",
                    Jsonb(source_metadata_json),
                    provenance_note,
                    validation_status,
                ),
            )

            cur.execute(
                file_insert,
                (
                    source_dataset_id,
                    metadata.filename,
                    metadata.relative_path.as_posix(),
                    metadata.file_size_bytes,
                    metadata.file_modified_time_utc,
                    metadata.file_sha256,
                    metadata.crs_authority,
                    metadata.crs_wkid,
                    metadata.crs_label,
                    metadata.cell_size_x,
                    metadata.cell_size_y,
                    metadata.nodata_value,
                    metadata.width_pixels,
                    metadata.height_pixels,
                    metadata.band_count,
                    metadata.dtype,
                    metadata.xmin,
                    metadata.ymin,
                    metadata.xmax,
                    metadata.ymax,
                    srid_for_geometry,
                    metadata.xmin,
                    metadata.ymin,
                    metadata.xmax,
                    metadata.ymax,
                    "Registered by Mode 1 single-file external_file workflow.",
                    validation_status,
                ),
            )

# ---------------------------------------------------------------------
# Mode 2 database write helpers
# ---------------------------------------------------------------------


def insert_aoi_definition(
    conn: psycopg.Connection,
    schema_name: str,
    aoi_id: str,
    aoi_name: str,
    description: str | None,
    aoi_source_type: str,
    metadata: AoiMetadata,
    provenance_note: str | None,
) -> None:
    """
    Insert one AOI definition row into aoi_definitions.

    First-pass Mode 2 behavior:
        - Stores the imported/source geometry in geom_original when available.
        - Stores the normalized workflow geometry in geom.
        - Uses WKT with ST_GeomFromText() for readability during development.
        - Marks validation_status as 'warning' if non-fatal warnings exist,
          otherwise 'passed'.

    Geometry SRID handling:
        - geom_original uses the source CRS WKID when available.
        - geom uses the working CRS WKID when available.
        - If a WKID is unavailable, SRID 0 is used.
    """
    validation_status = "warning" if metadata.warnings else "passed"

    source_srid = (
        metadata.source_crs_wkid
        if metadata.source_crs_wkid is not None
        else 0
    )

    working_srid = (
        metadata.working_crs_wkid
        if metadata.working_crs_wkid is not None
        else 0
    )

    transformation_metadata_json = dict(metadata.transformation_metadata_json)
    transformation_metadata_json["warnings"] = metadata.warnings

    aoi_table = qualified_table(schema_name, "aoi_definitions")

    insert_sql = sql.SQL(
        """
        INSERT INTO {aoi_table} (
            aoi_id,
            aoi_name,
            description,
            aoi_source_type,

            source_file_path,
            source_layer_name,

            source_crs_authority,
            source_crs_wkid,
            source_crs_label,

            working_crs_authority,
            working_crs_wkid,
            working_crs_label,

            geom_original,
            geom,

            was_reprojected,
            reprojection_note,
            transformation_metadata_json,

            area_square_meters,
            bbox_xmin,
            bbox_ymin,
            bbox_xmax,
            bbox_ymax,
            centroid_x,
            centroid_y,

            validation_status,
            last_error_message,
            provenance_note
        )
        VALUES (
            %s, %s, %s, %s,

            %s, %s,

            %s, %s, %s,

            %s, %s, %s,

            CASE
                WHEN %s::text IS NULL THEN NULL
                ELSE ST_GeomFromText(%s::text, %s)
            END,
            ST_GeomFromText(%s::text, %s),

            %s, %s, %s,

            %s, %s, %s, %s, %s, %s, %s,

            %s,
            NULL,
            %s
        );
        """
    ).format(aoi_table=aoi_table)

    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute(
                insert_sql,
                (
                    aoi_id,
                    aoi_name,
                    description,
                    aoi_source_type,

                    str(metadata.source_file_path),
                    metadata.source_layer_name,

                    metadata.source_crs_authority,
                    metadata.source_crs_wkid,
                    metadata.source_crs_label,

                    metadata.working_crs_authority,
                    metadata.working_crs_wkid,
                    metadata.working_crs_label,

                    metadata.geom_original_wkt,
                    metadata.geom_original_wkt,
                    source_srid,
                    metadata.geom_wkt,
                    working_srid,

                    metadata.was_reprojected,
                    metadata.reprojection_note,
                    Jsonb(transformation_metadata_json),

                    metadata.area_square_meters,
                    metadata.bbox_xmin,
                    metadata.bbox_ymin,
                    metadata.bbox_xmax,
                    metadata.bbox_ymax,
                    metadata.centroid_x,
                    metadata.centroid_y,

                    validation_status,
                    provenance_note,
                ),
            )

# ---------------------------------------------------------------------
# Mode 3 database write helpers
# ---------------------------------------------------------------------

#Added with initial implementation of Mode 3A: create tile plan only
def insert_mode3a_terrain_tile_run(
    conn: psycopg.Connection,
    schema_name: str,
    run_id: str,
    source: Mode3SourceDataset,
    aoi: Mode3AoiDefinition,
    settings: Mode3ASettings,
    computed: Mode3AComputedPlan,
) -> None:
    """
    Insert one terrain_tile_runs row for a Mode 3A plan-only operation.

    This records the run/session intent and resolved planning parameters.
    It does not mark the run completed; completion flags are updated after
    tile-grid rows and requested artifacts are written.
    """
    table = qualified_table(schema_name, "terrain_tile_runs")

    sampling_model_json = {
        "source_raster_model": "cell_center",
        "engine_heightmap_model": "vertex_grid",
        "heightmap_samples_per_side": settings.heightmap_resolution,
        "terrain_intervals_per_side": computed.terrain_intervals_per_side,
        "target_sample_spacing_meters": computed.target_sample_spacing_meters,
        "tile_size_meters": computed.tile_size_meters,
        "sampling_classification": computed.sampling_classification,
        "sampling_spacing_difference_meters": (
            computed.sampling_spacing_difference_meters
        ),
        "sampling_spacing_percent_difference": (
            computed.sampling_spacing_percent_difference
        ),
        "sampling_severity": computed.sampling_severity,
        "adjacent_tiles_duplicate_border_samples": True,
    }

    grid_convention_json = {
        "grid_anchor_policy": settings.grid_anchor_policy,
        "snap_reference": settings.snap_reference,
        "snap_min_direction": settings.snap_min_direction,
        "snap_max_direction": settings.snap_max_direction,
        "aoi_enclosure_policy": settings.aoi_enclosure_policy,
        "grid_origin_corner": GRID_ORIGIN_CORNER_SOUTHWEST,
        "tile_anchor_corner": TILE_ANCHOR_CORNER_SOUTHWEST,
        "row_increases_toward": ROW_INCREASES_TOWARD_NORTH,
        "col_increases_toward": COL_INCREASES_TOWARD_EAST,
        "tile_traversal": TILE_TRAVERSAL_ROW_MAJOR_SW_TO_NE,
        "grid_xmin": computed.grid_xmin,
        "grid_ymin": computed.grid_ymin,
        "grid_xmax": computed.grid_xmax,
        "grid_ymax": computed.grid_ymax,
        "rows": computed.rows,
        "cols": computed.cols,
        "tile_count": computed.tile_count,
    }

    nodata_handling_json = {
        "inside_source_nodata_strategy": "fail",
        "outside_source_coverage_strategy": "fail",
        "outside_aoi_padding_strategy": "edge_replicate_later",
        "note": (
            "Mode 3A records intended policies only. No raster pixels are "
            "created during plan-only mode."
        ),
    }

    run_metadata_json = {
        "mode": "Mode 3A",
        "mode_label": "Create tile plan only",
        "plan_only": True,
        "warnings": computed.warnings,
    }

    query = sql.SQL(
        """
        INSERT INTO {table} (
            session_id,
            run_id,
            derived_from_session_id,

            operation_type,
            operation_label,
            source_manifest_path,

            source_dataset_id,
            aoi_id,

            workflow_crs_authority,
            workflow_crs_wkid,
            workflow_crs_label,
            workflow_linear_unit,

            target_engine,
            target_geospatial_runtime,
            runtime_profile_id,

            working_crs_origin_x,
            working_crs_origin_y,
            working_crs_origin_z_meters,
            origin_anchor_corner,

            target_cell_size,
            heightmap_resolution,
            terrain_intervals_per_side,
            tile_size_meters,

            edge_policy,
            sampling_model_json,
            grid_convention_json,
            nodata_handling_json,

            output_root_folder,

            tile_plan_creation_requested,
            tile_plan_creation_completed,

            raster_tile_realization_requested,
            raster_tile_realization_completed,

            derived_raster_storage_requested,
            derived_raster_storage_completed,

            raw_file_export_requested,
            raw_file_export_completed,

            manifest_rule_generation_requested,
            manifest_rule_generation_completed,

            tile_catalog_generation_requested,
            tile_catalog_generation_completed,

            tile_grid_geopackage_export_requested,
            tile_grid_geopackage_export_completed,

            created_at,
            started_at,
            completed_at,

            operation_status,
            validation_status,
            failure_reason,
            last_error_message,

            run_metadata_json
        )
        VALUES (
            %(session_id)s,
            %(run_id)s,
            NULL,

            %(operation_type)s,
            %(operation_label)s,
            NULL,

            %(source_dataset_id)s,
            %(aoi_id)s,

            %(workflow_crs_authority)s,
            %(workflow_crs_wkid)s,
            %(workflow_crs_label)s,
            %(workflow_linear_unit)s,

            %(target_engine)s,
            %(target_geospatial_runtime)s,
            %(runtime_profile_id)s,

            %(working_crs_origin_x)s,
            %(working_crs_origin_y)s,
            %(working_crs_origin_z_meters)s,
            %(origin_anchor_corner)s,

            %(target_cell_size)s,
            %(heightmap_resolution)s,
            %(terrain_intervals_per_side)s,
            %(tile_size_meters)s,

            %(edge_policy)s,
            %(sampling_model_json)s,
            %(grid_convention_json)s,
            %(nodata_handling_json)s,

            %(output_root_folder)s,

            TRUE,
            FALSE,

            FALSE,
            FALSE,

            FALSE,
            FALSE,

            FALSE,
            FALSE,

            %(manifest_rule_generation_requested)s,
            FALSE,

            FALSE,
            FALSE,

            %(tile_grid_geopackage_export_requested)s,
            FALSE,

            NOW(),
            NOW(),
            NULL,

            'running',
            'not_checked',
            NULL,
            NULL,

            %(run_metadata_json)s
        );
        """
    ).format(table=table)

    params = {
        "session_id": computed.session_id,
        "run_id": run_id,

        "operation_type": MODE3_OPERATION_CREATE_TILE_PLAN_ONLY,
        "operation_label": "Mode 3A: create tile plan only",

        "source_dataset_id": source.source_dataset_id,
        "aoi_id": aoi.aoi_id,

        "workflow_crs_authority": aoi.working_crs_authority,
        "workflow_crs_wkid": aoi.working_crs_wkid,
        "workflow_crs_label": aoi.working_crs_label,
        "workflow_linear_unit": source.source_linear_unit,

        "target_engine": settings.target_engine,
        "target_geospatial_runtime": settings.target_geospatial_runtime,
        "runtime_profile_id": settings.runtime_profile_id,

        "working_crs_origin_x": computed.grid_xmin,
        "working_crs_origin_y": computed.grid_ymin,
        "working_crs_origin_z_meters": 0.0,
        "origin_anchor_corner": GRID_ORIGIN_CORNER_SOUTHWEST,

        # Existing schema field name. In Mode 3A this stores the resolved
        # target terrain sample spacing.
        "target_cell_size": computed.target_sample_spacing_meters,
        "heightmap_resolution": settings.heightmap_resolution,
        "terrain_intervals_per_side": computed.terrain_intervals_per_side,
        "tile_size_meters": computed.tile_size_meters,

        "edge_policy": settings.edge_policy,
        "sampling_model_json": Jsonb(sampling_model_json),
        "grid_convention_json": Jsonb(grid_convention_json),
        "nodata_handling_json": Jsonb(nodata_handling_json),

        "output_root_folder": (
            None
            if settings.output_root_folder is None
            else str(settings.output_root_folder)
        ),

        "manifest_rule_generation_requested": settings.generate_manifest_rule,
        "tile_grid_geopackage_export_requested": (
            settings.export_tile_grid_geopackage
        ),

        "run_metadata_json": Jsonb(run_metadata_json),
    }

    with conn.cursor() as cur:
        cur.execute(query, params)

#Added with initial implementation of Mode 3A: create tile plan only
#This helper should use SQL/PostGIS to generate the tile polygons. These will
#later be stored in a Geopackage via non-database write function.
#The intended filenames are only future filenames. They do not mean RAW/TIF 
#files exist.
def insert_mode3a_tile_grid_plan_rows(
    conn: psycopg.Connection,
    schema_name: str,
    aoi_id: str,
    settings: Mode3ASettings,
    computed: Mode3AComputedPlan,
) -> int:
    """
    Insert one terrain_tile_grid_plan row per planned tile.

    Tile geometries and AOI intersections are generated in PostGIS. The
    returned integer is the number of inserted tile-plan rows.
    """
    plan_table = qualified_table(schema_name, "terrain_tile_grid_plan")
    aoi_table = qualified_table(schema_name, "aoi_definitions")

    query = sql.SQL(
        """
        WITH params AS (
            SELECT
                %(session_id)s::text AS session_id,
                %(grid_xmin)s::double precision AS grid_xmin,
                %(grid_ymin)s::double precision AS grid_ymin,
                %(tile_size_meters)s::double precision AS tile_size_meters,
                %(rows)s::integer AS rows,
                %(cols)s::integer AS cols,
                %(working_crs_wkid)s::integer AS working_crs_wkid
        ),
        tile_indices AS (
            SELECT
                p.session_id,
                row_index,
                col_index,
                p.grid_xmin
                    + col_index * p.tile_size_meters AS xmin,
                p.grid_ymin
                    + row_index * p.tile_size_meters AS ymin,
                p.grid_xmin
                    + (col_index + 1) * p.tile_size_meters AS xmax,
                p.grid_ymin
                    + (row_index + 1) * p.tile_size_meters AS ymax,
                p.tile_size_meters,
                p.working_crs_wkid
            FROM params p
            CROSS JOIN generate_series(0, p.rows - 1) AS row_index
            CROSS JOIN generate_series(0, p.cols - 1) AS col_index
        ),
        tile_geoms AS (
            SELECT
                ti.*,
                ST_MakeEnvelope(
                    ti.xmin,
                    ti.ymin,
                    ti.xmax,
                    ti.ymax,
                    ti.working_crs_wkid
                ) AS grid_geom
            FROM tile_indices ti
        ),
        selected_aoi AS (
            SELECT geom
            FROM {aoi_table}
            WHERE aoi_id = %(aoi_id)s
        ),
        tile_intersections AS (
            SELECT
                tg.*,
                ST_Intersection(tg.grid_geom, a.geom) AS aoi_intersection_geom,
                ST_Area(tg.grid_geom) AS tile_area
            FROM tile_geoms tg
            CROSS JOIN selected_aoi a
        )
        INSERT INTO {plan_table} (
            session_id,
            tile_id,
            "row",
            col,

            grid_geom,

            planned_xmin,
            planned_ymin,
            planned_xmax,
            planned_ymax,

            planned_anchor_x,
            planned_anchor_y,
            planned_anchor_corner,

            working_crs_wkid,
            working_crs_label,

            raw_filename,
            tif_filename,

            edge_policy,
            is_edge_tile,

            planned_tile_width_meters,
            planned_tile_height_meters,

            aoi_intersection_geom,
            aoi_occupied_width_meters,
            aoi_occupied_height_meters,
            aoi_occupied_fraction,

            created_at,
            plan_status
        )
        SELECT
            ti.session_id,
            'r' || ti.row_index || '_c' || ti.col_index AS tile_id,
            ti.row_index AS "row",
            ti.col_index AS col,

            ti.grid_geom,

            ti.xmin,
            ti.ymin,
            ti.xmax,
            ti.ymax,

            ti.xmin,
            ti.ymin,
            %(planned_anchor_corner)s,

            %(working_crs_wkid)s,
            %(working_crs_label)s,

            'terrain_r' || ti.row_index || '_c' || ti.col_index || '.raw',
            'terrain_r' || ti.row_index || '_c' || ti.col_index || '.tif',

            %(edge_policy)s,
            NOT ST_Covers(a.geom, ti.grid_geom) AS is_edge_tile,

            ti.tile_size_meters,
            ti.tile_size_meters,

            ti.aoi_intersection_geom,

            CASE
                WHEN ST_IsEmpty(ti.aoi_intersection_geom) THEN NULL
                ELSE
                    ST_XMax(ST_Envelope(ti.aoi_intersection_geom))
                    - ST_XMin(ST_Envelope(ti.aoi_intersection_geom))
            END AS aoi_occupied_width_meters,

            CASE
                WHEN ST_IsEmpty(ti.aoi_intersection_geom) THEN NULL
                ELSE
                    ST_YMax(ST_Envelope(ti.aoi_intersection_geom))
                    - ST_YMin(ST_Envelope(ti.aoi_intersection_geom))
            END AS aoi_occupied_height_meters,

            CASE
                WHEN ti.tile_area = 0 THEN NULL
                ELSE ST_Area(ti.aoi_intersection_geom) / ti.tile_area
            END AS aoi_occupied_fraction,

            NOW(),
            'planned'
        FROM tile_intersections ti
        CROSS JOIN selected_aoi a
        ORDER BY ti.row_index, ti.col_index;
        """
    ).format(
        plan_table=plan_table,
        aoi_table=aoi_table,
    )

    params = {
        "session_id": computed.session_id,
        "grid_xmin": computed.grid_xmin,
        "grid_ymin": computed.grid_ymin,
        "tile_size_meters": computed.tile_size_meters,
        "rows": computed.rows,
        "cols": computed.cols,
        "working_crs_wkid": computed.working_crs_wkid,
        "working_crs_label": computed.working_crs_label,
        "aoi_id": aoi_id,
        "planned_anchor_corner": TILE_ANCHOR_CORNER_SOUTHWEST,
        "edge_policy": settings.edge_policy,
    }

    with conn.cursor() as cur:
        cur.execute(query, params)
        return int(cur.rowcount)

#Added with initial implementation of Mode 3A: create tile plan only
def update_mode3a_run_completion_status(
    conn: psycopg.Connection,
    schema_name: str,
    session_id: str,
    tile_plan_written: bool,
    manifest_written: bool,
    geopackage_written: bool,
    operation_status: str,
    validation_status: str,
    last_error_message: str | None = None,
) -> None:
    """
    Update requested/completed flags for a Mode 3A run.

    This should be called after tile-plan rows and requested artifacts have
    either succeeded or failed.
    """
    table = qualified_table(schema_name, "terrain_tile_runs")

    query = sql.SQL(
        """
        UPDATE {table}
        SET
            tile_plan_creation_completed = %(tile_plan_written)s,
            manifest_rule_generation_completed = %(manifest_written)s,
            tile_grid_geopackage_export_completed = %(geopackage_written)s,

            completed_at = NOW(),

            operation_status = %(operation_status)s,
            validation_status = %(validation_status)s,
            last_error_message = %(last_error_message)s
        WHERE session_id = %(session_id)s;
        """
    ).format(table=table)

    params = {
        "session_id": session_id,
        "tile_plan_written": tile_plan_written,
        "manifest_written": manifest_written,
        "geopackage_written": geopackage_written,
        "operation_status": operation_status,
        "validation_status": validation_status,
        "last_error_message": last_error_message,
    }

    with conn.cursor() as cur:
        cur.execute(query, params)

# ---------------------------------------------------------------------
# Mode 3A artifact helpers
# ---------------------------------------------------------------------

#Added with initial implementation of Mode 3A: create tile plan only
#This helper does not create the folder. The write helpers should create it 
#when needed.
def get_mode3a_output_folder(
    settings: Mode3ASettings,
    computed: Mode3AComputedPlan,
) -> Path:
    """
    Resolve the output folder for Mode 3A artifacts.

    The normal convention is one folder per session_id, so fixed artifact
    names such as manifest-rule.json and tile_grid.gpkg are safe inside
    that folder.
    """
    if settings.output_root_folder is None:
        output_root = Path("outputs") / "mode3"
    else:
        output_root = settings.output_root_folder

    return output_root / computed.session_id

#Added with initial implementation of Mode 3A: create tile plan only
#The manifest should include enough to recover or understand the plan:
#manifest identity
#database binding
#source dataset reference
#AOI reference
#workflow CRS
#runtime profile
#terrain sample structure
#sampling relationship
#grid convention
#planned output artifacts
#Mode 3A stage flags
#warnings
#
#It should also explicitly say that this is plan-only (see flags at bottom)
def build_mode3a_manifest_rule_dict(
    run_id: str,
    source: Mode3SourceDataset,
    aoi: Mode3AoiDefinition,
    settings: Mode3ASettings,
    computed: Mode3AComputedPlan,
) -> dict[str, Any]:
    """
    Build the manifest-rule.json content for a Mode 3A plan-only run.

    This returns a Python dictionary. It does not write the JSON file.
    """
    return {
        "manifest_type": "terrain_manifest_rule",
        "manifest_schema_version": "0.1",
        "workflow_stage": "mode3a_create_tile_plan_only",

        "database_binding": {
            "run_id": run_id,
            "session_id": computed.session_id,
            "source_dataset_id": source.source_dataset_id,
            "aoi_id": aoi.aoi_id,
            "operation_type": MODE3_OPERATION_CREATE_TILE_PLAN_ONLY,
        },

        "source_dataset": {
            "source_dataset_id": source.source_dataset_id,
            "source_name": source.source_name,
            "source_type": source.source_type,
            "source_storage_mode": source.source_storage_mode,
            "source_crs_authority": source.source_crs_authority,
            "source_crs_wkid": source.source_crs_wkid,
            "source_crs_label": source.source_crs_label,
            "source_linear_unit": source.source_linear_unit,
            "source_cell_size_x": source.source_cell_size_x,
            "source_cell_size_y": source.source_cell_size_y,
            "source_cell_size_unit": source.source_cell_size_unit,
            "source_nodata_value": source.source_nodata_value,
            "source_extent": {
                "xmin": source.source_xmin,
                "ymin": source.source_ymin,
                "xmax": source.source_xmax,
                "ymax": source.source_ymax,
            },
        },

        "aoi": {
            "aoi_id": aoi.aoi_id,
            "aoi_name": aoi.aoi_name,
            "working_crs_authority": aoi.working_crs_authority,
            "working_crs_wkid": aoi.working_crs_wkid,
            "working_crs_label": aoi.working_crs_label,
            "bbox": {
                "xmin": aoi.bbox_xmin,
                "ymin": aoi.bbox_ymin,
                "xmax": aoi.bbox_xmax,
                "ymax": aoi.bbox_ymax,
            },
            "area_square_meters": aoi.area_square_meters,
        },

        "runtime_profile": {
            "runtime_profile_id": settings.runtime_profile_id,
            "target_engine": settings.target_engine,
            "target_geospatial_runtime": settings.target_geospatial_runtime,
        },

        "terrain_sample_structure": {
            "heightmap_resolution": settings.heightmap_resolution,
            "terrain_intervals_per_side": computed.terrain_intervals_per_side,
            "tile_size_meters": computed.tile_size_meters,
            "target_sample_spacing_meters": (
                computed.target_sample_spacing_meters
            ),
            "source_raster_model": "cell_center",
            "engine_heightmap_model": "vertex_grid",
            "adjacent_tiles_duplicate_border_samples": True,
        },

        "sampling_relationship": {
            "classification": computed.sampling_classification,
            "spacing_difference_meters": (
                computed.sampling_spacing_difference_meters
            ),
            "spacing_percent_difference": (
                computed.sampling_spacing_percent_difference
            ),
            "severity": computed.sampling_severity,
        },

        "grid_convention": {
            "grid_anchor_policy": settings.grid_anchor_policy,
            "snap_reference": settings.snap_reference,
            "snap_min_direction": settings.snap_min_direction,
            "snap_max_direction": settings.snap_max_direction,
            "aoi_enclosure_policy": settings.aoi_enclosure_policy,
            "edge_policy": settings.edge_policy,

            "grid_origin_corner": GRID_ORIGIN_CORNER_SOUTHWEST,
            "tile_anchor_corner": TILE_ANCHOR_CORNER_SOUTHWEST,
            "row_increases_toward": ROW_INCREASES_TOWARD_NORTH,
            "col_increases_toward": COL_INCREASES_TOWARD_EAST,
            "tile_traversal": TILE_TRAVERSAL_ROW_MAJOR_SW_TO_NE,

            "grid_extent": {
                "xmin": computed.grid_xmin,
                "ymin": computed.grid_ymin,
                "xmax": computed.grid_xmax,
                "ymax": computed.grid_ymax,
            },
            "rows": computed.rows,
            "cols": computed.cols,
            "tile_count": computed.tile_count,
        },

        "planned_artifacts": {
            "manifest_rule": "manifest-rule.json",
            "tile_grid_geopackage": (
                "tile_grid.gpkg"
                if settings.export_tile_grid_geopackage
                else None
            ),
            "tile_catalog": None,
            "raw_files": None,
        },

        "mode3_stage_flags": {
            "tile_plan_creation_requested": True,
            "tile_plan_creation_completed": True,

            "raster_tile_realization_requested": False,
            "raster_tile_realization_completed": False,

            "derived_raster_storage_requested": False,
            "derived_raster_storage_completed": False,

            "raw_file_export_requested": False,
            "raw_file_export_completed": False,

            "manifest_rule_generation_requested": settings.generate_manifest_rule,
            "tile_catalog_generation_requested": False,
            "tile_catalog_generation_completed": False,

            "tile_grid_geopackage_export_requested": (
                settings.export_tile_grid_geopackage
            ),
        },

        "warnings": computed.warnings,
    }

#Added with initial implementation of Mode 3A: create tile plan only
#Write manifest-rule.json to disk.
def write_mode3a_manifest_rule_json(
    output_folder: Path,
    manifest_rule_dict: dict[str, Any],
) -> Path:
    """
    Write manifest-rule.json for a Mode 3A plan-only run.

    Returns the path to the written JSON file.
    """
    output_folder.mkdir(parents=True, exist_ok=True)

    manifest_path = output_folder / "manifest-rule.json"

    with manifest_path.open("w", encoding="utf-8") as file:
        json.dump(
            manifest_rule_dict,
            file,
            indent=2,
            ensure_ascii=False,
        )
        file.write("\n")

    return manifest_path

#Added with initial implementation of Mode 3A: create tile plan only
#This GPKG will be an inspection artifact, not an engine import catalog.
def export_mode3a_tile_grid_geopackage(
    conn: psycopg.Connection,
    schema_name: str,
    session_id: str,
    output_folder: Path,
) -> Path:
    """
    Export the Mode 3A planned tile grid to tile_grid.gpkg.

    The GeoPackage is for GIS inspection of the planned tile grid. It is not
    a tile catalog and does not imply that raster or RAW outputs exist.
    """
    output_folder.mkdir(parents=True, exist_ok=True)

    output_path = output_folder / "tile_grid.gpkg"

    table = qualified_table(schema_name, "terrain_tile_grid_plan")

    query = sql.SQL(
        """
        SELECT
            session_id,
            tile_id,
            "row",
            col,

            planned_xmin,
            planned_ymin,
            planned_xmax,
            planned_ymax,

            planned_anchor_x,
            planned_anchor_y,
            planned_anchor_corner,

            working_crs_wkid,
            working_crs_label,

            raw_filename,
            tif_filename,

            edge_policy,
            is_edge_tile,

            planned_tile_width_meters,
            planned_tile_height_meters,

            aoi_occupied_width_meters,
            aoi_occupied_height_meters,
            aoi_occupied_fraction,

            plan_status,

            grid_geom AS geom
        FROM {table}
        WHERE session_id = %s
        ORDER BY "row", col;
        """
    ).format(table=table)

    gdf = gpd.read_postgis(
        sql=query.as_string(conn),
        con=conn,
        geom_col="geom",
        params=(session_id,),
    )

    if gdf.empty:
        raise RuntimeError(
            f"No tile-grid plan rows found for session_id={session_id!r}."
        )

    if gdf.crs is None:
        first_wkid = gdf["working_crs_wkid"].iloc[0]
        if first_wkid is not None:
            gdf = gdf.set_crs(epsg=int(first_wkid), allow_override=True)

    gdf.to_file(
        output_path,
        layer="tile_grid_plan",
        driver="GPKG",
    )

    return output_path

# ---------------------------------------------------------------------
# Mode 3A confirmation summary helpers
# ---------------------------------------------------------------------

#Purpose of this section: 
#    Show the resolved Mode 3A run before anything is written.
#
#There are two warning sources:
#   compatibility_warnings:
#       produced by check_mode3a_source_aoi_compatibility()
#       concern source/AOI database facts
#
#   computed.warnings:
#       produced by compute_mode3a_plan()
#       concern computed sampling/grid-plan issues
#
#The summary should show both together.
#Fatal errors should already have stopped the workflow before this point. 
#This function is for confirmation, not for deciding whether Mode 3A is 
#allowed to proceed.

#Added with initial implementation of Mode 3A: create tile plan only
#Purpose of this function: Format numeric values for user-facing summaries.
#
#Raw floats can be visually noisy, especially if they contain many trailing 
#zeroes or tiny floating-point artifacts. This helper keeps enough precision 
#for projected CRS coordinates while making the summary readable.
def format_summary_float(
    value: float | None,
    decimals: int = 6,
) -> str:
    """
    Format a float for user-facing summaries.

    Keeps enough precision for projected CRS coordinates while avoiding
    excessive trailing zeroes.
    """
    if value is None:
        return "None"

    text = f"{value:.{decimals}f}"
    text = text.rstrip("0").rstrip(".")

    if text == "-0":
        return "0"

    return text

#Added with initial implementation of Mode 3A: create tile plan only
#Revised after initial testing of Mode 3A
#Purpose: Format CRS metadata for user-facing summaries.
#
#Source and AOI CRS values may have different levels of available metadata.
#This helper produces a readable CRS string from whatever pieces are present.
def format_summary_crs(
    authority: str | None,
    wkid: int | None,
    label: str | None,
) -> str:
    """
    Format CRS metadata for a user-facing summary.

    Avoids redundant output such as:
        EPSG:27700 (EPSG:27700)
    """
    authority_text = None if authority is None else str(authority).strip()
    label_text = None if label is None else str(label).strip()

    if authority_text and wkid is not None:
        authority_wkid_text = f"{authority_text}:{wkid}"

        if (
            label_text
            and label_text.lower() != authority_wkid_text.lower()
        ):
            return f"{authority_wkid_text} ({label_text})"

        return authority_wkid_text

    if label_text:
        return label_text

    return "unknown"


#Added after initial testing of Mode 3A: create tile plan only
def print_summary_line(
    label: str,
    value: Any,
    label_width: int = 34,
) -> None:
    """
    Print one aligned label/value row for user-facing summaries.

    The label is automatically suffixed with a colon and padded to a fixed
    width so values begin in the same column.
    """
    label_text = f"{label}:"
    print(f"{label_text:<{label_width}}{value}")

#Added with initial implementation of Mode 3A: create tile plan only
#Revised after initial testing of Mode 3A
#Main helper
#This function prints the resolved state after all defaults and computed 
#values are known.
def print_mode3a_confirmation_summary(
    run_id: str,
    source: Mode3SourceDataset,
    aoi: Mode3AoiDefinition,
    settings: Mode3ASettings,
    computed: Mode3AComputedPlan,
    compatibility_warnings: list[str] | None = None,
) -> None:
    """
    Print a user-facing confirmation summary for a Mode 3A plan-only run.

    This function does not prompt, write database records, or create files.
    It only displays the resolved run settings and computed plan so the user
    can accept, change settings, or cancel.
    """
    compatibility_warnings = compatibility_warnings or []
    all_warnings = compatibility_warnings + computed.warnings

    source_crs = format_summary_crs(
        authority=source.source_crs_authority,
        wkid=source.source_crs_wkid,
        label=source.source_crs_label,
    )

    aoi_crs = format_summary_crs(
        authority=aoi.working_crs_authority,
        wkid=aoi.working_crs_wkid,
        label=aoi.working_crs_label,
    )

    source_unit_suffix = (
        ""
        if source.source_cell_size_unit is None
        else f" {source.source_cell_size_unit}"
    )

    source_cell_size_text = (
        f"x={format_summary_float(source.source_cell_size_x)} "
        f"y={format_summary_float(source.source_cell_size_y)}"
        f"{source_unit_suffix}"
    )

    source_extent_text = (
        f"xmin={format_summary_float(source.source_xmin)}, "
        f"ymin={format_summary_float(source.source_ymin)}, "
        f"xmax={format_summary_float(source.source_xmax)}, "
        f"ymax={format_summary_float(source.source_ymax)}"
    )

    aoi_bbox_text = (
        f"xmin={format_summary_float(aoi.bbox_xmin)}, "
        f"ymin={format_summary_float(aoi.bbox_ymin)}, "
        f"xmax={format_summary_float(aoi.bbox_xmax)}, "
        f"ymax={format_summary_float(aoi.bbox_ymax)}"
    )

    grid_origin_text = (
        f"x={format_summary_float(computed.grid_xmin)}, "
        f"y={format_summary_float(computed.grid_ymin)}"
    )

    grid_extent_text = (
        f"xmin={format_summary_float(computed.grid_xmin)}, "
        f"ymin={format_summary_float(computed.grid_ymin)}, "
        f"xmax={format_summary_float(computed.grid_xmax)}, "
        f"ymax={format_summary_float(computed.grid_ymax)}"
    )

    print()
    print("=" * 72)
    print("Mode 3A: Create Tile Plan Only")
    print("=" * 72)

    print("\nRun identity")
    print("-" * 72)
    print_summary_line("Operation", MODE3_OPERATION_CREATE_TILE_PLAN_ONLY)
    print_summary_line("run_id", run_id)
    print_summary_line("session_id", computed.session_id)

    print("\nSource dataset")
    print("-" * 72)
    print_summary_line("source_dataset_id", source.source_dataset_id)
    print_summary_line("source name", source.source_name)
    print_summary_line("source type", source.source_type)
    print_summary_line("source storage mode", source.source_storage_mode)
    print_summary_line("source CRS", source_crs)
    print_summary_line("source cell size", source_cell_size_text)
    print_summary_line("source extent", source_extent_text)

    print("\nAOI")
    print("-" * 72)
    print_summary_line("aoi_id", aoi.aoi_id)
    print_summary_line("AOI name", aoi.aoi_name)
    print_summary_line("AOI working CRS", aoi_crs)
    print_summary_line("AOI bbox", aoi_bbox_text)
    print_summary_line(
        "AOI area sq meters",
        format_summary_float(aoi.area_square_meters),
    )

    print("\nRuntime profile")
    print("-" * 72)
    print_summary_line("runtime_profile_id", settings.runtime_profile_id)
    print_summary_line("target engine", settings.target_engine)
    print_summary_line(
        "target geospatial runtime",
        settings.target_geospatial_runtime,
    )

    print("\nTerrain sample structure")
    print("-" * 72)
    print_summary_line("heightmap resolution", settings.heightmap_resolution)
    print_summary_line(
        "terrain intervals per side",
        computed.terrain_intervals_per_side,
    )
    print_summary_line(
        "target sample spacing meters",
        format_summary_float(computed.target_sample_spacing_meters),
    )
    print_summary_line(
        "tile size meters",
        format_summary_float(computed.tile_size_meters),
    )
    print_summary_line("tile size strategy", settings.tile_size_strategy)

    print("\nSampling relationship")
    print("-" * 72)
    print_summary_line("classification", computed.sampling_classification)
    print_summary_line("severity", computed.sampling_severity)
    print_summary_line(
        "spacing difference meters",
        format_summary_float(computed.sampling_spacing_difference_meters),
    )
    print_summary_line(
        "spacing percent difference",
        f"{format_summary_float(computed.sampling_spacing_percent_difference)}%",
    )

    print("\nGrid convention")
    print("-" * 72)
    print_summary_line("grid anchor policy", settings.grid_anchor_policy)
    print_summary_line("snap reference", settings.snap_reference)
    print_summary_line("snap min direction", settings.snap_min_direction)
    print_summary_line("snap max direction", settings.snap_max_direction)
    print_summary_line("AOI enclosure policy", settings.aoi_enclosure_policy)
    print_summary_line("edge policy", settings.edge_policy)
    print_summary_line("grid origin corner", GRID_ORIGIN_CORNER_SOUTHWEST)
    print_summary_line("tile anchor corner", TILE_ANCHOR_CORNER_SOUTHWEST)
    print_summary_line("row increases toward", ROW_INCREASES_TOWARD_NORTH)
    print_summary_line("column increases toward", COL_INCREASES_TOWARD_EAST)

    print("\nComputed grid")
    print("-" * 72)
    print_summary_line("grid origin", grid_origin_text)
    print_summary_line("grid extent", grid_extent_text)
    print_summary_line("rows", computed.rows)
    print_summary_line("columns", computed.cols)
    print_summary_line("tile count", computed.tile_count)

    print("\nRequested artifacts and outputs")
    print("-" * 72)
    print_summary_line(
        "Generate manifest-rule.json",
        "yes" if settings.generate_manifest_rule else "no",
    )
    print_summary_line(
        "Export tile_grid.gpkg",
        "yes" if settings.export_tile_grid_geopackage else "no",
    )
    print_summary_line("Generate tile-catalog.json", "no")
    print_summary_line("Create raster tiles", "no")
    print_summary_line("Store derived rasters in PostGIS", "no")
    print_summary_line("Export RAW files", "no")

    print("\nOutput folder")
    print("-" * 72)
    if settings.output_root_folder is None:
        print_summary_line("configured output root", "default outputs/mode3")
    else:
        print_summary_line(
            "configured output root",
            settings.output_root_folder,
        )

    print("\nWarnings")
    print("-" * 72)
    if not all_warnings:
        print("None")
    else:
        for warning in all_warnings:
            print(f"- {warning}")

    print()
    print("=" * 72)
    print("No database records or files have been written yet.")
    print("=" * 72)
    print()

# ---------------------------------------------------------------------
# Mode 1 user-facing workflows
# ---------------------------------------------------------------------

#Added with initial implementation of Mode 1A: register single raster file
def print_single_file_summary(
    source_dataset_id: str,
    source_name: str,
    source_type: str,
    metadata: RasterMetadata,
    provenance_note: str | None,
    checksum_requested: bool,
) -> None:
    """
    Print confirmation summary before database write.
    """
    print("\nMode 1 registration summary")
    print("=" * 72)
    print(f"source_dataset_id:       {source_dataset_id}")
    print(f"source_name:             {source_name}")
    print(f"source_type:             {source_type}")
    print(f"source_storage_mode:     {SOURCE_STORAGE_MODE_EXTERNAL_FILE}")
    print(f"path_storage_mode:       {PATH_STORAGE_MODE_ROOT_PLUS_RELATIVE}")
    print(f"source_root_path:        {metadata.source_root_path}")
    print(f"relative_path:           {metadata.relative_path.as_posix()}")
    print(f"primary_source_path:     {metadata.primary_source_path}")
    print("file_count:              1")
    print(f"CRS:                     {metadata.crs_label}")
    print(f"CRS authority:           {metadata.crs_authority}")
    print(f"CRS WKID:                {metadata.crs_wkid}")
    print(f"CRS unit:                {metadata.linear_unit}")
    print(f"cell_size_x:             {metadata.cell_size_x}")
    print(f"cell_size_y:             {metadata.cell_size_y}")
    print(f"NoData:                  {metadata.nodata_value}")
    print(f"width x height:          {metadata.width_pixels} x {metadata.height_pixels}")
    print(f"band_count:              {metadata.band_count}")
    print(f"dtype:                   {metadata.dtype}")
    print(
        "extent:                  "
        f"xmin={metadata.xmin}, ymin={metadata.ymin}, "
        f"xmax={metadata.xmax}, ymax={metadata.ymax}"
    )
    print(f"file_size_bytes:         {metadata.file_size_bytes}")
    print(f"file_modified_time_utc:  {metadata.file_modified_time_utc}")
    print(f"checksum_requested:      {checksum_requested}")
    print(f"file_sha256:             {metadata.file_sha256}")
    print(f"provenance_note:         {provenance_note}")

    if metadata.warnings:
        print("\nWarnings:")
        for warning in metadata.warnings:
            print(f"  - {warning}")
    else:
        print("\nWarnings: none")

    print("=" * 72)

#Added with initial implementation of Mode 1A: register single raster file
def register_single_external_file(
    conn: psycopg.Connection,
    app_config: AppConfig,
    mode1_logger: logging.Logger,
) -> None:
    """
    Mode 1 branch: register one raster file as external_file.
    """
    print("\nMode 1A: Register single raster file as external_file")
    print("This branch registers metadata and file references only.")
    print("It does not load raster pixels into PostgreSQL/PostGIS.\n")
    
    
    print("First, you must create a dataset ID. This will be a stable, unique identifier string.")
    print("In SQL terms, this will be the primary key.\n")
    print("RULES:")
    print("Must start with a lowercase letter.")
    print("May contain lowercase letters, numbers, underscores, and hyphens.")
    print("Length 3–80 characters.")
    print("For instance, if you want to make the dataset name 'Local Site DTM 1m', ")
    print("the ID could be something like 'local_site_dtm_1m'.\n")

    while True:
        source_dataset_id = prompt_nonempty("Enter source_dataset_id: ")

        #checks input against pattern defined at top
        if not STABLE_IDENTIFIER_PATTERN.fullmatch(source_dataset_id): 
            print(
                f"\nInvalid source_dataset_id: {source_dataset_id}\n"
                "Please enter a source_dataset_id that follows the defined rules.\n\n"
                "RULES:\n"
                "Must start with a lowercase letter.\n"
                "May contain lowercase letters, numbers, underscores, and hyphens.\n"
                "Length 3–80 characters.\n"
                "Example: local_site_dtm_1m\n"
        )
            continue

        if source_dataset_exists(conn, app_config.schema_name, source_dataset_id):
            print(
                f"\nA source dataset already exists with ID: {source_dataset_id}\n"
                "This first implementation does not update existing datasets.\n"
                "Choose a different source_dataset_id or delete/reset the existing record deliberately.\n"
        )
            continue
        
        break
    
    print(f"\nYou have chosen source ID: {source_dataset_id}\n\n"
          "Next, you will create a dataset name. "
          "There is no technical requirement that this be unique, "
          "though using an existing name may cause confusion. "
          "The only rule is the length must be 3-80 characters.\n"
    )
    while True:
        source_name = prompt_nonempty("Enter source dataset name: ").strip()

        if not (3 <= len(source_name) <= 80):
            print(
                "\nInvalid source dataset name length."
                "Please enter a source dataset name between 3 and 80 characters.\n"
        )
            continue
        if source_name_exists(conn, app_config.schema_name, source_name):
            print(
            f"\nA source dataset with this display name already exists: {source_name}\n"
            "This is allowed, but it may be confusing for humans.\n"
        )
            proceed_with_duplicate_name = prompt_yes_no(
            "Continue with this duplicate display name?",
                default=False,
        )

            if not proceed_with_duplicate_name:
                continue

        break
    
    print(f"\nYou have chosen source name: {source_name}\n\n")
    
    source_type = prompt_source_type()
    print(f"\nYou have selected {source_type}\n")

    # Below: for single-file external registration, store the containing folder as
    # source_root_path and the filename as relative_path. This keeps the file
    # reference portable: if the dataset folder moves later, the dataset-level
    # source_root_path can be updated without rewriting the file-level relative_path.
    # The same pattern becomes especially important for multi-file datasets.

    raster_path = prompt_existing_file("Enter path to raster file (you can click and drag the file to paste the path here): ")

    print("\nDefault path handling for a single file:")
    print(f"  source_root_path = {raster_path.parent}")
    print(f"  relative_path    = {raster_path.name}")
    print("  path_storage_mode = root_plus_relative")

    checksum_requested = prompt_yes_no(
        "\nCompute SHA-256 checksum for this file?",
        default=False,
    )

    if checksum_requested:
        print("\nComputing SHA-256 checksum using chunked reads.")
        print("This is memory-safe, but it still reads the full file from disk.\n")

    try:
        metadata = read_single_raster_metadata(
            raster_path,
            compute_checksum=checksum_requested,
        )
    except Exception as error:
        mode1_logger.error("Failed to read raster metadata: %s", error)
        print(f"\nFailed to read raster metadata: {error}\n")
        return

    if metadata.crs_label is None:
        print("\nThis raster has no readable CRS. Registration aborted.\n")
        mode1_logger.error("Registration aborted because raster has no readable CRS: %s", raster_path)
        return

    provenance_note = prompt_optional(
        "Optional provenance note / description. Press Enter to skip: "
    )# consider adding length rule here and checking for it

    print_single_file_summary(
        source_dataset_id=source_dataset_id,
        source_name=source_name,
        source_type=source_type,
        metadata=metadata,
        provenance_note=provenance_note,
        checksum_requested=checksum_requested,
    )

    proceed = prompt_yes_no("Write this source dataset registration to the database?", default=False)

    if not proceed:
        print("\nRegistration aborted. No database records were written.\n")
        mode1_logger.info(
            "User aborted single-file registration for source_dataset_id=%s",
            source_dataset_id,
        )
        return

    try:
        insert_external_file_dataset(
            conn=conn,
            schema_name=app_config.schema_name,
            source_dataset_id=source_dataset_id,
            source_name=source_name,
            source_type=source_type,
            metadata=metadata,
            provenance_note=provenance_note,
            checksum_requested=checksum_requested,
        )
    except Exception as error:
        mode1_logger.error("Database insert failed: %s", error)
        print(f"\nDatabase insert failed: {error}\n")
        return

    mode1_logger.info(
        "Registered single external raster file. source_dataset_id=%s path=%s",
        source_dataset_id,
        raster_path,
    )

    print("\nRegistration completed successfully.")
    print(f"Registered source_dataset_id: {source_dataset_id}\n")

#Added with initial implementation of Mode 1A: register single raster file
def mode1_menu(
    conn: psycopg.Connection,
    app_config: AppConfig,
    mode1_logger: logging.Logger,
) -> None:
    """
    Mode 1 menu loop.
    """
    while True:
        choice = prompt_choice(
            "Mode 1: Register Source Raster Dataset",
            [
                ("single_external_file", "Register single raster file as external_file"),
                ("list", "List existing source raster datasets"),
                ("external_files_placeholder", "Register folder/CSV as external_files [not implemented yet]"),
                ("virtual_mosaic_placeholder", "Register/create virtual_mosaic [not implemented yet]"),
                ("postgis_raster_placeholder", "Register postgis_raster source [recognized, deferred]"),
                ("return", "Return to main menu"),
            ],
        )

        if choice == "single_external_file":
            register_single_external_file(conn, app_config, mode1_logger)

        elif choice == "list":
            list_source_datasets(conn, app_config.schema_name)

        elif choice == "external_files_placeholder":
            print("\nFolder/CSV external_files registration is not implemented in this pass.\n")

        elif choice == "virtual_mosaic_placeholder":
            print("\nvirtual_mosaic registration/VRT creation is not implemented in this pass.\n")

        elif choice == "postgis_raster_placeholder":
            print(
                "\npostgis_raster source storage is recognized by the schema, "
                "but source raster payload loading is deferred.\n"
            )

        elif choice == "return":
            return

# ---------------------------------------------------------------------
# Mode 2 user-facing workflows
# ---------------------------------------------------------------------

#Added with initial implementation of Mode 2A: register AOI from SHP file
def print_aoi_summary(
    aoi_id: str,
    aoi_name: str,
    description: str | None,
    metadata: AoiMetadata,
    provenance_note: str | None,
) -> None:
    """
    Print AOI confirmation summary before database write.
    """
    print("\nMode 2 AOI registration summary")
    print("=" * 72)
    print(f"aoi_id:                   {aoi_id}")
    print(f"aoi_name:                 {aoi_name}")
    print(f"description:              {description}")
    print(f"aoi_source_type:          {AOI_SOURCE_TYPE_SHAPEFILE}")
    print(f"source_file_path:         {metadata.source_file_path}")
    print(f"source_layer_name:        {metadata.source_layer_name}")

    print(f"source CRS:               {metadata.source_crs_label}")
    print(f"source CRS authority:     {metadata.source_crs_authority}")
    print(f"source CRS WKID:          {metadata.source_crs_wkid}")

    print(f"working CRS:              {metadata.working_crs_label}")
    print(f"working CRS authority:    {metadata.working_crs_authority}")
    print(f"working CRS WKID:         {metadata.working_crs_wkid}")

    print(f"was_reprojected:          {metadata.was_reprojected}")
    print(f"reprojection_note:        {metadata.reprojection_note}")

    print(f"area_square_meters:       {metadata.area_square_meters}")
    print(
        "bbox:                     "
        f"xmin={metadata.bbox_xmin}, ymin={metadata.bbox_ymin}, "
        f"xmax={metadata.bbox_xmax}, ymax={metadata.bbox_ymax}"
    )
    print(f"centroid_x:               {metadata.centroid_x}")
    print(f"centroid_y:               {metadata.centroid_y}")
    print(f"provenance_note:          {provenance_note}")

    if metadata.warnings:
        print("\nWarnings:")
        for warning in metadata.warnings:
            print(f"  - {warning}")
    else:
        print("\nWarnings: none")

    print("=" * 72)

#Added with initial implementation of Mode 2A: register AOI from SHP file
def register_shapefile_aoi(
    conn: psycopg.Connection,
    app_config: AppConfig,
    mode2_logger: logging.Logger,
) -> None:
    """
    Mode 2 branch: register one shapefile polygon/multipolygon as an AOI.
    """
    print("\nMode 2A: Register AOI from Shapefile")
    print("This branch registers a reusable AOI boundary.")
    print("It stores normalized AOI geometry in PostgreSQL/PostGIS.")
    print("It does not ask for engine, SDK, runtime, RAW, or tile settings.\n")

    print("First, you must create an AOI ID. This will be a stable, unique identifier string.")
    print("In SQL terms, this will be the primary key in aoi_definitions.\n")
    print("RULES:")
    print("Must start with a lowercase letter.")
    print("May contain lowercase letters, numbers, underscores, and hyphens.")
    print("Length 3–80 characters.")
    print("Example: yrwyddfa_test_aoi\n")

    while True:
        aoi_id = prompt_nonempty("Enter aoi_id: ")

        if not STABLE_IDENTIFIER_PATTERN.fullmatch(aoi_id):
            print(
                f"\nInvalid aoi_id: {aoi_id}\n"
                "Please enter an aoi_id that follows the defined rules.\n\n"
                "RULES:\n"
                "Must start with a lowercase letter.\n"
                "May contain lowercase letters, numbers, underscores, and hyphens.\n"
                "Length 3–80 characters.\n"
                "Example: yrwyddfa_test_aoi\n"
            )
            continue

        if aoi_exists(conn, app_config.schema_name, aoi_id):
            print(
                f"\nAn AOI already exists with ID: {aoi_id}\n"
                "This first implementation does not update existing AOIs.\n"
                "Choose a different aoi_id or delete/reset the existing record deliberately.\n"
            )
            continue

        break

    print(
        f"\nYou have chosen AOI ID: {aoi_id}\n\n"
        "Next, you will create an AOI name. "
        "There is no technical requirement that this be unique, "
        "though using an existing name may cause confusion. "
        "The only rule is the length must be 3–80 characters.\n"
    )

    while True:
        aoi_name = prompt_nonempty("Enter AOI name: ").strip()

        if not (3 <= len(aoi_name) <= 80):
            print(
                "\nInvalid AOI name length.\n"
                "Please enter an AOI name between 3 and 80 characters.\n"
            )
            continue

        if aoi_name_exists(conn, app_config.schema_name, aoi_name):
            print(
                f"\nAn AOI with this display name already exists: {aoi_name}\n"
                "This is allowed, but it may be confusing for humans.\n"
            )

            proceed_with_duplicate_name = prompt_yes_no(
                "Continue with this duplicate AOI name?",
                default=False,
            )

            if not proceed_with_duplicate_name:
                continue

        break

    print(f"\nYou have chosen AOI name: {aoi_name}\n")

    description = prompt_optional(
        "Optional AOI description. Press Enter to skip: "
    )

    shapefile_path = prompt_existing_shapefile(
        "Enter path to AOI shapefile .shp file "
        "(you can drag the file here to paste the path): "
    )

    working_crs_choice = prompt_choice(
        "Choose AOI working CRS",
        [
            ("source_file_crs", "Use the shapefile CRS as the working CRS"),
            ("registered_source_dataset_crs", "Use CRS from a registered source raster dataset"),
            ("manual_epsg", "Enter working CRS EPSG code manually"),
        ],
    )

    working_crs_input: Any | None = None

    if working_crs_choice == "source_file_crs":
        working_crs_input = None
        print("\nAOI working CRS will be the shapefile CRS.\n")

    elif working_crs_choice == "registered_source_dataset_crs":
        try:
            check_required_tables(
                conn=conn,
                schema_name=app_config.schema_name,
                required_tables=["source_raster_datasets"],
                context_label="Mode 2 registered source CRS lookup",
            )
        except RuntimeError as error:
            mode2_logger.error("%s", error)
            print(f"\n{error}\n")
            return

        print(
            "\nEnter the source_dataset_id whose CRS should be used as the AOI working CRS."
        )
        print("Type 'list' to show registered source raster datasets.\n")

        while True:
            source_dataset_id_for_crs = prompt_nonempty(
                "Enter ID (source_dataset_id) for CRS lookup: "
            )

            if source_dataset_id_for_crs.lower() == "list":
                list_source_datasets(conn, app_config.schema_name)
                continue

            source_crs_metadata = get_registered_source_dataset_crs(
                conn=conn,
                schema_name=app_config.schema_name,
                source_dataset_id=source_dataset_id_for_crs,
            )

            if source_crs_metadata is None:
                print(
                    f"\nNo registered source dataset found with ID: {source_dataset_id_for_crs}\n"
                    "Enter a different source_dataset_id, or type 'list'.\n"
                )
                continue

            if source_crs_metadata.label is None:
                print(
                    f"\nRegistered source dataset has no usable CRS label: {source_dataset_id_for_crs}\n"
                    "Choose a different source dataset or use manual EPSG entry.\n"
                )
                continue

            working_crs_input = source_crs_metadata.label

            print(
                f"\nAOI working CRS will use registered source dataset CRS: "
                f"{source_crs_metadata.label}\n"
            )
            break

    elif working_crs_choice == "manual_epsg":
        while True:
            epsg_text = prompt_nonempty("Enter working CRS EPSG code, for example 27700: ")

            try:
                epsg_code = int(epsg_text)
                PyprojCRS.from_epsg(epsg_code)
            except Exception as error:
                print(
                    f"\nInvalid EPSG code: {epsg_text}\n"
                    f"pyproj could not interpret this EPSG code: {error}\n"
                )
                continue

            working_crs_input = f"EPSG:{epsg_code}"
            print(f"\nAOI working CRS will be EPSG:{epsg_code}\n")
            break

    try:
        metadata = read_shapefile_aoi_metadata(
            shapefile_path=shapefile_path,
            working_crs_input=working_crs_input,
        )
    except Exception as error:
        mode2_logger.error("Failed to read or normalize shapefile AOI: %s", error)
        print(f"\nFailed to read or normalize shapefile AOI: {error}\n")
        return

    provenance_note = prompt_optional(
        "Optional AOI provenance note. Press Enter to skip: "
    )

    print_aoi_summary(
        aoi_id=aoi_id,
        aoi_name=aoi_name,
        description=description,
        metadata=metadata,
        provenance_note=provenance_note,
    )

    proceed = prompt_yes_no(
        "Write this AOI definition to the database?",
        default=False,
    )

    if not proceed:
        print("\nAOI registration aborted. No database records were written.\n")
        mode2_logger.info(
            "User aborted shapefile AOI registration for aoi_id=%s",
            aoi_id,
        )
        return

    try:
        insert_aoi_definition(
            conn=conn,
            schema_name=app_config.schema_name,
            aoi_id=aoi_id,
            aoi_name=aoi_name,
            description=description,
            aoi_source_type=AOI_SOURCE_TYPE_SHAPEFILE,
            metadata=metadata,
            provenance_note=provenance_note,
        )
    except Exception as error:
        mode2_logger.error("AOI database insert failed: %s", error)
        print(f"\nAOI database insert failed: {error}\n")
        return

    mode2_logger.info(
        "Registered shapefile AOI. aoi_id=%s path=%s",
        aoi_id,
        shapefile_path,
    )

    print("\nAOI registration completed successfully.")
    print(f"Registered aoi_id: {aoi_id}\n")

#Added with initial implementation of Mode 2A: register AOI from SHP file
def mode2_menu(
    conn: psycopg.Connection,
    app_config: AppConfig,
    mode2_logger: logging.Logger,
) -> None:
    """
    Mode 2 menu loop.
    """
    while True:
        choice = prompt_choice(
            "Mode 2: Register AOI Definition",
            [
                ("shapefile", "Register AOI from Shapefile"),
                ("list", "List existing AOI definitions"),
                ("geopackage_placeholder", "Register AOI from GeoPackage [not implemented yet]"),
                ("return", "Return to main menu"),
            ],
        )

        if choice == "shapefile":
            register_shapefile_aoi(conn, app_config, mode2_logger)

        elif choice == "list":
            list_aoi_definitions(conn, app_config.schema_name)

        elif choice == "geopackage_placeholder":
            print("\nGeoPackage AOI registration is not implemented in this pass.\n")

        elif choice == "return":
            return

# ---------------------------------------------------------------------
# Mode 3 user-facing workflows
# ---------------------------------------------------------------------

#Added with initial implementation of Mode 3A: create tile plan only
def print_mode3a_success_summary(
    computed: Mode3AComputedPlan,
    output_folder: Path,
    inserted_tile_count: int,
    manifest_path: Path | None,
    geopackage_path: Path | None,
) -> None:
    """
    Print a concise success summary after Mode 3A completes.
    """
    print()
    print("=" * 72)
    print("Mode 3A completed")
    print("=" * 72)
    print(f"session_id:                        {computed.session_id}")
    print(f"planned tile rows inserted:         {inserted_tile_count}")
    print(f"computed tile count:                {computed.tile_count}")
    print(f"output folder:                      {output_folder}")

    if manifest_path is not None:
        print(f"manifest-rule.json:                 {manifest_path}")
    else:
        print("manifest-rule.json:                 not generated")

    if geopackage_path is not None:
        print(f"tile_grid.gpkg:                     {geopackage_path}")
    else:
        print("tile_grid.gpkg:                     not generated")

    print("=" * 72)
    print()
    
#Added after initial testing of Mode 3A: create tile plan only
def confirm_mode3a_input_selection(
    run_id: str,
    source: Mode3SourceDataset,
    aoi: Mode3AoiDefinition,
) -> bool:
    """
    Show a short Mode 3A input-selection summary and ask whether to continue.

    This confirms only the selected operation, run_id, Source ID, and AOI ID.
    It runs before compatibility checks, config loading, tile-plan computation,
    database writes, or artifact creation.

    Returns:
        True:
            Continue with Mode 3A.

        False:
            Cancel this Mode 3A attempt and return to the Mode 3 menu.
    """
    print()
    print("=" * 72)
    print("Mode 3A input selections")
    print("=" * 72)
    print(f"Operation:                         {MODE3_OPERATION_CREATE_TILE_PLAN_ONLY}")
    print(f"run_id:                            {run_id}")

    print()
    print(f"Source ID:                         {source.source_dataset_id}")
    print(f"Source name:                       {source.source_name}")
    print(f"Source type:                       {source.source_type}")
    print(f"Source storage mode:               {source.source_storage_mode}")

    print()
    print(f"AOI ID:                            {aoi.aoi_id}")
    print(f"AOI name:                          {aoi.aoi_name}")

    print("=" * 72)

    return prompt_yes_no(
        "Continue with these Mode 3A inputs?",
        default=True,
    )
    
    
    
#Added with initial implementation of Mode 3A: create tile plan only
#Revised after initial testing of Mode 3A
#Important behavior:
#    Database plan inserts happen inside a transaction.
#
#    Artifact writing happens after the database plan exists.
#
#    If artifact writing fails, the run row can be marked failed rather than
#    silently pretending the whole operation succeeded.
def create_tile_plan_only_mode3a(
    conn: psycopg.Connection,
    app_config: AppConfig,
    mode3_logger: logging.Logger,
) -> None:
    """
    Run Mode 3A: create tile plan only.

    This workflow creates a terrain_tile_runs row, populates
    terrain_tile_grid_plan, writes manifest-rule.json if requested, and
    optionally exports tile_grid.gpkg.

    It does not create raster tiles, export RAW files, or generate
    tile-catalog.json.
    """
    mode3_logger.info("Starting Mode 3A: create tile plan only.")

    print()
    print("=" * 72)
    print("Mode 3A: Create Tile Plan Only")
    print("=" * 72)
    print(
        "This operation creates a planned terrain tile grid from a registered "
        "source dataset and registered AOI."
    )
    print("It does not build raster tiles or export RAW files.")
    print()

    run_id = prompt_new_mode3_run_id(
        conn=conn,
        schema_name=app_config.schema_name,
    )

    source_dataset_id = prompt_existing_source_dataset_id_for_mode3(
        conn=conn,
        schema_name=app_config.schema_name,
    )

    aoi_id = prompt_existing_aoi_id_for_mode3(
        conn=conn,
        schema_name=app_config.schema_name,
    )

    source = read_mode3_source_dataset(
        conn=conn,
        schema_name=app_config.schema_name,
        source_dataset_id=source_dataset_id,
    )

    if source is None:
        print(
            f"\nNo source dataset found with "
            f"source_dataset_id={source_dataset_id!r}\n"
        )
        mode3_logger.error(
            "Mode 3A stopped because source_dataset_id was not found: %s",
            source_dataset_id,
        )
        return

    aoi = read_mode3_aoi_definition(
        conn=conn,
        schema_name=app_config.schema_name,
        aoi_id=aoi_id,
    )

    if aoi is None:
        print(f"\nNo AOI found with aoi_id={aoi_id!r}\n")
        mode3_logger.error(
            "Mode 3A stopped because aoi_id was not found: %s",
            aoi_id,
        )
        return

    continue_with_inputs = confirm_mode3a_input_selection(
        run_id=run_id,
        source=source,
        aoi=aoi,
    )

    if not continue_with_inputs:
        print("\nMode 3A input selection cancelled. Returning to Mode 3 menu.\n")
        mode3_logger.info(
            "Mode 3A input selection cancelled before compatibility checks."
        )
        return

    fatal_errors, compatibility_warnings = (
        check_mode3a_source_aoi_compatibility(
            source=source,
            aoi=aoi,
        )
    )

    if fatal_errors:
        print("\nMode 3A cannot continue:")
        for error in fatal_errors:
            print(f"  - {error}")
            mode3_logger.error("Mode 3A compatibility error: %s", error)
        print()
        return

    try:
        settings = load_mode3a_settings_from_config(app_config)
        computed = compute_mode3a_plan(
            conn=conn,
            schema_name=app_config.schema_name,
            run_id=run_id,
            source=source,
            aoi=aoi,
            settings=settings,
        )
    except Exception as error:
        mode3_logger.exception("Mode 3A failed during settings/plan computation.")
        print("\nMode 3A failed while loading settings or computing the plan:")
        print(f"  {error}")
        print()
        return

    while True:
        print_mode3a_confirmation_summary(
            run_id=run_id,
            source=source,
            aoi=aoi,
            settings=settings,
            computed=computed,
            compatibility_warnings=compatibility_warnings,
        )

        choice = prompt_mode3a_summary_choice()

        if choice == "accept":
            break

        if choice == "cancel":
            print("\nMode 3A cancelled. No database records or files were written.\n")
            mode3_logger.info("Mode 3A cancelled before database writes.")
            return

        if choice in {"sampling", "grid", "runtime", "outputs"}:
            print()
            print("Runtime setting overrides are not implemented in this pass.")
            print(
                "To change these settings for now, cancel this run, edit "
                "tool_config.yaml, and run Mode 3A again."
            )
            print()
            continue

        print(f"\nUnrecognized Mode 3A summary choice: {choice!r}\n")

    output_folder = get_mode3a_output_folder(
        settings=settings,
        computed=computed,
    )

    inserted_tile_count = 0
    tile_plan_written = False
    manifest_written = False
    geopackage_written = False
    manifest_path: Path | None = None
    geopackage_path: Path | None = None

    try:
        with conn.transaction():
            insert_mode3a_terrain_tile_run(
                conn=conn,
                schema_name=app_config.schema_name,
                run_id=run_id,
                source=source,
                aoi=aoi,
                settings=settings,
                computed=computed,
            )

            inserted_tile_count = insert_mode3a_tile_grid_plan_rows(
                conn=conn,
                schema_name=app_config.schema_name,
                aoi_id=aoi.aoi_id,
                settings=settings,
                computed=computed,
            )

            if inserted_tile_count != computed.tile_count:
                raise RuntimeError(
                    f"Expected to insert {computed.tile_count} tile-plan rows, "
                    f"but inserted {inserted_tile_count}."
                )

        tile_plan_written = True

        if settings.generate_manifest_rule:
            manifest_rule_dict = build_mode3a_manifest_rule_dict(
                run_id=run_id,
                source=source,
                aoi=aoi,
                settings=settings,
                computed=computed,
            )

            manifest_path = write_mode3a_manifest_rule_json(
                output_folder=output_folder,
                manifest_rule_dict=manifest_rule_dict,
            )
            manifest_written = True

        if settings.export_tile_grid_geopackage:
            geopackage_path = export_mode3a_tile_grid_geopackage(
                conn=conn,
                schema_name=app_config.schema_name,
                session_id=computed.session_id,
                output_folder=output_folder,
            )
            geopackage_written = True

        success_validation_status = (
            "warning"
            if compatibility_warnings or computed.warnings
            else "passed"
        )

        with conn.transaction():
            update_mode3a_run_completion_status(
                conn=conn,
                schema_name=app_config.schema_name,
                session_id=computed.session_id,
                tile_plan_written=tile_plan_written,
                manifest_written=manifest_written,
                geopackage_written=geopackage_written,
                operation_status="completed",
                validation_status=success_validation_status,
                last_error_message=None,
            )

        mode3_logger.info(
            "Mode 3A completed successfully. "
            "session_id=%s, tile_count=%s, validation_status=%s",
            computed.session_id,
            computed.tile_count,
            success_validation_status,
        )

        print_mode3a_success_summary(
            computed=computed,
            output_folder=output_folder,
            inserted_tile_count=inserted_tile_count,
            manifest_path=manifest_path,
            geopackage_path=geopackage_path,
        )

    except Exception as error:
        mode3_logger.exception("Mode 3A failed during database/artifact writes.")

        print("\nMode 3A failed during database or artifact writing:")
        print(f"  {error}")
        print()

        if tile_plan_written:
            try:
                with conn.transaction():
                    update_mode3a_run_completion_status(
                        conn=conn,
                        schema_name=app_config.schema_name,
                        session_id=computed.session_id,
                        tile_plan_written=tile_plan_written,
                        manifest_written=manifest_written,
                        geopackage_written=geopackage_written,
                        operation_status="failed",
                        validation_status="failed",
                        last_error_message=str(error),
                    )
            except Exception:
                mode3_logger.exception(
                    "Failed to update Mode 3A run status after failure."
                )

        return

#Added with initial implementation of Mode 3A: create tile plan only
def mode3_menu(
    conn: psycopg.Connection,
    app_config: AppConfig,
    mode3_logger: logging.Logger,
) -> None:
    """
    Show the Mode 3 terrain package operations menu.

    Only Mode 3A is implemented in this pass. Later branches are shown as
    placeholders so the menu reflects the intended workflow structure.
    """
    while True:
        choice = prompt_choice(
            "Mode 3: Terrain Package Operations",
            [
                (
                    "create_tile_plan_only",
                    "Create tile plan only",
                ),
                (
                    "create_plan_and_build_raster_tiles",
                    "Create tile plan and build raster tiles [not implemented yet]",
                ),
                (
                    "build_raster_tiles_from_existing_plan",
                    "Use existing tile plan to build raster tiles [not implemented yet]",
                ),
                (
                    "export_raw_from_stored_rasters",
                    "Export RAW files from stored raster tiles [not implemented yet]",
                ),
                (
                    "validate_or_reexport_from_manifest",
                    "Validate or re-export from manifest-rule.json [not implemented yet]",
                ),
                (
                    "return",
                    "Return to main menu",
                ),
            ],
        )

        if choice == "create_tile_plan_only":
            create_tile_plan_only_mode3a(
                conn=conn,
                app_config=app_config,
                mode3_logger=mode3_logger,
            )

        elif choice == "return":
            return

        else:
            print()
            print("That Mode 3 branch is not implemented in this pass.")
            print()



# ---------------------------------------------------------------------
# General user-facing workflows
# ---------------------------------------------------------------------


def main_menu(
    conn: psycopg.Connection,
    app_config: AppConfig,
    general_logger: logging.Logger,
    mode1_logger: logging.Logger,
    mode2_logger: logging.Logger,
    mode3_logger: logging.Logger,
) -> None:
    """
    Main tool menu loop.
    """
    while True:
        choice = prompt_choice(
            "GEOG670 Terrain Tool Main Menu",
            [
                ("mode1", "Mode 1: Register Source Raster Dataset"),
                ("mode2", "Mode 2: Register AOI Definition"),
                ("mode3", "Mode 3: Terrain Package Operations"),
                ("quit", "Quit"),
            ],
        )

        #if user chooses mode1, check for tables first   
        if choice == "mode1":
            try:
                check_required_tables(
                    conn=conn,
                    schema_name=app_config.schema_name,
                    required_tables=REQUIRED_MODE1_TABLES,
                    context_label="Mode 1 raster registration",
                )
            except RuntimeError as error:
                general_logger.error("%s", error)
                print(f"\n{error}\n")
                continue

            mode1_menu(conn, app_config, mode1_logger)
   
        elif choice == "mode2":
            try:
                check_required_tables(
                    conn=conn,
                    schema_name=app_config.schema_name,
                    required_tables=REQUIRED_MODE2_TABLES,
                    context_label="Mode 2 AOI registration",
                )
            except RuntimeError as error:
                general_logger.error("%s", error)
                print(f"\n{error}\n")
                continue

            mode2_menu(conn, app_config, mode2_logger)

        elif choice == "mode3":
                check_required_tables(
                    conn=conn,
                    schema_name=app_config.schema_name,
                    required_tables=REQUIRED_FOR_MODE3A,
                    context_label="Mode 3A terrain tile planning",
                )

                mode3_menu(conn, app_config, mode3_logger)

        elif choice == "quit":
            general_logger.info("User exited terrain_tool.py.")
            print("\nGoodbye.\n")
            return


# ---------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------


def main() -> None:
    """
    Main entry point.
    """
    try:
        app_config = load_app_config()
        general_logger, mode1_logger, mode2_logger, mode3_logger = configure_logging(app_config)

        general_logger.info("Starting terrain_tool.py.")
        general_logger.info("terrain_tool.py internal script version: %s", TERRAIN_TOOL_SCRIPT_VERSION)
        general_logger.info("Project root: %s", app_config.project_root)
        general_logger.info("Using database config: %s", app_config.database_config_path)
        if app_config.tool_config_path is not None:
            general_logger.info("Using tool config: %s", app_config.tool_config_path)
        else:
            general_logger.warning("tool_config.yaml not found. Using internal defaults where needed.")

        connection_info = build_connection_info(app_config.database_config)

        with psycopg.connect(**connection_info, autocommit=True) as conn:
            run_startup_readiness_check(conn, app_config, general_logger)
            main_menu(
                conn, 
                app_config, 
                general_logger, 
                mode1_logger, 
                mode2_logger,
                mode3_logger
                )

    except KeyboardInterrupt:
        print("\nInterrupted by user.\n")
        sys.exit(130)

    except Exception as error:
        print("\nterrain_tool.py failed before the main menu could continue.")
        print(error)
        sys.exit(1)


if __name__ == "__main__":
    main()
