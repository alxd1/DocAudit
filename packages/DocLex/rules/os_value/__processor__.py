
import re

from packages.DocLex.models import RecognitionResult, RecognitionStatus


STATUS_PRIORITY = {
    RecognitionStatus.GOOD: 0,
    RecognitionStatus.NORMAL: 1,
    RecognitionStatus.WARNING: 2,
    RecognitionStatus.CRITICAL: 3,
    RecognitionStatus.FATAL: 4,
}


VERSION_PATTERN = re.compile(
    r"^[\s,;:–—-]*"
    r"(?:(?:версия|версии|вер\.?|v\.?|version|release|релиз)\s*)?"
    r"(?P<version>\d+(?:\.\d+)*)"
    r"(?P<plus>\+)?"
    r"(?=$|[^\w.])"
)


def add_warning(result: RecognitionResult, comment: str) -> None:
    if STATUS_PRIORITY[result.status] < STATUS_PRIORITY[RecognitionStatus.WARNING]:
        result.status = RecognitionStatus.WARNING

    result.comment = "; ".join(filter(None, [result.comment, comment]))


def process(result: RecognitionResult) -> RecognitionResult:
    if result.reg_span is None:
        return result

    remainder = result.processed_text[result.reg_span[1]:]
    match = VERSION_PATTERN.match(remainder)

    if match is None:
        add_warning(result, "Не указана версия операционной системы")
        return result

    version = match.group("version")
    plus = match.group("plus") or ""

    result.base_value = f"{result.base_value} {version}{plus}"

    if plus:
        add_warning(result, "Указана минимальная версия операционной системы")

    return result
