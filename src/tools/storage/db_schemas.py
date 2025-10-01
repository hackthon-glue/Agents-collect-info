"""
Database schema definitions for Aurora PostgreSQL

Contains table schemas and field mappings for generating dynamic queries.
"""

import json
import os
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class TableSchema:
    """Database table schema definition"""

    table_name: str
    columns: List[str]
    conflict_column: str = None


# Todo: Refactor to write cleaner code as integrate similar configs
# Schema file to table mapping
SCHEMA_MAPPINGS = {
    "news": {
        "file": "news_schema.json",
        "table": "public.insights_countrynewsitem",
        "field_mapping": {
            "publishedAt": "published_at",
            "collectAt": "collected_at",
            "sourceType": "source_type",
            "summary": "description",
        },
        "conflict_column": "url",
    },
    "weather": {
        "file": "weather_schema.json",
        "table": "public.insights_countryweather",
        "field_mapping": {
            "location": "city_name",
            "latitude": "coordinates_lat",
            "longitude": "coordinates_lon",
            "main_weather": "weather_main",
            "description": "weather_description",
            "wind_deg": "wind_direction",
            "clouds": "cloudiness",
            "collectAt": "collected_at",
            "sourceType": "source_type",
        },
    },
    "social_media": {
        "file": "social_media_schema.json",
        "table": "public.insights_countrysocialmedia",
        "field_mapping": {
            "publishedAt": "published_at",
            "collectAt": "collected_at",
            "sourceType": "source_type",
        },
        "conflict_column": "url",
    },
}


def load_schema_from_json(schema_key: str) -> TableSchema:
    """Load schema from JSON file and create TableSchema"""
    config = SCHEMA_MAPPINGS[schema_key]
    schema_path = os.path.join(
        os.path.dirname(__file__), "../../../config/schemas", config["file"]
    )

    with open(schema_path, "r") as f:
        schema_data = json.load(f)

    # Extract columns from schema fields
    columns = ["country_id"]  # Always include country_id
    field_mapping = config.get("field_mapping", {})

    for field_name in schema_data["fields"].keys():
        if field_name == "country":  # Skip country as it maps to country_id
            continue
        db_column = field_mapping.get(field_name, field_name)
        columns.append(db_column)

    # Add standard columns
    columns.extend(["raw_response"])

    return TableSchema(
        table_name=config["table"],
        columns=columns,
        conflict_column=config.get("conflict_column"),
    )


def build_insert_query(schema_key: str) -> str:
    """Build INSERT query from JSON schema definition"""
    schema = load_schema_from_json(schema_key)
    placeholders = ", ".join(["%s"] * len(schema.columns))
    columns_str = ", ".join(schema.columns)

    query = f"""
    INSERT INTO {schema.table_name} (
        {columns_str}
    ) VALUES ({placeholders})
    """

    if schema.conflict_column:
        query += f"ON CONFLICT ({schema.conflict_column}) DO NOTHING"

    return query
