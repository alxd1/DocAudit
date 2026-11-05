from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class RecognitionStatus(str, Enum):
    GOOD = "Good"
    NORMAL = "Normal"
    WARNING = "Warning"
    CRITICAL = "Critical"
    FATAL = "Fatal"


class RuleType(str, Enum):
    EXACT = "exact"
    REGEX = "regex"


@dataclass
class RecognitionRule:
    value: str
    rule_type: RuleType
    status: RecognitionStatus
    comment: str = ""
    line: int | None = None
    priority: int = 0

@dataclass
class RecognitionValue:
    name: str
    rules: list[RecognitionRule] = field(default_factory=list)
    source: Path | None = None


@dataclass
class RecognitionClass:
    name: str
    values: list[RecognitionValue] = field(default_factory=list)
    source: Path | None = None
    processor: Callable[["RecognitionResult"], "RecognitionResult"] | None = None


@dataclass
class RecognitionResult:
    hyperclass: str
    base_value: str
    initial_text: str
    processed_text: str
    status: RecognitionStatus
    comment: str = ""
    index: int | None = None
    reg_value: str | None = None
    reg_span: tuple[int, int] | None = None

    def set_index(self, index: int):
        self.index = index