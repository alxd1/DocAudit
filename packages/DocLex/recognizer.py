
import re

from .models import (
    RecognitionClass,
    RecognitionResult,
    RecognitionRule,
    RecognitionStatus,
    RuleType,
)

def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def rule_matches(text: str, rule: RecognitionRule) -> re.Match | bool | None:
    if rule.rule_type == RuleType.EXACT:
        return text == normalize(rule.value)

    if rule.rule_type == RuleType.REGEX:
        return re.fullmatch(rule.value, text, flags=re.IGNORECASE)

    return None



def get_base_value(text: str, match: re.Match | bool, canonical_value: str) -> str:
    if canonical_value != "<value>":
        return canonical_value

    if isinstance(match, re.Match):
        if "value" in match.groupdict():
            return match.group("value")

        return match.group(0)

    return text


def recognize(text: str, classes: dict[str, RecognitionClass], hyperclass: str | list[str] | None = None, preprocessor=None) -> RecognitionResult | None:
    initial_text = text

    if preprocessor is not None:
        text = preprocessor(text)

        if not isinstance(text, str):
            raise TypeError("Preprocessor must return str")

    processed_text = normalize(text)

    if hyperclass is not None:
        hyperclasses = [hyperclass] if isinstance(hyperclass, str) else hyperclass

        for name in hyperclasses:
            if name not in classes:
                raise ValueError(f"Неизвестный гиперкласс: {name}")

        classes = {name: classes[name] for name in hyperclasses}

    for rule_type in (RuleType.EXACT, RuleType.REGEX):
        matches: list[tuple[RecognitionResult, int]] = []

        for recognition_class in classes.values():
            for value in recognition_class.values:
                for rule in value.rules:
                    if rule.rule_type != rule_type:
                        continue

                    match = rule_matches(processed_text, rule)

                    if not match:
                        continue

                    reg_value = None
                    reg_span = None

                    if isinstance(match, re.Match) and "ret" in match.groupdict():
                        reg_value = match.group("ret")
                        reg_span = match.span("ret")

                    matches.append((
                        RecognitionResult(
                            hyperclass=recognition_class.name,
                            base_value=get_base_value(processed_text, match, value.name),
                            initial_text=initial_text,
                            processed_text=processed_text,
                            status=rule.status,
                            comment=rule.comment,
                            reg_value=reg_value,
                            reg_span=reg_span,
                        ),
                        rule.priority,
                    ))

        if not matches:
            continue

        best_score = min(
            (item.status, priority)
            for item, priority in matches
        )

        best_matches = [
            item for item, priority in matches
            if (item.status, priority) == best_score
        ]

        destinations = {
            (item.hyperclass, item.base_value)
            for item in best_matches
        }

        if len(destinations) > 1:
            raise ValueError(f"Ambiguous recognition for {text!r}: {destinations}")

        result = best_matches[0]
        processor = classes[result.hyperclass].processor

        if processor is not None:
            result = processor(result)

            if not isinstance(result, RecognitionResult):
                raise TypeError(f"Processor for {best_matches[0].hyperclass} must return RecognitionResult")

        return result

    return None
