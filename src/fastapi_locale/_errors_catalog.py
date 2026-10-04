"""Built-in validation error templates, keyed on the Pydantic error type (ADR-0006).

The English wording follows pydantic-core, which is MIT licensed. Plural messages are split into
singular and plural templates so each language can apply its own plural rules.
"""

from __future__ import annotations

import functools
import math
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from fastapi_locale._catalog import BUILTIN_DOMAIN
from fastapi_locale._formatting import format_message, placeholders

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Mapping

    from fastapi_locale._translator import Translator

__all__ = ["TEMPLATES", "ErrorLocalizer", "ErrorTemplate", "all_templates"]


@dataclass(frozen=True, slots=True)
class ErrorTemplate:
    """English template for one error type; placeholders are keys of the error's ``ctx``."""

    type: str
    message: str
    plural: str | None = None
    count_key: str | None = None
    # Used instead when the error has no value for one of this template's placeholders.
    fallback: ErrorTemplate | None = None


_ALL = (
    ErrorTemplate("no_such_attribute", "Object has no attribute '{attribute}'"),
    ErrorTemplate("json_invalid", "Invalid JSON: {error}"),
    ErrorTemplate("json_type", "JSON input should be string, bytes or bytearray"),
    ErrorTemplate(
        "needs_python_object",
        "Cannot check `{method_name}` when validating from json, use a JsonOrPython validator instead",
    ),
    ErrorTemplate("recursion_loop", "Recursion error - cyclic reference detected"),
    ErrorTemplate("missing", "Field required"),
    ErrorTemplate("frozen_field", "Field is frozen"),
    ErrorTemplate("frozen_instance", "Instance is frozen"),
    ErrorTemplate("extra_forbidden", "Extra inputs are not permitted"),
    ErrorTemplate("invalid_key", "Keys should be strings"),
    ErrorTemplate("get_attribute_error", "Error extracting attribute: {error}"),
    ErrorTemplate("model_type", "Input should be a valid dictionary or instance of {class_name}"),
    ErrorTemplate(
        "model_attributes_type",
        "Input should be a valid dictionary or object to extract fields from",
    ),
    ErrorTemplate("dataclass_type", "Input should be a dictionary or an instance of {class_name}"),
    ErrorTemplate("dataclass_exact_type", "Input should be an instance of {class_name}"),
    ErrorTemplate(
        "default_factory_not_called",
        "The default factory uses validated data, but at least one validation error occurred",
    ),
    ErrorTemplate("none_required", "Input should be None"),
    ErrorTemplate("greater_than", "Input should be greater than {gt}"),
    ErrorTemplate("greater_than_equal", "Input should be greater than or equal to {ge}"),
    ErrorTemplate("less_than", "Input should be less than {lt}"),
    ErrorTemplate("less_than_equal", "Input should be less than or equal to {le}"),
    ErrorTemplate("multiple_of", "Input should be a multiple of {multiple_of}"),
    ErrorTemplate("finite_number", "Input should be a finite number"),
    ErrorTemplate(
        "too_short",
        "{field_type} should have at least {min_length} item after validation, not {actual_length}",
        plural="{field_type} should have at least {min_length} items after validation, not {actual_length}",
        count_key="min_length",
    ),
    ErrorTemplate(
        "too_long",
        "{field_type} should have at most {max_length} item after validation, not {actual_length}",
        plural="{field_type} should have at most {max_length} items after validation, not {actual_length}",
        count_key="max_length",
        # Pydantic stops reading some inputs at the limit and then reports no actual length.
        fallback=ErrorTemplate(
            "too_long",
            "{field_type} should have at most {max_length} item after validation, not more",
            plural="{field_type} should have at most {max_length} items after validation, not more",
            count_key="max_length",
        ),
    ),
    ErrorTemplate("iterable_type", "Input should be iterable"),
    ErrorTemplate("iteration_error", "Error iterating over object, error: {error}"),
    ErrorTemplate("string_type", "Input should be a valid string"),
    ErrorTemplate(
        "string_sub_type",
        "Input should be a string, not an instance of a subclass of str",
    ),
    ErrorTemplate(
        "string_unicode",
        "Input should be a valid string, unable to parse raw data as a unicode string",
    ),
    ErrorTemplate(
        "string_too_short",
        "String should have at least {min_length} character",
        plural="String should have at least {min_length} characters",
        count_key="min_length",
    ),
    ErrorTemplate(
        "string_too_long",
        "String should have at most {max_length} character",
        plural="String should have at most {max_length} characters",
        count_key="max_length",
    ),
    ErrorTemplate("string_pattern_mismatch", "String should match pattern '{pattern}'"),
    ErrorTemplate("string_not_ascii", "String should contain only ASCII characters"),
    ErrorTemplate("enum", "Input should be {expected}"),
    ErrorTemplate("dict_type", "Input should be a valid dictionary"),
    ErrorTemplate("mapping_type", "Input should be a valid mapping, error: {error}"),
    ErrorTemplate("list_type", "Input should be a valid list"),
    ErrorTemplate("tuple_type", "Input should be a valid tuple"),
    ErrorTemplate("set_type", "Input should be a valid set"),
    ErrorTemplate("set_item_not_hashable", "Set items should be hashable"),
    ErrorTemplate("bool_type", "Input should be a valid boolean"),
    ErrorTemplate("bool_parsing", "Input should be a valid boolean, unable to interpret input"),
    ErrorTemplate("int_type", "Input should be a valid integer"),
    ErrorTemplate(
        "int_parsing",
        "Input should be a valid integer, unable to parse string as an integer",
    ),
    ErrorTemplate(
        "int_parsing_size",
        "Unable to parse input string as an integer, exceeded maximum size",
    ),
    ErrorTemplate(
        "int_from_float",
        "Input should be a valid integer, got a number with a fractional part",
    ),
    ErrorTemplate("float_type", "Input should be a valid number"),
    ErrorTemplate(
        "float_parsing",
        "Input should be a valid number, unable to parse string as a number",
    ),
    ErrorTemplate("bytes_type", "Input should be a valid bytes"),
    ErrorTemplate(
        "bytes_too_short",
        "Data should have at least {min_length} byte",
        plural="Data should have at least {min_length} bytes",
        count_key="min_length",
    ),
    ErrorTemplate(
        "bytes_too_long",
        "Data should have at most {max_length} byte",
        plural="Data should have at most {max_length} bytes",
        count_key="max_length",
    ),
    ErrorTemplate("bytes_invalid_encoding", "Data should be valid {encoding}: {encoding_error}"),
    ErrorTemplate("value_error", "Value error, {error}"),
    ErrorTemplate("assertion_error", "Assertion failed, {error}"),
    ErrorTemplate("literal_error", "Input should be {expected}"),
    ErrorTemplate("missing_sentinel_error", "Input should be the 'MISSING' sentinel"),
    ErrorTemplate("date_type", "Input should be a valid date"),
    ErrorTemplate("date_parsing", "Input should be a valid date in the format YYYY-MM-DD, {error}"),
    ErrorTemplate(
        "date_from_datetime_parsing",
        "Input should be a valid date or datetime, {error}",
    ),
    ErrorTemplate(
        "date_from_datetime_inexact",
        "Datetimes provided to dates should have zero time - e.g. be exact dates",
    ),
    ErrorTemplate("date_past", "Date should be in the past"),
    ErrorTemplate("date_future", "Date should be in the future"),
    ErrorTemplate("time_type", "Input should be a valid time"),
    ErrorTemplate("time_parsing", "Input should be in a valid time format, {error}"),
    ErrorTemplate("datetime_type", "Input should be a valid datetime"),
    ErrorTemplate("datetime_parsing", "Input should be a valid datetime, {error}"),
    ErrorTemplate("datetime_object_invalid", "Invalid datetime object, got {error}"),
    ErrorTemplate(
        "datetime_from_date_parsing",
        "Input should be a valid datetime or date, {error}",
    ),
    ErrorTemplate("datetime_past", "Input should be in the past"),
    ErrorTemplate("datetime_future", "Input should be in the future"),
    ErrorTemplate("timezone_naive", "Input should not have timezone info"),
    ErrorTemplate("timezone_aware", "Input should have timezone info"),
    ErrorTemplate("timezone_offset", "Timezone offset of {tz_expected} required, got {tz_actual}"),
    ErrorTemplate("time_delta_type", "Input should be a valid timedelta"),
    ErrorTemplate("time_delta_parsing", "Input should be a valid timedelta, {error}"),
    ErrorTemplate("frozen_set_type", "Input should be a valid frozenset"),
    ErrorTemplate("is_instance_of", "Input should be an instance of {class}"),
    ErrorTemplate("is_subclass_of", "Input should be a subclass of {class}"),
    ErrorTemplate("callable_type", "Input should be callable"),
    ErrorTemplate(
        "union_tag_invalid",
        "Input tag '{tag}' found using {discriminator} does not match any of the expected tags: {expected_tags}",
    ),
    ErrorTemplate(
        "union_tag_not_found",
        "Unable to extract tag using discriminator {discriminator}",
    ),
    ErrorTemplate("arguments_type", "Arguments must be a tuple, list or a dictionary"),
    ErrorTemplate("missing_argument", "Missing required argument"),
    ErrorTemplate("unexpected_keyword_argument", "Unexpected keyword argument"),
    ErrorTemplate("missing_keyword_only_argument", "Missing required keyword only argument"),
    ErrorTemplate("unexpected_positional_argument", "Unexpected positional argument"),
    ErrorTemplate("missing_positional_only_argument", "Missing required positional only argument"),
    ErrorTemplate("multiple_argument_values", "Got multiple values for argument"),
    ErrorTemplate("url_type", "URL input should be a string or URL"),
    ErrorTemplate("url_parsing", "Input should be a valid URL, {error}"),
    ErrorTemplate("url_syntax_violation", "Input violated strict URL syntax rules, {error}"),
    ErrorTemplate(
        "url_too_long",
        "URL should have at most {max_length} character",
        plural="URL should have at most {max_length} characters",
        count_key="max_length",
    ),
    ErrorTemplate("url_scheme", "URL scheme should be {expected_schemes}"),
    ErrorTemplate("uuid_type", "UUID input should be a string, bytes or UUID object"),
    ErrorTemplate("uuid_parsing", "Input should be a valid UUID, {error}"),
    ErrorTemplate("uuid_version", "UUID version {expected_version} expected"),
    ErrorTemplate(
        "decimal_type",
        "Decimal input should be an integer, float, string or Decimal object",
    ),
    ErrorTemplate("decimal_parsing", "Input should be a valid decimal"),
    ErrorTemplate(
        "decimal_max_digits",
        "Decimal input should have no more than {max_digits} digit in total",
        plural="Decimal input should have no more than {max_digits} digits in total",
        count_key="max_digits",
    ),
    ErrorTemplate(
        "decimal_max_places",
        "Decimal input should have no more than {decimal_places} decimal place",
        plural="Decimal input should have no more than {decimal_places} decimal places",
        count_key="decimal_places",
    ),
    ErrorTemplate(
        "decimal_whole_digits",
        "Decimal input should have no more than {whole_digits} digit before the decimal point",
        plural="Decimal input should have no more than {whole_digits} digits before the decimal point",
        count_key="whole_digits",
    ),
    ErrorTemplate(
        "complex_type",
        "Input should be a valid python complex object, a number, or a valid complex string following the rules at https://docs.python.org/3/library/functions.html#complex",
    ),
    ErrorTemplate(
        "complex_str_parsing",
        "Input should be a valid complex string following the rules at https://docs.python.org/3/library/functions.html#complex",
    ),
)

TEMPLATES: Mapping[str, ErrorTemplate] = {template.type: template for template in _ALL}


def all_templates() -> Iterator[ErrorTemplate]:
    """Yield every template, each followed by its fallbacks."""
    for template in TEMPLATES.values():
        current: ErrorTemplate | None = template
        while current is not None:
            yield current
            current = current.fallback


class ErrorLocalizer:
    """Rewrite the ``msg`` of Pydantic error dictionaries in the active translator's locale."""

    __slots__ = ("_domain", "_templates")

    def __init__(
        self,
        templates: Mapping[str, ErrorTemplate] = TEMPLATES,
        domain: str = BUILTIN_DOMAIN,
    ) -> None:
        self._templates = templates
        self._domain = domain

    def localize(
        self, errors: Iterable[Mapping[str, Any]], translator: Translator
    ) -> list[dict[str, Any]]:
        """Return copies of ``errors`` with ``msg`` translated; other keys are left unchanged."""
        return [self._localize_one(error, translator) for error in errors]

    def _localize_one(self, error: Mapping[str, Any], translator: Translator) -> dict[str, Any]:
        template = self._templates.get(error.get("type", ""))
        values: dict[str, object] = {
            name: _display(value)
            for name, value in (error.get("ctx") or {}).items()
            if value is not None
        }
        while template is not None and not _names(template) <= values.keys():
            template = template.fallback
        if template is None:
            return dict(error)
        count = values.get(template.count_key) if template.count_key else None
        if template.plural is None or not isinstance(count, int) or isinstance(count, bool):
            count = None
        message = template.message
        text = translator._find(
            message, plural=template.plural, n=count, context=template.type, domain=self._domain
        )
        if text is None:
            # Nothing to translate into: Pydantic's own message is the source-language text.
            return dict(error)
        if count is not None:
            values.setdefault("n", count)
        domain = self._domain
        msg = format_message(
            text, values, lambda name: translator._warn_missing(domain, message, name)
        )
        return {**error, "msg": msg}


@functools.cache
def _names(template: ErrorTemplate) -> frozenset[str]:
    """Placeholders a template needs from ``ctx``; ``n`` is supplied by the count itself."""
    names = placeholders(template.message) | placeholders(template.plural or "")
    return names - {"n"} if template.plural is not None else names


def _display(value: object) -> object:
    """Show numbers as Pydantic's messages do: ``2`` rather than ``2.0``, and no exponent."""
    if isinstance(value, float) and math.isfinite(value):
        return str(int(value)) if value.is_integer() else format(Decimal(repr(value)), "f")
    return value
