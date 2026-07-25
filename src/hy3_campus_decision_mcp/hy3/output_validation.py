"""在 Provider 输出进入工具信封前进行校验。"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from ..errors import Hy3ProviderError

OutputModelT = TypeVar("OutputModelT", bound=BaseModel)


def validate_provider_output(
    raw_output: Any,
    output_model: type[OutputModelT],
    *,
    allowed_source_ids: Iterable[str] = (),
) -> OutputModelT:
    """校验结构化输出，并将来源 ID 绑定到可信本地证据。"""

    try:
        parsed = output_model.model_validate(raw_output)
    except ValidationError as error:
        raise Hy3ProviderError(
            "hy3_output_invalid",
            "Hy3 returned an invalid structured response.",
        ) from error

    allowed = set(allowed_source_ids)
    source_ids = getattr(parsed, "source_ids", None)
    if source_ids is not None and not set(source_ids).issubset(allowed):
        raise Hy3ProviderError(
            "hy3_source_reference_invalid",
            "Hy3 referenced a source that was not supplied as evidence.",
        )
    return parsed
