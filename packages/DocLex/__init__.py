from configuration.configuration import DOC_LEX_RECOGNITION_RULES_DIRECTORY

from .config_loader import load_all_classes
from .models import RecognitionResult
from .recognizer import recognize as _recognize


RECOGNITION_CLASSES = load_all_classes(DOC_LEX_RECOGNITION_RULES_DIRECTORY)


def recognize(text: str, hyperclass: str | list[str] | None = None) -> RecognitionResult | None:
    return _recognize(text, RECOGNITION_CLASSES, hyperclass=hyperclass)