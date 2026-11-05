from .configuration import DOC_LEX_RECOGNITION_RULES_DIRECTORY

from .config_loader import load_all_classes
from .models import RecognitionResult
from .recognizer import recognize as _recognize


RECOGNITION_CLASSES = load_all_classes(DOC_LEX_RECOGNITION_RULES_DIRECTORY)


from .configuration import DOC_LEX_RECOGNITION_RULES_DIRECTORY

from .config_loader import load_all_classes, load_processor
from .models import RecognitionResult
from .recognizer import recognize as _recognize


RECOGNITION_CLASSES = load_all_classes(DOC_LEX_RECOGNITION_RULES_DIRECTORY)

PREPROCESSOR = load_processor(DOC_LEX_RECOGNITION_RULES_DIRECTORY, "__preprocessor__.py")
POSTPROCESSOR = load_processor(DOC_LEX_RECOGNITION_RULES_DIRECTORY, "__postprocessor__.py")


def recognize(text: str, hyperclass: str | list[str] | None = None) -> RecognitionResult | None:
    result = _recognize(
        text,
        RECOGNITION_CLASSES,
        hyperclass=hyperclass,
        preprocessor=PREPROCESSOR
    )

    if result is not None and POSTPROCESSOR is not None:
        result = POSTPROCESSOR(result)

        if not isinstance(result, RecognitionResult):
            raise TypeError("Postprocessor must return RecognitionResult")

    return result