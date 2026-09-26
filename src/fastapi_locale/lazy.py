"""Lazy text: a message translated when it is rendered, not when it is defined (ADR-0005)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, final

from fastapi.encoders import ENCODERS_BY_TYPE
from pydantic_core import SchemaSerializer, core_schema

from fastapi_locale._context import get_translator

if TYPE_CHECKING:
    from collections.abc import Mapping

    from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler
    from pydantic.json_schema import JsonSchemaValue

__all__ = ["LazyText", "gettext_lazy", "ngettext_lazy", "npgettext_lazy", "pgettext_lazy"]


@final
class LazyText:
    """A message and its values, translated in the active locale each time it is rendered."""

    __slots__ = ("_context", "_domain", "_message", "_n", "_params", "_plural")

    def __init__(
        self,
        message: str,
        *,
        plural: str | None = None,
        n: int | None = None,
        context: str | None = None,
        domain: str | None = None,
        params: Mapping[str, object] | None = None,
    ) -> None:
        self._message = message
        self._plural = plural
        self._n = n
        self._context = context
        self._domain = domain
        self._params: Mapping[str, object] = dict(params or {})

    @property
    def message(self) -> str:
        """The untranslated message (msgid)."""
        return self._message

    def __str__(self) -> str:
        return get_translator().translate(
            self._message,
            plural=self._plural,
            n=self._n,
            context=self._context,
            domain=self._domain,
            params=self._params,
        )

    def __format__(self, format_spec: str) -> str:
        return format(str(self), format_spec)

    def __repr__(self) -> str:
        return f"LazyText({self._message!r})"

    def _identity(self) -> tuple[object, ...]:
        return (self._message, self._plural, self._n, self._context, self._domain)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, LazyText):
            return NotImplemented
        return self._identity() == other._identity() and self._params == other._params

    def __hash__(self) -> int:
        return hash((self._message, self._plural, self._context, self._domain))

    def __reduce__(self) -> tuple[Any, ...]:
        return (
            _restore,
            (self._message, self._plural, self._n, self._context, self._domain, self._params),
        )

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: object, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.union_schema(
            [core_schema.is_instance_schema(cls), core_schema.str_schema()],
            serialization=core_schema.plain_serializer_function_ser_schema(str, when_used="json"),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        return {"type": "string"}


def _restore(  # noqa: PLR0917 - pickle passes the fields positionally
    message: str,
    plural: str | None,
    n: int | None,
    context: str | None,
    domain: str | None,
    params: Mapping[str, object],
) -> LazyText:
    return LazyText(message, plural=plural, n=n, context=context, domain=domain, params=params)


# jsonable_encoder looks up exact types here; this renders LazyText in dict and list responses.
ENCODERS_BY_TYPE[LazyText] = str
# Pydantic uses this for values it meets in Any or object positions, such as a route annotated
# ``-> dict[str, object]``, which FastAPI serializes with Pydantic directly.
LazyText.__pydantic_serializer__ = SchemaSerializer(  # type: ignore[attr-defined]
    core_schema.any_schema(
        serialization=core_schema.plain_serializer_function_ser_schema(str, when_used="json")
    )
)


def gettext_lazy(message: str, /, **params: object) -> LazyText:
    """Mark a message for translation when it is rendered."""
    return LazyText(message, params=params)


def ngettext_lazy(singular: str, plural: str, n: int, /, **params: object) -> LazyText:
    """Mark a plural message for translation when it is rendered."""
    return LazyText(singular, plural=plural, n=n, params=params)


def pgettext_lazy(context: str, message: str, /, **params: object) -> LazyText:
    """Mark a message with a context for translation when it is rendered."""
    return LazyText(message, context=context, params=params)


def npgettext_lazy(
    context: str, singular: str, plural: str, n: int, /, **params: object
) -> LazyText:
    """Mark a plural message with a context for translation when it is rendered."""
    return LazyText(singular, plural=plural, n=n, context=context, params=params)
