# -*- coding: utf-8 -*-
"""
Created on Mon May 11 16:35:47 2026

@author: Peter Seabrook with GPT assistance
"""

"""
db_prepare.py

Prepares the PostgreSQL/PostGIS database for the GEOG670 terrain packaging tool.

This script:

1. Reads database connection settings from config/database_config.yaml.
2. Reads optional tool settings from config/tool_config.yaml.
3. Locates db/schema.sql.
4. Connects to the configured PostgreSQL database.
5. Executes schema.sql.
6. Verifies that schema metadata was written.

The database itself should already exist before this script is run.

Recommended use from the project root:

    python db/db_prepare.py
"""

from pathlib import Path
import logging
import os
import sys

import yaml
import psycopg


def get_project_root() -> Path:
    """
    Return the project root.

    This script is expected to live in:

        project_root/db/db_prepare.py

    Therefore the project root is the parent of the db/ folder.
    """
    return Path(__file__).resolve().parents[1]


def configure_logging(project_root: Path) -> logging.Logger:
    """
    Configure console and file logging for database preparation.
    """
    logs_dir = project_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    log_path = logs_dir / "db_prepare.log"

    logger = logging.getLogger("db_prepare")
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


def read_yaml_file(path: Path) -> dict:
    """
    Read a YAML file and return its contents as a dictionary.

    Raises FileNotFoundError if the file is missing.
    Raises ValueError if the file is empty or does not parse to a dictionary.
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

    database_config.yaml should contain something like:

        database:
          password_env_var: "GEOG670_DB_PASSWORD"

    If password_env_var is omitted, this returns None.
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

    connection_info = {
        "host": database_section["host"],
        "port": int(database_section["port"]),
        "dbname": database_section["name"],
        "user": database_section["user"],
        "password": get_database_password(database_config),
        "connect_timeout": int(connection_section.get("connect_timeout_seconds", 10)),
        "application_name": connection_section.get(
            "application_name",
            "geog670_db_prepare",
        ),
    }

    return connection_info


def get_schema_sql_path(project_root: Path, tool_config: dict | None) -> Path:
    """
    Determine the schema.sql path.

    If config/tool_config.yaml exists and has:

        paths:
          schema_sql_path: "db/schema.sql"

    then that path is used.

    Otherwise, default to:

        project_root/db/schema.sql
    """
    default_relative_path = "db/schema.sql"

    if tool_config is not None:
        paths_section = tool_config.get("paths", {})
        relative_path = paths_section.get("schema_sql_path", default_relative_path)
    else:
        relative_path = default_relative_path

    schema_path = project_root / relative_path

    return schema_path.resolve(strict=False)


def read_schema_sql(schema_path: Path) -> str:
    """
    Read schema.sql as UTF-8 text.
    """
    if not schema_path.exists():
        raise FileNotFoundError(f"schema.sql not found: {schema_path}")

    schema_sql = schema_path.read_text(encoding="utf-8")

    if not schema_sql.strip():
        raise ValueError(f"schema.sql is empty: {schema_path}")

    return schema_sql


def execute_schema(connection_info: dict, schema_sql: str, logger: logging.Logger) -> None:
    """
    Execute the schema SQL.

    schema.sql already contains BEGIN and COMMIT, so this connection uses
    autocommit=True to avoid wrapping the script in a second implicit transaction.
    """
    logger.info("Connecting to PostgreSQL database.")
    logger.info("Target database: %s", connection_info["dbname"])
    logger.info("Target host: %s", connection_info["host"])

    with psycopg.connect(**connection_info, autocommit=True) as conn:
        logger.info("Connected successfully.")
        logger.info("Executing schema.sql.")

        with conn.cursor() as cur:
            cur.execute(schema_sql)

        logger.info("schema.sql executed successfully.")


def verify_schema_metadata(connection_info: dict, logger: logging.Logger) -> None:
    """
    Verify that terrain_schema_metadata exists and contains schema_version.
    """
    logger.info("Verifying schema metadata.")

    query = """
        SELECT metadata_value
        FROM terrain_schema_metadata
        WHERE metadata_key = 'schema_version';
    """

    with psycopg.connect(**connection_info) as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            row = cur.fetchone()

    if row is None:
        raise RuntimeError(
            "Schema metadata table exists check failed: schema_version was not found."
        )

    schema_version = row[0]
    logger.info("Database schema version: %s", schema_version)


def main() -> None:
    """
    Main entry point.
    """
    project_root = get_project_root()
    logger = configure_logging(project_root)

    logger.info("Starting database preparation.")
    logger.info("Project root: %s", project_root)

    database_config_path = project_root / "config" / "database_config.yaml"
    tool_config_path = project_root / "config" / "tool_config.yaml"

    try:
        database_config = read_yaml_file(database_config_path)

        if tool_config_path.exists():
            tool_config = read_yaml_file(tool_config_path)
        else:
            tool_config = None
            logger.warning(
                "tool_config.yaml not found. Falling back to default schema path."
            )

        connection_info = build_connection_info(database_config)
        schema_path = get_schema_sql_path(project_root, tool_config)

        logger.info("Using schema SQL file: %s", schema_path)

        schema_sql = read_schema_sql(schema_path)

        execute_schema(connection_info, schema_sql, logger)
        verify_schema_metadata(connection_info, logger)

    except Exception as error:
        logger.error("Database preparation failed.")
        logger.error("%s", error)
        sys.exit(1)

    logger.info("Database preparation completed successfully.")
    print("\nDatabase preparation completed successfully.")
    print("Next recommended step:")
    print("  python db/db_check.py")


if __name__ == "__main__":
    main()