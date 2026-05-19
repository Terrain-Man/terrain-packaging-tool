### 5.2 Appendix B: JSON Artifact Examples

The selected runtime profile is **Unity + ArcGIS Maps SDK for Unity**, but the schema also supports a different engine or profile such as Cesium by changing the runtime profile and filling the transformed `runtime_origin` fields.  note that manifest-rule.json can vary depending on choices made--see bottom.

#### `manifest-rule.json`

the main json demonstrates a workflow from a file or set 

```json
{
  "manifest_type": "terrain_package_manifest_rule",
  "manifest_schema_version": "0.4.0",

  "project_metadata": {
    "project_name": "Temporal_Twin_Proof_of_Concept",
    "export_timestamp_utc": "2026-04-27T22:10:14Z",
    "workflow_version": "1.0",
    "description": "Terrain package generated from georeferenced elevation rasters through a PostgreSQL/PostGIS-centered workflow."
  },

  "database_binding": {
    "database_name": "geog670_terrain_packaging_v1",
    "schema_name": "public",
    "run_id": "yw_2026_04_27_a",
    "session_id": "yw_2026_04_27_a_build_001",
    "derived_from_session_id": null,
    "source_dataset_id": "wales_dtm_1m",
    "aoi_id": "yr_wyddfa_19km_aoi",
    "source_registry_tables": {
      "dataset_table": "source_raster_datasets",
      "file_table": "source_raster_files"
    },
    "run_table": "terrain_tile_runs",
    "tile_plan_table": "terrain_tile_grid_plan",
    "tile_outputs_table": "terrain_tile_grid_outputs",
    "tile_rasters_table": "terrain_tile_grid_rasters"
  },

  "run_stage": {
    "operation": "create_tile_plan_and_build_raster_tiles",
    "operation_label": "Mode 3B (terrain package operations: create tile plan and build raster tiles)",

    "tile_plan_creation_requested": true,
    "tile_plan_creation_completed": true,

    "raster_tile_realization_requested": true,
    "raster_tile_realization_completed": true,

    "derived_raster_storage_requested": false,
    "derived_raster_storage_completed": false,

    "raw_file_export_requested": true,
    "raw_file_export_completed": true,

    "manifest_rule_generation_requested": true,
    "manifest_rule_generation_completed": true,

    "tile_catalog_generation_requested": true,
    "tile_catalog_generation_completed": true,

    "tile_grid_geopackage_export_requested": true,
    "tile_grid_geopackage_export_completed": true,

    "operation_status": "completed",
    "validation_status": "not_checked",
    "failure_reason": null,
    "last_error_message": null
  },

  "source_dataset": {
    "source_dataset_id": "wales_dtm_1m",
    "dataset_name": "Wales DTM 1m",
    "source_type": "DTM",
    "source_storage_mode": "external_files",
    "raster_access_method": "registered_external_files",
    "source_registry_tables": {
      "dataset_table": "source_raster_datasets",
      "file_table": "source_raster_files"
    },
    "registered_source_file_count": 361,
    "required_source_file_count_for_run": 25,
    "source_crs": {
      "authority": "EPSG",
      "wkid": 27700,
      "label": "EPSG:27700",
      "linear_unit": "meter"
    },
    "source_cell_size_meters": 1.0,
    "source_nodata_value": -9999.0,
    "registered_source_extent": {
      "xmin": 250000.0,
      "ymin": 346000.0,
      "xmax": 269000.0,
      "ymax": 365000.0
    },
    "source_access_summary": {
      "required_source_files_checked": true,
      "required_source_files_found": true,
      "required_source_files_readable": true,
      "non_required_registered_files_missing": 0,
      "source_coverage_status": "sufficient"
    },
    "provenance_note": "Source dataset registered in Mode 1 (raster registration). Dataset-level metadata is stored in source_raster_datasets. File-level metadata is stored in source_raster_files. Source raster pixels remain outside PostgreSQL/PostGIS."
  },

  "aoi": {
    "aoi_id": "yr_wyddfa_19km_aoi",
    "name": "Yr_Wyddfa_19km_AOI",
    "working_crs": {
      "authority": "EPSG",
      "wkid": 27700,
      "label": "EPSG:27700",
      "linear_unit": "meter"
    },
    "extent": {
      "xmin": 250000.0,
      "ymin": 346000.0,
      "xmax": 269000.0,
      "ymax": 365000.0
    },
    "width_meters": 19000.0,
    "height_meters": 19000.0,
    "provenance_note": "AOI registered in Mode 2 (AOI registration)."
  },

  "workflow_spatial_reference": {
    "description": "The workflow working CRS is the authoritative coordinate system for source registration, AOI geometry, tile planning, raster realization, and tile extents.",
    "working_crs": {
      "authority": "EPSG",
      "wkid": 27700,
      "label": "EPSG:27700",
      "linear_unit": "meter"
    },
    "terrain_production_crs_matches_source_crs": true,
    "terrain_production_crs_matches_aoi_working_crs": true
  },

  "runtime_georeferencing": {
    "description": "Defines how the finished terrain package describes its placement to the selected engine or geospatial runtime. This does not replace the workflow working CRS as the authority for tile generation.",
    "target_engine": "unity",
    "target_geospatial_runtime": "arcgis_maps_sdk_for_unity",
    "runtime_profile_schema_version": "0.1.0",
    "compatible_runtime_profiles": [
      "unity_arcgis_maps_sdk",
      "unity_cesium"
    ],
    "selected_runtime_profile": {
      "profile_id": "unity_arcgis_maps_sdk",
      "sdk_name": "ArcGIS Maps SDK for Unity",
      "engine_component": "ArcGISLocation",
      "intended_parent_name": "TerrainPackage_Yr_Wyddfa",
      "anchor_corner": "southwest",
      "children_use_engine_local_offsets": true
    },
    "working_crs_origin": {
      "description": "Package origin expressed in the workflow working CRS. This is the authoritative southwest terrain-package anchor.",
      "spatial_reference": {
        "authority": "EPSG",
        "wkid": 27700,
        "label": "EPSG:27700",
        "linear_unit": "meter"
      },
      "x": 250000.0,
      "y": 346000.0,
      "z_meters": 0.0
    },
    "runtime_origin": {
      "description": "Origin values used by the selected runtime profile. For this ArcGIS profile, the runtime origin uses the working CRS directly.",
      "origin_authority": "working_crs_direct",
      "spatial_reference": {
        "authority": "EPSG",
        "wkid": 27700,
        "label": "EPSG:27700",
        "linear_unit": "meter"
      },
      "x": 250000.0,
      "y": 346000.0,
      "z_meters": 0.0,
      "longitude_degrees": null,
      "latitude_degrees": null,
      "ellipsoid_height_meters": null,
      "ecef_x_meters": null,
      "ecef_y_meters": null,
      "ecef_z_meters": null,
      "position_meaning": "Package origin expressed in the workflow working CRS. Child terrain tiles use engine-local offsets from this parent or georeference object."
    },
    "runtime_rotation": {
      "heading_degrees": 0.0,
      "pitch_degrees": 0.0,
      "roll_degrees": 0.0
    },
    "runtime_warnings": []
  },

  "grid_convention": {
    "description": "Defines how database tile rows and columns map to engine-local axes.",
    "grid_origin_corner": "southwest",
    "row_increases_toward": "north",
    "col_increases_toward": "east",
    "engine_x_maps_to": "east",
    "engine_z_maps_to": "north",
    "engine_y_maps_to": "elevation",
    "working_crs_x_maps_to": "east",
    "working_crs_y_maps_to": "north"
  },

  "engine_terrain_rules": {
    "heightmap_resolution": 4097,
    "terrain_intervals_per_side": 4096,
    "tile_size_meters": 4096.0,
    "target_sample_spacing_meters": 1.0,
    "terrain_height_meters": 1200.0,

    "sampling_model": {
      "description": "Explains how GIS raster cells are converted into engine terrain heightmap samples.",
      "source_raster_model": "cell_center",
      "engine_heightmap_model": "vertex_grid",
      "heightmap_samples_per_side": 4097,
      "terrain_intervals_per_side": 4096,
      "target_sample_spacing_meters": 1.0,
      "tile_ground_size_meters": 4096.0,
      "adjacent_tiles_duplicate_border_samples": true,
      "resampling_method": "bilinear"
    },

    "raw_format": {
      "description": "Rules for reading and writing RAW heightmap files for the target engine importer.",
      "file_extension": ".raw",
      "bit_depth": 16,
      "data_type": "uint16",
      "byte_order": "little_endian",
      "byte_order_note": "Little-endian means the least significant byte is written first. This must match the byte order expected by the engine importer.",
      "is_grayscale": true,
      "expected_full_tile_file_size_bytes": 33570818
    },

    "raw_array_orientation": {
      "description": "Defines the sample order inside each RAW file so tiles are not mirrored or flipped on import.",
      "first_sample_corner": "southwest",
      "row_order": "south_to_north",
      "column_order": "west_to_east",
      "engine_flip_vertically_on_import": false
    },

    "vertical_encoding": {
      "description": "Defines how real elevation values are encoded into unsigned 16-bit RAW heightmap values.",
      "encoding_type": "uint16_linear_global",
      "base_elevation_m": 0.0,
      "terrain_height_m": 1200.0,
      "source_min_elevation_m": 0.0,
      "source_max_elevation_m": 1200.0,
      "encoded_min_value": 0,
      "encoded_max_value": 65535,
      "decode_formula": "elevation_m = base_elevation_m + terrain_height_m * encoded_value / 65535"
    },

    "nodata_handling": {
      "description": "Defines how missing elevation values are handled before export. Engine terrain heightmaps cannot contain true NoData cells; every heightmap sample must become a numeric height.",
      "source_nodata_value": -9999.0,
      "inside_source_nodata_strategy": "fail",
      "outside_aoi_padding_strategy": "edge_replicate",
      "outside_source_coverage_strategy": "fail",
      "fallback_fill_value_m": null
    },

    "edge_policy": {
      "description": "Defines how the tile grid is expanded when the AOI does not divide evenly into full engine terrain tiles.",
      "tile_grid_policy": "ceil_to_full_tiles",
      "tile_grid_policy_note": "ceil_to_full_tiles means the grid is rounded upward so the AOI is fully enclosed by whole engine terrain tiles. Edge tiles remain full engine terrain size and may include padded area beyond the AOI.",
      "edge_tiles_remain_full_engine_size": true,
      "padding_allowed_beyond_aoi": true,
      "padding_allowed_beyond_source_coverage": false
    }
  },

  "tile_schema": {
    "rows": 5,
    "cols": 5,
    "tile_count": 25,
    "filename_pattern": "terrain_r{row}_c{col}.raw",
    "tile_id_pattern": "r{row}_c{col}",
    "full_tile_expected_file_size_bytes": 33570818
  },

  "output_artifacts": {
    "output_root_folder": "D:/GIS/terrain_packages/yw_2026_04_27_a/",
    "raw_output_folder": "raw_tiles/",
    "manifest_file": "manifest-rule.json",
    "tile_catalog_file": "tile-catalog.json",
    "tile_grid_geopackage": "tile_grid.gpkg"
  },

  "engine_import_modes": {
    "default_mode": "manifest_rule_plus_tile_catalog",
    "tile_catalog_required_for_import": true,
    "tile_catalog_file": "tile-catalog.json",
    "importer_should_create_runtime_parent_or_georeference": true,
    "importer_should_create_child_terrain_tiles": true,
    "importer_should_apply_engine_local_tile_offsets": true
  },

  "validation_summary": {
    "manifest_matches_database_run": "example_not_checked",
    "tile_plan_exists": true,
    "tile_outputs_exist": true,
    "stored_derived_rasters_exist": false,
    "raw_files_exist": "example_not_checked",
    "raw_file_sizes_valid": "example_not_checked",
    "raw_file_hashes_valid": "example_not_checked",
    "tile_catalog_exists": true,
    "source_rebuild_possible": true,
    "runtime_georeferencing_complete": true
  }
}
```

#### `tile-catalog.json`

```json
{
  "catalog_type": "terrain_tile_catalog",
  "catalog_schema_version": "0.4.0",
  "catalog_is_example": true,

  "database_binding": {
    "run_id": "yw_2026_04_27_a",
    "session_id": "yw_2026_04_27_a_build_001",
    "source_dataset_id": "wales_dtm_1m",
    "aoi_id": "yr_wyddfa_19km_aoi",
    "source_registry_tables": {
      "dataset_table": "source_raster_datasets",
      "file_table": "source_raster_files"
    }
  },

  "manifest_binding": {
    "manifest_file": "manifest-rule.json",
    "manifest_schema_version": "0.4.0"
  },

  "catalog_summary": {
    "description": "Per-tile output catalog used by the engine importer to create terrain tiles, place them using local offsets, and validate exported RAW files.",
    "declared_tile_count": 25,
    "tiles_in_catalog": 25,
    "rows": 5,
    "cols": 5,
    "tile_size_meters": 4096.0,
    "heightmap_resolution": 4097,
    "expected_full_tile_file_size_bytes": 33570818
  },

  "workflow_spatial_reference": {
    "description": "Authoritative CRS for tile extents, tile anchors, and package geometry.",
    "working_crs": {
      "authority": "EPSG",
      "wkid": 27700,
      "label": "EPSG:27700",
      "linear_unit": "meter"
    }
  },

  "runtime_profile": {
    "target_engine": "unity",
    "target_geospatial_runtime": "arcgis_maps_sdk_for_unity",
    "engine_component": "ArcGISLocation",
    "engine_local_offsets_are_relative_to": "runtime_origin"
  },

  "grid_convention": {
    "description": "Defines how tile row and column indices map to engine-local coordinates.",
    "grid_origin_corner": "southwest",
    "row_increases_toward": "north",
    "col_increases_toward": "east",
    "engine_x_maps_to": "east",
    "engine_z_maps_to": "north",
    "engine_y_maps_to": "elevation"
  },

  "shared_engine_terrain_size": {
    "x_meters": 4096.0,
    "y_meters": 1200.0,
    "z_meters": 4096.0
  },

  "raw_format": {
    "file_extension": ".raw",
    "bit_depth": 16,
    "data_type": "uint16",
    "byte_order": "little_endian",
    "expected_full_tile_file_size_bytes": 33570818
  },

  "raw_array_orientation": {
    "first_sample_corner": "southwest",
    "row_order": "south_to_north",
    "column_order": "west_to_east",
    "engine_flip_vertically_on_import": false
  },

  "vertical_encoding": {
    "encoding_type": "uint16_linear_global",
    "base_elevation_m": 0.0,
    "terrain_height_m": 1200.0,
    "encoded_min_value": 0,
    "encoded_max_value": 65535,
    "decode_formula": "elevation_m = base_elevation_m + terrain_height_m * encoded_value / 65535"
  },

  "tiles": [
    {
      "tile_id": "r0_c0",
      "filename": "terrain_r0_c0.raw",
      "relative_path": "raw_tiles/terrain_r0_c0.raw",
      "grid_index": {
        "row": 0,
        "col": 0
      },
      "engine_local_position": {
        "x": 0.0,
        "y": 0.0,
        "z": 0.0
      },
      "engine_terrain_size": {
        "x_meters": 4096.0,
        "y_meters": 1200.0,
        "z_meters": 4096.0
      },
      "working_crs_anchor": {
        "x": 250000.0,
        "y": 346000.0,
        "corner": "southwest"
      },
      "working_crs_extent": {
        "xmin": 250000.0,
        "ymin": 346000.0,
        "xmax": 254096.0,
        "ymax": 350096.0
      },
      "aoi_coverage": {
        "is_full_aoi_tile": true,
        "is_padded_beyond_aoi": false,
        "occupied_width_meters": 4096.0,
        "occupied_height_meters": 4096.0,
        "occupied_fraction": 1.0
      },
      "source_coverage": {
        "has_full_source_coverage": true,
        "contains_source_nodata": false,
        "source_coverage_fraction": 1.0,
        "source_coverage_status": "sufficient"
      },
      "tile_vertical_stats": {
        "tile_min_elevation_m": null,
        "tile_max_elevation_m": null,
        "tile_mean_elevation_m": null
      },
      "validation": {
        "expected_file_size_bytes": 33570818,
        "actual_file_size_bytes": null,
        "sha256": null,
        "file_size_valid": "example_not_checked",
        "hash_valid": "example_not_checked",
        "seam_validation_status": "not_checked"
      },
      "source_contribution": {
        "source_dataset_id": "wales_dtm_1m",
        "source_file_count": null,
        "source_file_ids": []
      },
      "provenance": {
        "tile_plan_id": "yw_2026_04_27_a_build_001_r0_c0",
        "notes": "Full interior tile."
      }
    },
    {
      "tile_id": "r0_c1",
      "filename": "terrain_r0_c1.raw",
      "relative_path": "raw_tiles/terrain_r0_c1.raw",
      "grid_index": {
        "row": 0,
        "col": 1
      },
      "engine_local_position": {
        "x": 4096.0,
        "y": 0.0,
        "z": 0.0
      },
      "engine_terrain_size": {
        "x_meters": 4096.0,
        "y_meters": 1200.0,
        "z_meters": 4096.0
      },
      "working_crs_anchor": {
        "x": 254096.0,
        "y": 346000.0,
        "corner": "southwest"
      },
      "working_crs_extent": {
        "xmin": 254096.0,
        "ymin": 346000.0,
        "xmax": 258192.0,
        "ymax": 350096.0
      },
      "aoi_coverage": {
        "is_full_aoi_tile": true,
        "is_padded_beyond_aoi": false,
        "occupied_width_meters": 4096.0,
        "occupied_height_meters": 4096.0,
        "occupied_fraction": 1.0
      },
      "source_coverage": {
        "has_full_source_coverage": true,
        "contains_source_nodata": false,
        "source_coverage_fraction": 1.0,
        "source_coverage_status": "sufficient"
      },
      "tile_vertical_stats": {
        "tile_min_elevation_m": null,
        "tile_max_elevation_m": null,
        "tile_mean_elevation_m": null
      },
      "validation": {
        "expected_file_size_bytes": 33570818,
        "actual_file_size_bytes": null,
        "sha256": null,
        "file_size_valid": "example_not_checked",
        "hash_valid": "example_not_checked",
        "seam_validation_status": "not_checked"
      },
      "source_contribution": {
        "source_dataset_id": "wales_dtm_1m",
        "source_file_count": null,
        "source_file_ids": []
      },
      "provenance": {
        "tile_plan_id": "yw_2026_04_27_a_build_001_r0_c1",
        "notes": "Full interior tile."
      }
    },
    {
      "tile_id": "r0_c2",
      "filename": "terrain_r0_c2.raw",
      "relative_path": "raw_tiles/terrain_r0_c2.raw",
      "grid_index": {
        "row": 0,
        "col": 2
      },
      "engine_local_position": {
        "x": 8192.0,
        "y": 0.0,
        "z": 0.0
      },
      "engine_terrain_size": {
        "x_meters": 4096.0,
        "y_meters": 1200.0,
        "z_meters": 4096.0
      },
      "working_crs_anchor": {
        "x": 258192.0,
        "y": 346000.0,
        "corner": "southwest"
      },
      "working_crs_extent": {
        "xmin": 258192.0,
        "ymin": 346000.0,
        "xmax": 262288.0,
        "ymax": 350096.0
      },
      "aoi_coverage": {
        "is_full_aoi_tile": true,
        "is_padded_beyond_aoi": false,
        "occupied_width_meters": 4096.0,
        "occupied_height_meters": 4096.0,
        "occupied_fraction": 1.0
      },
      "source_coverage": {
        "has_full_source_coverage": true,
        "contains_source_nodata": false,
        "source_coverage_fraction": 1.0,
        "source_coverage_status": "sufficient"
      },
      "tile_vertical_stats": {
        "tile_min_elevation_m": null,
        "tile_max_elevation_m": null,
        "tile_mean_elevation_m": null
      },
      "validation": {
        "expected_file_size_bytes": 33570818,
        "actual_file_size_bytes": null,
        "sha256": null,
        "file_size_valid": "example_not_checked",
        "hash_valid": "example_not_checked",
        "seam_validation_status": "not_checked"
      },
      "source_contribution": {
        "source_dataset_id": "wales_dtm_1m",
        "source_file_count": null,
        "source_file_ids": []
      },
      "provenance": {
        "tile_plan_id": "yw_2026_04_27_a_build_001_r0_c2",
        "notes": "Full interior tile."
      }
    },
    {
      "tile_id": "r0_c3",
      "filename": "terrain_r0_c3.raw",
      "relative_path": "raw_tiles/terrain_r0_c3.raw",
      "grid_index": {
        "row": 0,
        "col": 3
      },
      "engine_local_position": {
        "x": 12288.0,
        "y": 0.0,
        "z": 0.0
      },
      "engine_terrain_size": {
        "x_meters": 4096.0,
        "y_meters": 1200.0,
        "z_meters": 4096.0
      },
      "working_crs_anchor": {
        "x": 262288.0,
        "y": 346000.0,
        "corner": "southwest"
      },
      "working_crs_extent": {
        "xmin": 262288.0,
        "ymin": 346000.0,
        "xmax": 266384.0,
        "ymax": 350096.0
      },
      "aoi_coverage": {
        "is_full_aoi_tile": true,
        "is_padded_beyond_aoi": false,
        "occupied_width_meters": 4096.0,
        "occupied_height_meters": 4096.0,
        "occupied_fraction": 1.0
      },
      "source_coverage": {
        "has_full_source_coverage": true,
        "contains_source_nodata": false,
        "source_coverage_fraction": 1.0,
        "source_coverage_status": "sufficient"
      },
      "tile_vertical_stats": {
        "tile_min_elevation_m": null,
        "tile_max_elevation_m": null,
        "tile_mean_elevation_m": null
      },
      "validation": {
        "expected_file_size_bytes": 33570818,
        "actual_file_size_bytes": null,
        "sha256": null,
        "file_size_valid": "example_not_checked",
        "hash_valid": "example_not_checked",
        "seam_validation_status": "not_checked"
      },
      "source_contribution": {
        "source_dataset_id": "wales_dtm_1m",
        "source_file_count": null,
        "source_file_ids": []
      },
      "provenance": {
        "tile_plan_id": "yw_2026_04_27_a_build_001_r0_c3",
        "notes": "Full interior tile."
      }
    },
    {
      "tile_id": "r0_c4",
      "filename": "terrain_r0_c4.raw",
      "relative_path": "raw_tiles/terrain_r0_c4.raw",
      "grid_index": {
        "row": 0,
        "col": 4
      },
      "engine_local_position": {
        "x": 16384.0,
        "y": 0.0,
        "z": 0.0
      },
      "engine_terrain_size": {
        "x_meters": 4096.0,
        "y_meters": 1200.0,
        "z_meters": 4096.0
      },
      "working_crs_anchor": {
        "x": 266384.0,
        "y": 346000.0,
        "corner": "southwest"
      },
      "working_crs_extent": {
        "xmin": 266384.0,
        "ymin": 346000.0,
        "xmax": 270480.0,
        "ymax": 350096.0
      },
      "aoi_coverage": {
        "is_full_aoi_tile": false,
        "is_padded_beyond_aoi": true,
        "occupied_width_meters": 2616.0,
        "occupied_height_meters": 4096.0,
        "occupied_fraction": 0.6387
      },
      "source_coverage": {
        "has_full_source_coverage": true,
        "contains_source_nodata": false,
        "source_coverage_fraction": 1.0,
        "source_coverage_status": "sufficient"
      },
      "tile_vertical_stats": {
        "tile_min_elevation_m": null,
        "tile_max_elevation_m": null,
        "tile_mean_elevation_m": null
      },
      "validation": {
        "expected_file_size_bytes": 33570818,
        "actual_file_size_bytes": null,
        "sha256": null,
        "file_size_valid": "example_not_checked",
        "hash_valid": "example_not_checked",
        "seam_validation_status": "not_checked"
      },
      "source_contribution": {
        "source_dataset_id": "wales_dtm_1m",
        "source_file_count": null,
        "source_file_ids": []
      },
      "provenance": {
        "tile_plan_id": "yw_2026_04_27_a_build_001_r0_c4",
        "notes": "East edge tile. Tile remains full engine terrain size; AOI occupies only the western 2616 meters."
      }
    },
    {
      "tile_id": "r1_c0",
      "filename": "terrain_r1_c0.raw",
      "relative_path": "raw_tiles/terrain_r1_c0.raw",
      "grid_index": {
        "row": 1,
        "col": 0
      },
      "engine_local_position": {
        "x": 0.0,
        "y": 0.0,
        "z": 4096.0
      },
      "engine_terrain_size": {
        "x_meters": 4096.0,
        "y_meters": 1200.0,
        "z_meters": 4096.0
      },
      "working_crs_anchor": {
        "x": 250000.0,
        "y": 350096.0,
        "corner": "southwest"
      },
      "working_crs_extent": {
        "xmin": 250000.0,
        "ymin": 350096.0,
        "xmax": 254096.0,
        "ymax": 354192.0
      },
      "aoi_coverage": {
        "is_full_aoi_tile": true,
        "is_padded_beyond_aoi": false,
        "occupied_width_meters": 4096.0,
        "occupied_height_meters": 4096.0,
        "occupied_fraction": 1.0
      },
      "source_coverage": {
        "has_full_source_coverage": true,
        "contains_source_nodata": false,
        "source_coverage_fraction": 1.0,
        "source_coverage_status": "sufficient"
      },
      "tile_vertical_stats": {
        "tile_min_elevation_m": null,
        "tile_max_elevation_m": null,
        "tile_mean_elevation_m": null
      },
      "validation": {
        "expected_file_size_bytes": 33570818,
        "actual_file_size_bytes": null,
        "sha256": null,
        "file_size_valid": "example_not_checked",
        "hash_valid": "example_not_checked",
        "seam_validation_status": "not_checked"
      },
      "source_contribution": {
        "source_dataset_id": "wales_dtm_1m",
        "source_file_count": null,
        "source_file_ids": []
      },
      "provenance": {
        "tile_plan_id": "yw_2026_04_27_a_build_001_r1_c0",
        "notes": "Full interior tile."
      }
    },
    {
      "tile_id": "r1_c1",
      "filename": "terrain_r1_c1.raw",
      "relative_path": "raw_tiles/terrain_r1_c1.raw",
      "grid_index": {
        "row": 1,
        "col": 1
      },
      "engine_local_position": {
        "x": 4096.0,
        "y": 0.0,
        "z": 4096.0
      },
      "engine_terrain_size": {
        "x_meters": 4096.0,
        "y_meters": 1200.0,
        "z_meters": 4096.0
      },
      "working_crs_anchor": {
        "x": 254096.0,
        "y": 350096.0,
        "corner": "southwest"
      },
      "working_crs_extent": {
        "xmin": 254096.0,
        "ymin": 350096.0,
        "xmax": 258192.0,
        "ymax": 354192.0
      },
      "aoi_coverage": {
        "is_full_aoi_tile": true,
        "is_padded_beyond_aoi": false,
        "occupied_width_meters": 4096.0,
        "occupied_height_meters": 4096.0,
        "occupied_fraction": 1.0
      },
      "source_coverage": {
        "has_full_source_coverage": true,
        "contains_source_nodata": false,
        "source_coverage_fraction": 1.0,
        "source_coverage_status": "sufficient"
      },
      "tile_vertical_stats": {
        "tile_min_elevation_m": null,
        "tile_max_elevation_m": null,
        "tile_mean_elevation_m": null
      },
      "validation": {
        "expected_file_size_bytes": 33570818,
        "actual_file_size_bytes": null,
        "sha256": null,
        "file_size_valid": "example_not_checked",
        "hash_valid": "example_not_checked",
        "seam_validation_status": "not_checked"
      },
      "source_contribution": {
        "source_dataset_id": "wales_dtm_1m",
        "source_file_count": null,
        "source_file_ids": []
      },
      "provenance": {
        "tile_plan_id": "yw_2026_04_27_a_build_001_r1_c1",
        "notes": "Full interior tile."
      }
    },
    {
      "tile_id": "r1_c2",
      "filename": "terrain_r1_c2.raw",
      "relative_path": "raw_tiles/terrain_r1_c2.raw",
      "grid_index": {
        "row": 1,
        "col": 2
      },
      "engine_local_position": {
        "x": 8192.0,
        "y": 0.0,
        "z": 4096.0
      },
      "engine_terrain_size": {
        "x_meters": 4096.0,
        "y_meters": 1200.0,
        "z_meters": 4096.0
      },
      "working_crs_anchor": {
        "x": 258192.0,
        "y": 350096.0,
        "corner": "southwest"
      },
      "working_crs_extent": {
        "xmin": 258192.0,
        "ymin": 350096.0,
        "xmax": 262288.0,
        "ymax": 354192.0
      },
      "aoi_coverage": {
        "is_full_aoi_tile": true,
        "is_padded_beyond_aoi": false,
        "occupied_width_meters": 4096.0,
        "occupied_height_meters": 4096.0,
        "occupied_fraction": 1.0
      },
      "source_coverage": {
        "has_full_source_coverage": true,
        "contains_source_nodata": false,
        "source_coverage_fraction": 1.0,
        "source_coverage_status": "sufficient"
      },
      "tile_vertical_stats": {
        "tile_min_elevation_m": null,
        "tile_max_elevation_m": null,
        "tile_mean_elevation_m": null
      },
      "validation": {
        "expected_file_size_bytes": 33570818,
        "actual_file_size_bytes": null,
        "sha256": null,
        "file_size_valid": "example_not_checked",
        "hash_valid": "example_not_checked",
        "seam_validation_status": "not_checked"
      },
      "source_contribution": {
        "source_dataset_id": "wales_dtm_1m",
        "source_file_count": null,
        "source_file_ids": []
      },
      "provenance": {
        "tile_plan_id": "yw_2026_04_27_a_build_001_r1_c2",
        "notes": "Full interior tile."
      }
    },
    {
      "tile_id": "r1_c3",
      "filename": "terrain_r1_c3.raw",
      "relative_path": "raw_tiles/terrain_r1_c3.raw",
      "grid_index": {
        "row": 1,
        "col": 3
      },
      "engine_local_position": {
        "x": 12288.0,
        "y": 0.0,
        "z": 4096.0
      },
      "engine_terrain_size": {
        "x_meters": 4096.0,
        "y_meters": 1200.0,
        "z_meters": 4096.0
      },
      "working_crs_anchor": {
        "x": 262288.0,
        "y": 350096.0,
        "corner": "southwest"
      },
      "working_crs_extent": {
        "xmin": 262288.0,
        "ymin": 350096.0,
        "xmax": 266384.0,
        "ymax": 354192.0
      },
      "aoi_coverage": {
        "is_full_aoi_tile": true,
        "is_padded_beyond_aoi": false,
        "occupied_width_meters": 4096.0,
        "occupied_height_meters": 4096.0,
        "occupied_fraction": 1.0
      },
      "source_coverage": {
        "has_full_source_coverage": true,
        "contains_source_nodata": false,
        "source_coverage_fraction": 1.0,
        "source_coverage_status": "sufficient"
      },
      "tile_vertical_stats": {
        "tile_min_elevation_m": null,
        "tile_max_elevation_m": null,
        "tile_mean_elevation_m": null
      },
      "validation": {
        "expected_file_size_bytes": 33570818,
        "actual_file_size_bytes": null,
        "sha256": null,
        "file_size_valid": "example_not_checked",
        "hash_valid": "example_not_checked",
        "seam_validation_status": "not_checked"
      },
      "source_contribution": {
        "source_dataset_id": "wales_dtm_1m",
        "source_file_count": null,
        "source_file_ids": []
      },
      "provenance": {
        "tile_plan_id": "yw_2026_04_27_a_build_001_r1_c3",
        "notes": "Full interior tile."
      }
    },
    {
      "tile_id": "r1_c4",
      "filename": "terrain_r1_c4.raw",
      "relative_path": "raw_tiles/terrain_r1_c4.raw",
      "grid_index": {
        "row": 1,
        "col": 4
      },
      "engine_local_position": {
        "x": 16384.0,
        "y": 0.0,
        "z": 4096.0
      },
      "engine_terrain_size": {
        "x_meters": 4096.0,
        "y_meters": 1200.0,
        "z_meters": 4096.0
      },
      "working_crs_anchor": {
        "x": 266384.0,
        "y": 350096.0,
        "corner": "southwest"
      },
      "working_crs_extent": {
        "xmin": 266384.0,
        "ymin": 350096.0,
        "xmax": 270480.0,
        "ymax": 354192.0
      },
      "aoi_coverage": {
        "is_full_aoi_tile": false,
        "is_padded_beyond_aoi": true,
        "occupied_width_meters": 2616.0,
        "occupied_height_meters": 4096.0,
        "occupied_fraction": 0.6387
      },
      "source_coverage": {
        "has_full_source_coverage": true,
        "contains_source_nodata": false,
        "source_coverage_fraction": 1.0,
        "source_coverage_status": "sufficient"
      },
      "tile_vertical_stats": {
        "tile_min_elevation_m": null,
        "tile_max_elevation_m": null,
        "tile_mean_elevation_m": null
      },
      "validation": {
        "expected_file_size_bytes": 33570818,
        "actual_file_size_bytes": null,
        "sha256": null,
        "file_size_valid": "example_not_checked",
        "hash_valid": "example_not_checked",
        "seam_validation_status": "not_checked"
      },
      "source_contribution": {
        "source_dataset_id": "wales_dtm_1m",
        "source_file_count": null,
        "source_file_ids": []
      },
      "provenance": {
        "tile_plan_id": "yw_2026_04_27_a_build_001_r1_c4",
        "notes": "East edge tile. Tile remains full engine terrain size; AOI occupies only the western 2616 meters."
      }
    },
    {
      "tile_id": "r2_c0",
      "filename": "terrain_r2_c0.raw",
      "relative_path": "raw_tiles/terrain_r2_c0.raw",
      "grid_index": {
        "row": 2,
        "col": 0
      },
      "engine_local_position": {
        "x": 0.0,
        "y": 0.0,
        "z": 8192.0
      },
      "engine_terrain_size": {
        "x_meters": 4096.0,
        "y_meters": 1200.0,
        "z_meters": 4096.0
      },
      "working_crs_anchor": {
        "x": 250000.0,
        "y": 354192.0,
        "corner": "southwest"
      },
      "working_crs_extent": {
        "xmin": 250000.0,
        "ymin": 354192.0,
        "xmax": 254096.0,
        "ymax": 358288.0
      },
      "aoi_coverage": {
        "is_full_aoi_tile": true,
        "is_padded_beyond_aoi": false,
        "occupied_width_meters": 4096.0,
        "occupied_height_meters": 4096.0,
        "occupied_fraction": 1.0
      },
      "source_coverage": {
        "has_full_source_coverage": true,
        "contains_source_nodata": false,
        "source_coverage_fraction": 1.0,
        "source_coverage_status": "sufficient"
      },
      "tile_vertical_stats": {
        "tile_min_elevation_m": null,
        "tile_max_elevation_m": null,
        "tile_mean_elevation_m": null
      },
      "validation": {
        "expected_file_size_bytes": 33570818,
        "actual_file_size_bytes": null,
        "sha256": null,
        "file_size_valid": "example_not_checked",
        "hash_valid": "example_not_checked",
        "seam_validation_status": "not_checked"
      },
      "source_contribution": {
        "source_dataset_id": "wales_dtm_1m",
        "source_file_count": null,
        "source_file_ids": []
      },
      "provenance": {
        "tile_plan_id": "yw_2026_04_27_a_build_001_r2_c0",
        "notes": "Full interior tile."
      }
    },
    {
      "tile_id": "r2_c1",
      "filename": "terrain_r2_c1.raw",
      "relative_path": "raw_tiles/terrain_r2_c1.raw",
      "grid_index": {
        "row": 2,
        "col": 1
      },
      "engine_local_position": {
        "x": 4096.0,
        "y": 0.0,
        "z": 8192.0
      },
      "engine_terrain_size": {
        "x_meters": 4096.0,
        "y_meters": 1200.0,
        "z_meters": 4096.0
      },
      "working_crs_anchor": {
        "x": 254096.0,
        "y": 354192.0,
        "corner": "southwest"
      },
      "working_crs_extent": {
        "xmin": 254096.0,
        "ymin": 354192.0,
        "xmax": 258192.0,
        "ymax": 358288.0
      },
      "aoi_coverage": {
        "is_full_aoi_tile": true,
        "is_padded_beyond_aoi": false,
        "occupied_width_meters": 4096.0,
        "occupied_height_meters": 4096.0,
        "occupied_fraction": 1.0
      },
      "source_coverage": {
        "has_full_source_coverage": true,
        "contains_source_nodata": false,
        "source_coverage_fraction": 1.0,
        "source_coverage_status": "sufficient"
      },
      "tile_vertical_stats": {
        "tile_min_elevation_m": null,
        "tile_max_elevation_m": null,
        "tile_mean_elevation_m": null
      },
      "validation": {
        "expected_file_size_bytes": 33570818,
        "actual_file_size_bytes": null,
        "sha256": null,
        "file_size_valid": "example_not_checked",
        "hash_valid": "example_not_checked",
        "seam_validation_status": "not_checked"
      },
      "source_contribution": {
        "source_dataset_id": "wales_dtm_1m",
        "source_file_count": null,
        "source_file_ids": []
      },
      "provenance": {
        "tile_plan_id": "yw_2026_04_27_a_build_001_r2_c1",
        "notes": "Full interior tile."
      }
    },
    {
      "tile_id": "r2_c2",
      "filename": "terrain_r2_c2.raw",
      "relative_path": "raw_tiles/terrain_r2_c2.raw",
      "grid_index": {
        "row": 2,
        "col": 2
      },
      "engine_local_position": {
        "x": 8192.0,
        "y": 0.0,
        "z": 8192.0
      },
      "engine_terrain_size": {
        "x_meters": 4096.0,
        "y_meters": 1200.0,
        "z_meters": 4096.0
      },
      "working_crs_anchor": {
        "x": 258192.0,
        "y": 354192.0,
        "corner": "southwest"
      },
      "working_crs_extent": {
        "xmin": 258192.0,
        "ymin": 354192.0,
        "xmax": 262288.0,
        "ymax": 358288.0
      },
      "aoi_coverage": {
        "is_full_aoi_tile": true,
        "is_padded_beyond_aoi": false,
        "occupied_width_meters": 4096.0,
        "occupied_height_meters": 4096.0,
        "occupied_fraction": 1.0
      },
      "source_coverage": {
        "has_full_source_coverage": true,
        "contains_source_nodata": false,
        "source_coverage_fraction": 1.0,
        "source_coverage_status": "sufficient"
      },
      "tile_vertical_stats": {
        "tile_min_elevation_m": null,
        "tile_max_elevation_m": null,
        "tile_mean_elevation_m": null
      },
      "validation": {
        "expected_file_size_bytes": 33570818,
        "actual_file_size_bytes": null,
        "sha256": null,
        "file_size_valid": "example_not_checked",
        "hash_valid": "example_not_checked",
        "seam_validation_status": "not_checked"
      },
      "source_contribution": {
        "source_dataset_id": "wales_dtm_1m",
        "source_file_count": null,
        "source_file_ids": []
      },
      "provenance": {
        "tile_plan_id": "yw_2026_04_27_a_build_001_r2_c2",
        "notes": "Full interior tile."
      }
    },
    {
      "tile_id": "r2_c3",
      "filename": "terrain_r2_c3.raw",
      "relative_path": "raw_tiles/terrain_r2_c3.raw",
      "grid_index": {
        "row": 2,
        "col": 3
      },
      "engine_local_position": {
        "x": 12288.0,
        "y": 0.0,
        "z": 8192.0
      },
      "engine_terrain_size": {
        "x_meters": 4096.0,
        "y_meters": 1200.0,
        "z_meters": 4096.0
      },
      "working_crs_anchor": {
        "x": 262288.0,
        "y": 354192.0,
        "corner": "southwest"
      },
      "working_crs_extent": {
        "xmin": 262288.0,
        "ymin": 354192.0,
        "xmax": 266384.0,
        "ymax": 358288.0
      },
      "aoi_coverage": {
        "is_full_aoi_tile": true,
        "is_padded_beyond_aoi": false,
        "occupied_width_meters": 4096.0,
        "occupied_height_meters": 4096.0,
        "occupied_fraction": 1.0
      },
      "source_coverage": {
        "has_full_source_coverage": true,
        "contains_source_nodata": false,
        "source_coverage_fraction": 1.0,
        "source_coverage_status": "sufficient"
      },
      "tile_vertical_stats": {
        "tile_min_elevation_m": null,
        "tile_max_elevation_m": null,
        "tile_mean_elevation_m": null
      },
      "validation": {
        "expected_file_size_bytes": 33570818,
        "actual_file_size_bytes": null,
        "sha256": null,
        "file_size_valid": "example_not_checked",
        "hash_valid": "example_not_checked",
        "seam_validation_status": "not_checked"
      },
      "source_contribution": {
        "source_dataset_id": "wales_dtm_1m",
        "source_file_count": null,
        "source_file_ids": []
      },
      "provenance": {
        "tile_plan_id": "yw_2026_04_27_a_build_001_r2_c3",
        "notes": "Full interior tile."
      }
    },
    {
      "tile_id": "r2_c4",
      "filename": "terrain_r2_c4.raw",
      "relative_path": "raw_tiles/terrain_r2_c4.raw",
      "grid_index": {
        "row": 2,
        "col": 4
      },
      "engine_local_position": {
        "x": 16384.0,
        "y": 0.0,
        "z": 8192.0
      },
      "engine_terrain_size": {
        "x_meters": 4096.0,
        "y_meters": 1200.0,
        "z_meters": 4096.0
      },
      "working_crs_anchor": {
        "x": 266384.0,
        "y": 354192.0,
        "corner": "southwest"
      },
      "working_crs_extent": {
        "xmin": 266384.0,
        "ymin": 354192.0,
        "xmax": 270480.0,
        "ymax": 358288.0
      },
      "aoi_coverage": {
        "is_full_aoi_tile": false,
        "is_padded_beyond_aoi": true,
        "occupied_width_meters": 2616.0,
        "occupied_height_meters": 4096.0,
        "occupied_fraction": 0.6387
      },
      "source_coverage": {
        "has_full_source_coverage": true,
        "contains_source_nodata": false,
        "source_coverage_fraction": 1.0,
        "source_coverage_status": "sufficient"
      },
      "tile_vertical_stats": {
        "tile_min_elevation_m": null,
        "tile_max_elevation_m": null,
        "tile_mean_elevation_m": null
      },
      "validation": {
        "expected_file_size_bytes": 33570818,
        "actual_file_size_bytes": null,
        "sha256": null,
        "file_size_valid": "example_not_checked",
        "hash_valid": "example_not_checked",
        "seam_validation_status": "not_checked"
      },
      "source_contribution": {
        "source_dataset_id": "wales_dtm_1m",
        "source_file_count": null,
        "source_file_ids": []
      },
      "provenance": {
        "tile_plan_id": "yw_2026_04_27_a_build_001_r2_c4",
        "notes": "East edge tile. Tile remains full engine terrain size; AOI occupies only the western 2616 meters."
      }
    },
    {
      "tile_id": "r3_c0",
      "filename": "terrain_r3_c0.raw",
      "relative_path": "raw_tiles/terrain_r3_c0.raw",
      "grid_index": {
        "row": 3,
        "col": 0
      },
      "engine_local_position": {
        "x": 0.0,
        "y": 0.0,
        "z": 12288.0
      },
      "engine_terrain_size": {
        "x_meters": 4096.0,
        "y_meters": 1200.0,
        "z_meters": 4096.0
      },
      "working_crs_anchor": {
        "x": 250000.0,
        "y": 358288.0,
        "corner": "southwest"
      },
      "working_crs_extent": {
        "xmin": 250000.0,
        "ymin": 358288.0,
        "xmax": 254096.0,
        "ymax": 362384.0
      },
      "aoi_coverage": {
        "is_full_aoi_tile": true,
        "is_padded_beyond_aoi": false,
        "occupied_width_meters": 4096.0,
        "occupied_height_meters": 4096.0,
        "occupied_fraction": 1.0
      },
      "source_coverage": {
        "has_full_source_coverage": true,
        "contains_source_nodata": false,
        "source_coverage_fraction": 1.0,
        "source_coverage_status": "sufficient"
      },
      "tile_vertical_stats": {
        "tile_min_elevation_m": null,
        "tile_max_elevation_m": null,
        "tile_mean_elevation_m": null
      },
      "validation": {
        "expected_file_size_bytes": 33570818,
        "actual_file_size_bytes": null,
        "sha256": null,
        "file_size_valid": "example_not_checked",
        "hash_valid": "example_not_checked",
        "seam_validation_status": "not_checked"
      },
      "source_contribution": {
        "source_dataset_id": "wales_dtm_1m",
        "source_file_count": null,
        "source_file_ids": []
      },
      "provenance": {
        "tile_plan_id": "yw_2026_04_27_a_build_001_r3_c0",
        "notes": "Full interior tile."
      }
    },
    {
      "tile_id": "r3_c1",
      "filename": "terrain_r3_c1.raw",
      "relative_path": "raw_tiles/terrain_r3_c1.raw",
      "grid_index": {
        "row": 3,
        "col": 1
      },
      "engine_local_position": {
        "x": 4096.0,
        "y": 0.0,
        "z": 12288.0
      },
      "engine_terrain_size": {
        "x_meters": 4096.0,
        "y_meters": 1200.0,
        "z_meters": 4096.0
      },
      "working_crs_anchor": {
        "x": 254096.0,
        "y": 358288.0,
        "corner": "southwest"
      },
      "working_crs_extent": {
        "xmin": 254096.0,
        "ymin": 358288.0,
        "xmax": 258192.0,
        "ymax": 362384.0
      },
      "aoi_coverage": {
        "is_full_aoi_tile": true,
        "is_padded_beyond_aoi": false,
        "occupied_width_meters": 4096.0,
        "occupied_height_meters": 4096.0,
        "occupied_fraction": 1.0
      },
      "source_coverage": {
        "has_full_source_coverage": true,
        "contains_source_nodata": false,
        "source_coverage_fraction": 1.0,
        "source_coverage_status": "sufficient"
      },
      "tile_vertical_stats": {
        "tile_min_elevation_m": null,
        "tile_max_elevation_m": null,
        "tile_mean_elevation_m": null
      },
      "validation": {
        "expected_file_size_bytes": 33570818,
        "actual_file_size_bytes": null,
        "sha256": null,
        "file_size_valid": "example_not_checked",
        "hash_valid": "example_not_checked",
        "seam_validation_status": "not_checked"
      },
      "source_contribution": {
        "source_dataset_id": "wales_dtm_1m",
        "source_file_count": null,
        "source_file_ids": []
      },
      "provenance": {
        "tile_plan_id": "yw_2026_04_27_a_build_001_r3_c1",
        "notes": "Full interior tile."
      }
    },
    {
      "tile_id": "r3_c2",
      "filename": "terrain_r3_c2.raw",
      "relative_path": "raw_tiles/terrain_r3_c2.raw",
      "grid_index": {
        "row": 3,
        "col": 2
      },
      "engine_local_position": {
        "x": 8192.0,
        "y": 0.0,
        "z": 12288.0
      },
      "engine_terrain_size": {
        "x_meters": 4096.0,
        "y_meters": 1200.0,
        "z_meters": 4096.0
      },
      "working_crs_anchor": {
        "x": 258192.0,
        "y": 358288.0,
        "corner": "southwest"
      },
      "working_crs_extent": {
        "xmin": 258192.0,
        "ymin": 358288.0,
        "xmax": 262288.0,
        "ymax": 362384.0
      },
      "aoi_coverage": {
        "is_full_aoi_tile": true,
        "is_padded_beyond_aoi": false,
        "occupied_width_meters": 4096.0,
        "occupied_height_meters": 4096.0,
        "occupied_fraction": 1.0
      },
      "source_coverage": {
        "has_full_source_coverage": true,
        "contains_source_nodata": false,
        "source_coverage_fraction": 1.0,
        "source_coverage_status": "sufficient"
      },
      "tile_vertical_stats": {
        "tile_min_elevation_m": null,
        "tile_max_elevation_m": null,
        "tile_mean_elevation_m": null
      },
      "validation": {
        "expected_file_size_bytes": 33570818,
        "actual_file_size_bytes": null,
        "sha256": null,
        "file_size_valid": "example_not_checked",
        "hash_valid": "example_not_checked",
        "seam_validation_status": "not_checked"
      },
      "source_contribution": {
        "source_dataset_id": "wales_dtm_1m",
        "source_file_count": null,
        "source_file_ids": []
      },
      "provenance": {
        "tile_plan_id": "yw_2026_04_27_a_build_001_r3_c2",
        "notes": "Full interior tile."
      }
    },
    {
      "tile_id": "r3_c3",
      "filename": "terrain_r3_c3.raw",
      "relative_path": "raw_tiles/terrain_r3_c3.raw",
      "grid_index": {
        "row": 3,
        "col": 3
      },
      "engine_local_position": {
        "x": 12288.0,
        "y": 0.0,
        "z": 12288.0
      },
      "engine_terrain_size": {
        "x_meters": 4096.0,
        "y_meters": 1200.0,
        "z_meters": 4096.0
      },
      "working_crs_anchor": {
        "x": 262288.0,
        "y": 358288.0,
        "corner": "southwest"
      },
      "working_crs_extent": {
        "xmin": 262288.0,
        "ymin": 358288.0,
        "xmax": 266384.0,
        "ymax": 362384.0
      },
      "aoi_coverage": {
        "is_full_aoi_tile": true,
        "is_padded_beyond_aoi": false,
        "occupied_width_meters": 4096.0,
        "occupied_height_meters": 4096.0,
        "occupied_fraction": 1.0
      },
      "source_coverage": {
        "has_full_source_coverage": true,
        "contains_source_nodata": false,
        "source_coverage_fraction": 1.0,
        "source_coverage_status": "sufficient"
      },
      "tile_vertical_stats": {
        "tile_min_elevation_m": null,
        "tile_max_elevation_m": null,
        "tile_mean_elevation_m": null
      },
      "validation": {
        "expected_file_size_bytes": 33570818,
        "actual_file_size_bytes": null,
        "sha256": null,
        "file_size_valid": "example_not_checked",
        "hash_valid": "example_not_checked",
        "seam_validation_status": "not_checked"
      },
      "source_contribution": {
        "source_dataset_id": "wales_dtm_1m",
        "source_file_count": null,
        "source_file_ids": []
      },
      "provenance": {
        "tile_plan_id": "yw_2026_04_27_a_build_001_r3_c3",
        "notes": "Full interior tile."
      }
    },
    {
      "tile_id": "r3_c4",
      "filename": "terrain_r3_c4.raw",
      "relative_path": "raw_tiles/terrain_r3_c4.raw",
      "grid_index": {
        "row": 3,
        "col": 4
      },
      "engine_local_position": {
        "x": 16384.0,
        "y": 0.0,
        "z": 12288.0
      },
      "engine_terrain_size": {
        "x_meters": 4096.0,
        "y_meters": 1200.0,
        "z_meters": 4096.0
      },
      "working_crs_anchor": {
        "x": 266384.0,
        "y": 358288.0,
        "corner": "southwest"
      },
      "working_crs_extent": {
        "xmin": 266384.0,
        "ymin": 358288.0,
        "xmax": 270480.0,
        "ymax": 362384.0
      },
      "aoi_coverage": {
        "is_full_aoi_tile": false,
        "is_padded_beyond_aoi": true,
        "occupied_width_meters": 2616.0,
        "occupied_height_meters": 4096.0,
        "occupied_fraction": 0.6387
      },
      "source_coverage": {
        "has_full_source_coverage": true,
        "contains_source_nodata": false,
        "source_coverage_fraction": 1.0,
        "source_coverage_status": "sufficient"
      },
      "tile_vertical_stats": {
        "tile_min_elevation_m": null,
        "tile_max_elevation_m": null,
        "tile_mean_elevation_m": null
      },
      "validation": {
        "expected_file_size_bytes": 33570818,
        "actual_file_size_bytes": null,
        "sha256": null,
        "file_size_valid": "example_not_checked",
        "hash_valid": "example_not_checked",
        "seam_validation_status": "not_checked"
      },
      "source_contribution": {
        "source_dataset_id": "wales_dtm_1m",
        "source_file_count": null,
        "source_file_ids": []
      },
      "provenance": {
        "tile_plan_id": "yw_2026_04_27_a_build_001_r3_c4",
        "notes": "East edge tile. Tile remains full engine terrain size; AOI occupies only the western 2616 meters."
      }
    },
    {
      "tile_id": "r4_c0",
      "filename": "terrain_r4_c0.raw",
      "relative_path": "raw_tiles/terrain_r4_c0.raw",
      "grid_index": {
        "row": 4,
        "col": 0
      },
      "engine_local_position": {
        "x": 0.0,
        "y": 0.0,
        "z": 16384.0
      },
      "engine_terrain_size": {
        "x_meters": 4096.0,
        "y_meters": 1200.0,
        "z_meters": 4096.0
      },
      "working_crs_anchor": {
        "x": 250000.0,
        "y": 362384.0,
        "corner": "southwest"
      },
      "working_crs_extent": {
        "xmin": 250000.0,
        "ymin": 362384.0,
        "xmax": 254096.0,
        "ymax": 366480.0
      },
      "aoi_coverage": {
        "is_full_aoi_tile": false,
        "is_padded_beyond_aoi": true,
        "occupied_width_meters": 4096.0,
        "occupied_height_meters": 2616.0,
        "occupied_fraction": 0.6387
      },
      "source_coverage": {
        "has_full_source_coverage": true,
        "contains_source_nodata": false,
        "source_coverage_fraction": 1.0,
        "source_coverage_status": "sufficient"
      },
      "tile_vertical_stats": {
        "tile_min_elevation_m": null,
        "tile_max_elevation_m": null,
        "tile_mean_elevation_m": null
      },
      "validation": {
        "expected_file_size_bytes": 33570818,
        "actual_file_size_bytes": null,
        "sha256": null,
        "file_size_valid": "example_not_checked",
        "hash_valid": "example_not_checked",
        "seam_validation_status": "not_checked"
      },
      "source_contribution": {
        "source_dataset_id": "wales_dtm_1m",
        "source_file_count": null,
        "source_file_ids": []
      },
      "provenance": {
        "tile_plan_id": "yw_2026_04_27_a_build_001_r4_c0",
        "notes": "North edge tile. Tile remains full engine terrain size; AOI occupies only the southern 2616 meters."
      }
    },
    {
      "tile_id": "r4_c1",
      "filename": "terrain_r4_c1.raw",
      "relative_path": "raw_tiles/terrain_r4_c1.raw",
      "grid_index": {
        "row": 4,
        "col": 1
      },
      "engine_local_position": {
        "x": 4096.0,
        "y": 0.0,
        "z": 16384.0
      },
      "engine_terrain_size": {
        "x_meters": 4096.0,
        "y_meters": 1200.0,
        "z_meters": 4096.0
      },
      "working_crs_anchor": {
        "x": 254096.0,
        "y": 362384.0,
        "corner": "southwest"
      },
      "working_crs_extent": {
        "xmin": 254096.0,
        "ymin": 362384.0,
        "xmax": 258192.0,
        "ymax": 366480.0
      },
      "aoi_coverage": {
        "is_full_aoi_tile": false,
        "is_padded_beyond_aoi": true,
        "occupied_width_meters": 4096.0,
        "occupied_height_meters": 2616.0,
        "occupied_fraction": 0.6387
      },
      "source_coverage": {
        "has_full_source_coverage": true,
        "contains_source_nodata": false,
        "source_coverage_fraction": 1.0,
        "source_coverage_status": "sufficient"
      },
      "tile_vertical_stats": {
        "tile_min_elevation_m": null,
        "tile_max_elevation_m": null,
        "tile_mean_elevation_m": null
      },
      "validation": {
        "expected_file_size_bytes": 33570818,
        "actual_file_size_bytes": null,
        "sha256": null,
        "file_size_valid": "example_not_checked",
        "hash_valid": "example_not_checked",
        "seam_validation_status": "not_checked"
      },
      "source_contribution": {
        "source_dataset_id": "wales_dtm_1m",
        "source_file_count": null,
        "source_file_ids": []
      },
      "provenance": {
        "tile_plan_id": "yw_2026_04_27_a_build_001_r4_c1",
        "notes": "North edge tile. Tile remains full engine terrain size; AOI occupies only the southern 2616 meters."
      }
    },
    {
      "tile_id": "r4_c2",
      "filename": "terrain_r4_c2.raw",
      "relative_path": "raw_tiles/terrain_r4_c2.raw",
      "grid_index": {
        "row": 4,
        "col": 2
      },
      "engine_local_position": {
        "x": 8192.0,
        "y": 0.0,
        "z": 16384.0
      },
      "engine_terrain_size": {
        "x_meters": 4096.0,
        "y_meters": 1200.0,
        "z_meters": 4096.0
      },
      "working_crs_anchor": {
        "x": 258192.0,
        "y": 362384.0,
        "corner": "southwest"
      },
      "working_crs_extent": {
        "xmin": 258192.0,
        "ymin": 362384.0,
        "xmax": 262288.0,
        "ymax": 366480.0
      },
      "aoi_coverage": {
        "is_full_aoi_tile": false,
        "is_padded_beyond_aoi": true,
        "occupied_width_meters": 4096.0,
        "occupied_height_meters": 2616.0,
        "occupied_fraction": 0.6387
      },
      "source_coverage": {
        "has_full_source_coverage": true,
        "contains_source_nodata": false,
        "source_coverage_fraction": 1.0,
        "source_coverage_status": "sufficient"
      },
      "tile_vertical_stats": {
        "tile_min_elevation_m": null,
        "tile_max_elevation_m": null,
        "tile_mean_elevation_m": null
      },
      "validation": {
        "expected_file_size_bytes": 33570818,
        "actual_file_size_bytes": null,
        "sha256": null,
        "file_size_valid": "example_not_checked",
        "hash_valid": "example_not_checked",
        "seam_validation_status": "not_checked"
      },
      "source_contribution": {
        "source_dataset_id": "wales_dtm_1m",
        "source_file_count": null,
        "source_file_ids": []
      },
      "provenance": {
        "tile_plan_id": "yw_2026_04_27_a_build_001_r4_c2",
        "notes": "North edge tile. Tile remains full engine terrain size; AOI occupies only the southern 2616 meters."
      }
    },
    {
      "tile_id": "r4_c3",
      "filename": "terrain_r4_c3.raw",
      "relative_path": "raw_tiles/terrain_r4_c3.raw",
      "grid_index": {
        "row": 4,
        "col": 3
      },
      "engine_local_position": {
        "x": 12288.0,
        "y": 0.0,
        "z": 16384.0
      },
      "engine_terrain_size": {
        "x_meters": 4096.0,
        "y_meters": 1200.0,
        "z_meters": 4096.0
      },
      "working_crs_anchor": {
        "x": 262288.0,
        "y": 362384.0,
        "corner": "southwest"
      },
      "working_crs_extent": {
        "xmin": 262288.0,
        "ymin": 362384.0,
        "xmax": 266384.0,
        "ymax": 366480.0
      },
      "aoi_coverage": {
        "is_full_aoi_tile": false,
        "is_padded_beyond_aoi": true,
        "occupied_width_meters": 4096.0,
        "occupied_height_meters": 2616.0,
        "occupied_fraction": 0.6387
      },
      "source_coverage": {
        "has_full_source_coverage": true,
        "contains_source_nodata": false,
        "source_coverage_fraction": 1.0,
        "source_coverage_status": "sufficient"
      },
      "tile_vertical_stats": {
        "tile_min_elevation_m": null,
        "tile_max_elevation_m": null,
        "tile_mean_elevation_m": null
      },
      "validation": {
        "expected_file_size_bytes": 33570818,
        "actual_file_size_bytes": null,
        "sha256": null,
        "file_size_valid": "example_not_checked",
        "hash_valid": "example_not_checked",
        "seam_validation_status": "not_checked"
      },
      "source_contribution": {
        "source_dataset_id": "wales_dtm_1m",
        "source_file_count": null,
        "source_file_ids": []
      },
      "provenance": {
        "tile_plan_id": "yw_2026_04_27_a_build_001_r4_c3",
        "notes": "North edge tile. Tile remains full engine terrain size; AOI occupies only the southern 2616 meters."
      }
    },
    {
      "tile_id": "r4_c4",
      "filename": "terrain_r4_c4.raw",
      "relative_path": "raw_tiles/terrain_r4_c4.raw",
      "grid_index": {
        "row": 4,
        "col": 4
      },
      "engine_local_position": {
        "x": 16384.0,
        "y": 0.0,
        "z": 16384.0
      },
      "engine_terrain_size": {
        "x_meters": 4096.0,
        "y_meters": 1200.0,
        "z_meters": 4096.0
      },
      "working_crs_anchor": {
        "x": 266384.0,
        "y": 362384.0,
        "corner": "southwest"
      },
      "working_crs_extent": {
        "xmin": 266384.0,
        "ymin": 362384.0,
        "xmax": 270480.0,
        "ymax": 366480.0
      },
      "aoi_coverage": {
        "is_full_aoi_tile": false,
        "is_padded_beyond_aoi": true,
        "occupied_width_meters": 2616.0,
        "occupied_height_meters": 2616.0,
        "occupied_fraction": 0.4079
      },
      "source_coverage": {
        "has_full_source_coverage": true,
        "contains_source_nodata": false,
        "source_coverage_fraction": 1.0,
        "source_coverage_status": "sufficient"
      },
      "tile_vertical_stats": {
        "tile_min_elevation_m": null,
        "tile_max_elevation_m": null,
        "tile_mean_elevation_m": null
      },
      "validation": {
        "expected_file_size_bytes": 33570818,
        "actual_file_size_bytes": null,
        "sha256": null,
        "file_size_valid": "example_not_checked",
        "hash_valid": "example_not_checked",
        "seam_validation_status": "not_checked"
      },
      "source_contribution": {
        "source_dataset_id": "wales_dtm_1m",
        "source_file_count": null,
        "source_file_ids": []
      },
      "provenance": {
        "tile_plan_id": "yw_2026_04_27_a_build_001_r4_c4",
        "notes": "Northeast corner edge tile. Tile remains a full 4096 m engine terrain tile. AOI occupies only the southwest 2616 m by 2616 m portion; the remainder is padded according to the manifest edge policy."
      }
    }
  ]
}
```

---
If a VRT is chosen then the `source_dataset` section in manifest-rule.json will look like this (an additional subsection is added):

```json
"source_dataset": {
  "source_dataset_id": "wales_dtm_1m_vrt",
  "dataset_name": "Wales DTM 1m Virtual Mosaic",
  "source_type": "DTM",
  "source_storage_mode": "virtual_mosaic",
  "raster_access_method": "registered_virtual_mosaic",
  "source_registry_tables": {
    "dataset_table": "source_raster_datasets",
    "file_table": "source_raster_files"
  },
  "registered_source_file_count": 361,
  "required_source_file_count_for_run": 25,
  "source_crs": {
    "authority": "EPSG",
    "wkid": 27700,
    "label": "EPSG:27700",
    "linear_unit": "meter"
  },
  "source_cell_size_meters": 1.0,
  "source_nodata_value": -9999.0,
  "registered_source_extent": {
    "xmin": 250000.0,
    "ymin": 346000.0,
    "xmax": 269000.0,
    "ymax": 365000.0
  },
  "virtual_mosaic": {
    "vrt_path": "D:/GIS/Eryri/DTM/virtual_mosaics/wales_dtm_1m.vrt",
    "vrt_origin": "created_by_mode1",
    "vrt_source_files_recorded_in": "source_raster_files",
    "vrt_is_primary_raster_access_surface": true
  },
  "source_access_summary": {
    "vrt_checked": true,
    "vrt_found": true,
    "vrt_readable": true,
    "vrt_referenced_source_files_checked": true,
    "required_source_files_checked": true,
    "required_source_files_found": true,
    "required_source_files_readable": true,
    "non_required_registered_files_missing": 0,
    "source_coverage_status": "sufficient"
  },
  "provenance_note": "Source dataset registered in Mode 1 (raster registration) as a virtual mosaic. Dataset-level metadata, including the registered VRT path and VRT origin, is stored in source_raster_datasets. File-level metadata for the original source rasters referenced by the VRT is stored in source_raster_files. Source raster pixels remain outside PostgreSQL/PostGIS."
}
```


But **`virtual_mosaic` is not the only possible source-related condition that could add a whole subsection inside `source_dataset`**.

But for the current first-version design, setting aside engine/runtime differences, there are only **two source-storage cases** that justify that kind of structural addition:

```text
virtual_mosaic
postgis_raster
```

### Why `virtual_mosaic` gets a subsection

`virtual_mosaic` has dataset-level access metadata that does not exist for ordinary `external_files`: the VRT is the primary raster access surface, and it may be created by Mode 1 or supplied by the user. The planning docs already distinguish this: for `virtual_mosaic`, Mode 1 records one dataset row, one row per original source file, and dataset-level VRT path or VRT metadata. 

So this is justified:

```json
"virtual_mosaic": {
  "vrt_path": "...",
  "vrt_origin": "created_by_mode1",
  "vrt_source_files_recorded_in": "source_raster_files",
  "vrt_is_primary_raster_access_surface": true
}
```

### The other possible case: `postgis_raster`

If `postgis_raster` is later implemented, it would probably also deserve a nested subsection, because its source access model is meaningfully different: Mode 3 reads source elevation values from PostGIS raster records rather than from external files. The docs describe `postgis_raster` as source pixels loaded into PostGIS, with optional file provenance rows if originally loaded from files. 

That might look like:

```json
"postgis_raster": {
  "source_payload_table": "source_raster_payloads",
  "source_payload_count": 1,
  "source_pixels_stored_in_postgis": true,
  "file_provenance_recorded_in": "source_raster_files"
}
```

But since we are deferring `postgis_raster`, this should be treated as future design, not part of the immediate manifest example.

### What should **not** get a new subsection

For `external_file` and `external_files`, I would **not** add a special nested subsection. Their access model is already expressed cleanly by:

```json
"source_storage_mode": "external_files",
"raster_access_method": "registered_external_files",
"source_registry_tables": {
  "dataset_table": "source_raster_datasets",
  "file_table": "source_raster_files"
}
```

The physical file registry belongs in `source_raster_files`; the docs explicitly define `source_raster_files` as one row per registered physical source raster file, including for `external_file`, `external_files`, and `virtual_mosaic`. 

### Clean rule

Use a nested subsection inside `source_dataset` only when the selected `source_storage_mode` has **additional dataset-level access facts** beyond the common source fields.

For v1:

```text
external_file       → no special subsection
external_files      → no special subsection
virtual_mosaic      → add "virtual_mosaic"
postgis_raster      → future "postgis_raster" subsection, if implemented
```

Other manifest sections can still vary by Mode 3 operation, requested/completed stages, validation results, and stored/exported artifact state, but those should change field values or summaries rather than radically changing the `source_dataset` structure.
