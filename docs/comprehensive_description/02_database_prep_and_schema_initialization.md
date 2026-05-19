## 3. Database Preparation and Schema Initialization

Before Modes 1–3 can run, the PostgreSQL/PostGIS database must be prepared with the required extensions, tables, indexes, constraints, and schema metadata.

This should be treated as a one-time setup or maintenance operation, not as one of the three workflow modes.

Modes 1–3 assume that the database schema already exists.

The recommended structure is:

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
```

#### `schema.sql`

`schema.sql` should be the authoritative schema-definition file.

It should contain the SQL needed to create:

* required PostgreSQL extensions
* required PostGIS extensions
* core workflow tables
* conditional first-version tables, if used
* indexes
* foreign keys
* constraints
* schema/version metadata, if used

At minimum, it should prepare the core first-version tables described in Appendix A.

The database schema should not be created manually through repeated ad hoc pgAdmin actions. Manual inspection in pgAdmin is useful, but the schema itself should be reproducible.

#### `db_prepare.py`

`db_prepare.py` should be the automated database-preparation script.

It should read the database connection settings from:

```text
config/database_config.yaml
```

It should then connect to the project database and execute `schema.sql`.

The script should:

* connect to `geog670_terrain_packaging_v1`
* verify that PostgreSQL/PostGIS are reachable
* create required extensions if they do not already exist
* create required tables if they do not already exist
* create required indexes and constraints
* report whether preparation succeeded
* write preparation results to the tool log

For development, `db_prepare.py` may also support explicit maintenance options such as:

```text
python db/db_prepare.py --check
python db/db_prepare.py --reset-dev
```

A destructive option such as `--reset-dev` should require explicit confirmation.

#### `db_check.py`

`db_check.py` may be a separate validation script or a check mode inside `db_prepare.py`.

Its purpose is to verify that the database is ready for `terrain_tool.py`.

It should check:

* database connection
* PostGIS availability
* PostGIS Raster availability, if raster payload storage is enabled
* required tables
* required columns
* required indexes
* required constraints
* expected schema version, if schema versioning is used

If the database is incomplete, the check should report what is missing and tell the user to run the preparation script.

#### Relationship to `terrain_tool.py`

`terrain_tool.py` should not normally create or modify the database schema during Mode 1, Mode 2, or Mode 3 operations.

Instead:

* `db_prepare.py` prepares the database.
* `db_check.py` verifies readiness.
* `terrain_tool.py` uses the prepared database.

At startup, `terrain_tool.py` should perform a lightweight readiness check. If the schema is missing or incomplete, it should stop with a clear message.

Example:

```text
Database schema not found or incomplete.

Run:
  python db/db_prepare.py

Then restart terrain_tool.py.
```

#### Best rule

**Database preparation is a reproducible setup step. Modes 1–3 are workflow operations that depend on the prepared database.**
