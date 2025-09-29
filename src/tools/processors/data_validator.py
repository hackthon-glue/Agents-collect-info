"""
Data validation tool for Strands Data Pipeline

Validates JSON data against predefined schemas for news, weather, and social media data.
"""

from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
import re
import json
import os

from ..utilities.data_models import ValidationResult, NewsArticle, WeatherData

logger = logging.getLogger(__name__)


class DataValidator:
    """Validates data against predefined schemas for database storage"""

    def __init__(self):
        """Initialize the data validator by loading schemas from JSON files"""
        self.schemas = self._load_schemas()

    def _load_schemas(self) -> Dict[str, Dict[str, Any]]:
        """Load all schemas from the 'config/schemas' directory"""
        schemas = {}
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        )
        schema_dir = os.path.join(project_root, "config", "schemas")
        for filename in os.listdir(schema_dir):
            if filename.endswith(".json"):
                schema_name = filename.replace("_schema.json", "")
                with open(os.path.join(schema_dir, filename), "r") as f:
                    schemas[schema_name] = json.load(f)
        return schemas

    def validate_data(
        self, data: List[Dict[str, Any]], schema_type: str
    ) -> ValidationResult:
        """
        Validate data against specified schema type

        Args:
            data: List of data objects to validate
            schema_type: Schema type (news, weather, social_media)

        Returns:
            ValidationResult with validation status and error details
        """
        if schema_type not in self.schemas:
            return ValidationResult(
                is_valid=False, errors=[f"Unknown schema type: {schema_type}"]
            )

        schema = self.schemas[schema_type]
        errors = []
        warnings = []

        for i, item in enumerate(data):
            item_errors, item_warnings = self._validate_item(item, schema, i)
            errors.extend(item_errors)
            warnings.extend(item_warnings)

        is_valid = len(errors) == 0

        logger.info(
            f"Validated {len(data)} {schema_type} items: {len(errors)} errors, {len(warnings)} warnings"
        )

        return ValidationResult(is_valid=is_valid, errors=errors, warnings=warnings)

    def _validate_item(
        self, item: Dict[str, Any], schema: Dict[str, Any], index: int
    ) -> tuple[List[str], List[str]]:
        """Validate a single data item against schema"""
        errors = []
        warnings = []

        # Check required fields
        for field in schema.get("required", []):
            if field not in item:
                errors.append(f"Item {index}: Missing required field '{field}'")
            elif item[field] is None or (
                isinstance(item[field], str) and not item[field].strip()
            ):
                errors.append(f"Item {index}: Required field '{field}' is empty")

        # Check field types and constraints
        for field, constraints in schema.get("fields", {}).items():
            if field in item and item[field] is not None:
                field_errors, field_warnings = self._validate_field(
                    item[field], field, constraints, index
                )
                errors.extend(field_errors)
                warnings.extend(field_warnings)

        return errors, warnings

    def _validate_field(
        self, value: Any, field_name: str, constraints: Dict[str, Any], index: int
    ) -> tuple[List[str], List[str]]:
        """Validate a single field against its constraints"""
        errors = []
        warnings = []

        # Type validation
        expected_type_str = constraints.get("type")
        if expected_type_str:
            type_map = {
                "string": str,
                "integer": int,
                "number": (int, float),
                "dict": dict,
            }
            expected_type = type_map.get(expected_type_str)
            if expected_type and not isinstance(value, expected_type):
                errors.append(
                    f"Item {index}: Field '{field_name}' should be {expected_type_str}, got {type(value).__name__}"
                )
                return errors, warnings

        # String validations
        if isinstance(value, str):
            if "min_length" in constraints and len(value) < constraints["min_length"]:
                errors.append(
                    f"Item {index}: Field '{field_name}' too short (min: {constraints['min_length']})"
                )

            if "max_length" in constraints and len(value) > constraints["max_length"]:
                if field_name in ["summary", "description"]:
                    warnings.append(
                        f"Item {index}: Field '{field_name}' too long (max: {constraints['max_length']})"
                    )
                else:
                    errors.append(
                        f"Item {index}: Field '{field_name}' too long (max: {constraints['max_length']})"
                    )

            if "pattern" in constraints and not re.match(constraints["pattern"], value):
                errors.append(
                    f"Item {index}: Field '{field_name}' doesn't match required pattern"
                )

        # Numeric validations
        if isinstance(value, (int, float)):
            if "min_value" in constraints and value < constraints["min_value"]:
                errors.append(
                    f"Item {index}: Field '{field_name}' below minimum ({constraints['min_value']})"
                )

            if "max_value" in constraints and value > constraints["max_value"]:
                # Critical fields should generate errors, not warnings
                if field_name in ["temperature", "humidity", "latitude", "longitude"]:
                    errors.append(
                        f"Item {index}: Field '{field_name}' above maximum ({constraints['max_value']})"
                    )
                else:
                    warnings.append(
                        f"Item {index}: Field '{field_name}' above maximum ({constraints['max_value']})"
                    )

        return errors, warnings
