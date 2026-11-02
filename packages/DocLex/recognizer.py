
import re

from .models import (
    RecognitionClass,
    RecognitionResult,
    RecognitionRule,
    RecognitionStatus,
    RuleType,
)


STATUS_PRIORITY = {
    RecognitionStatus.GOOD: 4,
    RecognitionStatus.NORMAL: 3,
    RecognitionStatus.WARNING: 2,
    RecognitionStatus.FATAL: 1,
}


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def rule_matches(text: str, rule: RecognitionRule) -> bool:
    if rule.rule_type == RuleType.EXACT:
        return normalize(text) == normalize(rule.value)

    if rule.rule_type == RuleType.REGEX:
        return re.fullmatch(
            rule.value,
            text.strip(),
            flags=re.IGNORECASE,
        ) is not None

    return False

def get_base_value(
    text: str,
    rule: RecognitionRule,
    canonical_value: str,
) -> str:
    if canonical_value != "<value>":
        return canonical_value

    if rule.rule_type == RuleType.REGEX:
        match = re.fullmatch(
            rule.value,
            text.strip(),
            flags=re.IGNORECASE,
        )

        if match is not None:
            if "value" in match.groupdict():
                return match.group("value")

            return match.group(0)

    return text.strip()

def recognize(
    text: str,
    classes: dict[str, RecognitionClass],
    hyperclass: str | None = None,
) -> RecognitionResult | None:

    if hyperclass is not None:
        if hyperclass not in classes:
            raise ValueError(
                f"Неизвестный гиперкласс: {hyperclass}"
            )

        classes = {hyperclass: classes[hyperclass]}

    for rule_type in (RuleType.EXACT, RuleType.REGEX):
        matches: list[RecognitionResult] = []

        for recognition_class in classes.values():
            for value in recognition_class.values:
                for rule in value.rules:
                    if rule.rule_type != rule_type:
                        continue

                    if not rule_matches(text, rule):
                        continue

                    matches.append(
                        RecognitionResult(
                            hyperclass=recognition_class.name,
                            base_value=get_base_value(text, rule, value.name),
                            value=text,
                            status=rule.status,
                            comment=rule.comment,
                        )
                    )

        if not matches:
            continue

        # Определяем максимальный приоритет.
        best_priority = max(
            STATUS_PRIORITY[item.status]
            for item in matches
        )

        # Оставляем только самые благоприятные совпадения.
        best_matches = [
            item for item in matches
            if STATUS_PRIORITY[item.status] == best_priority
        ]

        # Проверяем, не относятся ли лучшие совпадения
        # к разным каноническим значениям.
        destinations = {
            (item.hyperclass, item.base_value)
            for item in best_matches
        }

        if len(destinations) > 1:
            raise ValueError(
                f"Ambiguous recognition for {text!r}: "
                f"{destinations}"
            )

        return best_matches[0]

    return None
