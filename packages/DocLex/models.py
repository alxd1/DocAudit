from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class RecognitionStatus(str, Enum):
    GOOD = "Good"
    NORMAL = "Normal"
    WARNING = "Warning"
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


@dataclass
class RecognitionResult:
    hyperclass: str
    base_value: str
    value: str
    status: RecognitionStatus
    comment: str = ""