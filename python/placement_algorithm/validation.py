"""Utilities for validation."""
import jsonschema

from placement_algorithm.logger import LOGGER


class ValidationError(Exception):
    """Validation error."""


def validate_config(config, schema):
    """Raise an exception if the configuration is not valid.

    Args:
        config (dict|None): configuration to be validated.
        schema (dict): json schema.

    Raises:
        ValidationError if the validation failed.
    """
    if config is None:
        LOGGER.error("The configuration cannot be empty.")
        raise ValidationError("Empty configuration")
    cls = jsonschema.validators.validator_for(schema)
    cls.check_schema(schema)
    validator = cls(schema)
    errors = list(validator.iter_errors(config))
    if errors:
        # Log an error message for each error.
        msg = []
        for n, e in enumerate(errors, 1):
            path = ".".join(str(elem) for elem in ["root"] + list(e.absolute_path))
            msg.append(f"{n}: Failed validating {path}: {e.message}")
        msg = "\n".join(msg)
        LOGGER.error("Invalid configuration:\n%s", msg)
        raise ValidationError("Invalid configuration")
