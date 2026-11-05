import re


def process(text: str) -> str:
    text = re.sub(r"(?<=\w)\*+(?=\s|$)", "", text)
    text = re.sub(r"\s+\*+\s*$", "", text)
    return text