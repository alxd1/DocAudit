from pathlib import Path
import hashlib
import importlib.util
import re

from .models import RecognitionClass, RecognitionRule, RecognitionStatus, RecognitionValue, RuleType
from .configuration import DOC_LEX_DEFAULT_RULE_PRIORITY

class DocLexConfigError(ValueError):
    """Invalid DocLex configuration."""


def _error(path: Path, line: int, message: str) -> DocLexConfigError:
    return DocLexConfigError(f"{path}:{line}: {message}")


def _parse_quoted(text: str, pos: int, path: Path, line: int, raw: bool = False) -> tuple[str, int]:
    if pos >= len(text) or text[pos] != '"':
        raise _error(path, line, 'Expected opening double quote')
    pos += 1
    chars: list[str] = []
    while pos < len(text):
        ch = text[pos]
        if ch == '"':
            return ''.join(chars), pos + 1
        if ch == '\\':
            if pos + 1 >= len(text):
                raise _error(path, line, 'Unfinished escape sequence')
            nxt = text[pos + 1]
            if nxt == '"':
                chars.append('"')
            elif nxt == '\\' and not raw:
                chars.append('\\')
            else:
                chars.append('\\' + nxt)
            pos += 2
            continue
        chars.append(ch)
        pos += 1
    raise _error(path, line, 'Unclosed double-quoted string')


def _parse_rule(text: str, path: Path, line: int) -> RecognitionRule:
    priority, text = _extract_priority(text)
    pos = 0
    is_regex = text.startswith('r"')
    if is_regex:
        pos = 1
    value, pos = _parse_quoted(text, pos, path, line, raw=is_regex)
    if not value:
        raise _error(path, line, 'Empty rule value')
    rest = text[pos:].lstrip()
    if not rest.startswith('|'):
        raise _error(path, line, "Expected '|' after rule value")
    rest = rest[1:].lstrip()
    status_match = re.match(r'([A-Za-z]+)\b', rest)
    if not status_match:
        raise _error(path, line, 'Expected rule status')
    status_text = status_match.group(1)
    try:
        status = RecognitionStatus(status_text)
    except ValueError as exc:
        raise _error(path, line, f'Unknown status {status_text!r}') from exc
    rest = rest[status_match.end():].lstrip()
    comment = ''
    if rest.startswith('|'):
        rest = rest[1:].lstrip()
        comment, pos = _parse_quoted(rest, 0, path, line)
        rest = rest[pos:].lstrip()
    if rest and not rest.startswith('#'):
        raise _error(path, line, f'Unexpected trailing text: {rest!r}')
    if is_regex:
        try:
            re.compile(value, flags=re.IGNORECASE)
        except re.error as exc:
            raise _error(path, line, f'Invalid regex: {exc}') from exc
    return RecognitionRule(value=value, rule_type=RuleType.REGEX if is_regex else RuleType.EXACT,
                           status=status, comment=comment, line=line, priority=priority)


def _parse_header(text: str, path: Path, line: int) -> str:
    match = re.fullmatch(r'\[([^\[\]\r\n]+)\]', text)
    if not match or not match.group(1).strip():
        raise _error(path, line, 'Expected a single [name] header')
    return match.group(1).strip()


def _content_lines(path: Path):
    for line_no, raw in enumerate(path.read_text(encoding='utf-8-sig').splitlines(), 1):
        text = raw.strip()
        if text and not text.startswith('#'):
            yield line_no, text

def _extract_priority(text: str) -> tuple[int, str]:
    text = text.strip()

    match = re.match(r'^(\d+)\s+(?=(?:r)?")', text)

    if match is None:
        return DOC_LEX_DEFAULT_RULE_PRIORITY, text

    priority = int(match.group(1))
    rule_text = text[match.end():].lstrip()

    return priority, rule_text


def load_values(path: Path) -> list[RecognitionValue]:
    values = []
    name = None
    rules = []
    header_line = 0

    for line_no, text in _content_lines(path):
        if text.startswith('['):
            if name is not None:
                if not rules:
                    raise _error(path, header_line, 'No rules for canonical value')

                values.append(RecognitionValue(name=name, rules=rules, source=path))

            name = _parse_header(text, path, line_no)
            rules = []
            header_line = line_no
            continue

        if name is None:
            raise _error(path, line_no, 'Expected [name] header before rules')

        rules.append(_parse_rule(text, path, line_no))

    if name is None:
        raise _error(path, 1, 'Empty .darc file')

    if not rules:
        raise _error(path, header_line, 'No rules for canonical value')

    values.append(RecognitionValue(name=name, rules=rules, source=path))

    return values


def load_processor(directory: Path, filename: str = "__processor__.py"):
    path = directory / filename

    if not path.is_file():
        return None

    module_name = f"_doclex_processor_{hashlib.sha256(str(path.resolve()).encode()).hexdigest()}"
    spec = importlib.util.spec_from_file_location(module_name, path)

    if spec is None or spec.loader is None:
        raise DocLexConfigError(f"Cannot load processor: {path}")

    module = importlib.util.module_from_spec(spec)

    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise DocLexConfigError(f"Error loading processor {path}: {exc}") from exc

    processor = getattr(module, "process", None)

    if not callable(processor):
        raise DocLexConfigError(f"Processor {path} must define callable process()")

    return processor


def load_class(directory: Path) -> RecognitionClass:
    class_file = directory / '__class__.dahc'
    if not class_file.is_file():
        raise DocLexConfigError(f'Missing {class_file}')
    lines = list(_content_lines(class_file))
    if len(lines) != 1:
        raise _error(class_file, 1, 'Expected exactly one [ClassName] header')
    name = _parse_header(lines[0][1], class_file, lines[0][0])
    values = [
        value
        for path in sorted(directory.glob('*.darc'))
        for value in load_values(path)
    ]
    seen = set()
    for item in values:
        if item.name.casefold() in seen:
            raise DocLexConfigError(f'Duplicate canonical value {item.name!r} in {directory}')
        seen.add(item.name.casefold())
    return RecognitionClass(name=name, values=values, source=class_file, processor=load_processor(directory))



def load_all_classes(root: str | Path) -> dict[str, RecognitionClass]:
    root = Path(root)

    if not root.is_dir():
        raise DocLexConfigError(
            f"Recognition directory not found: {root}"
        )

    classes: dict[str, RecognitionClass] = {}
    seen_names: set[str] = set()

    for directory in sorted(root.iterdir()):
        if not directory.is_dir() or directory.name == "__pycache__":
            continue

        recognition_class = load_class(directory)

        normalized_name = recognition_class.name.casefold()

        if normalized_name in seen_names:
            raise DocLexConfigError(
                f"Duplicate hyperclass {recognition_class.name!r}"
            )

        seen_names.add(normalized_name)
        classes[recognition_class.name] = recognition_class

    return classes
