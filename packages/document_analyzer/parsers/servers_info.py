
from pathlib import Path
from docx import Document
import re


def get_header_info(table) -> dict[str, list[int] | None]:
    if len(table.rows) < 2:
        return None


    