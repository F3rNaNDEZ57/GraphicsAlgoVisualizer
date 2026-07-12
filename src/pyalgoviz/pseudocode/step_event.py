from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StepEvent:
    """One visualization action the interpreter performed. Yielded by
    Interpreter.run() so a caller can highlight the source line, log a
    readable trace, or (later) record a replay/export stream."""

    action: str
    args: tuple[Any, ...]
    lineno: int | None
