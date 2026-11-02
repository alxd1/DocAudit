
from packages.DocLex import recognize
from packages.DocLex.models import RecognitionStatus


def get_table_indices(first_row, second_row):
    result = {
        "ServerNameColumn": [],
        "DiskSystemColumn": [],
        "OSColumn": [],
        "CPUColumn": [],
        "RAMColumn": [],
        "DiskPurposeColumn": [],
        "DiskSizeColumn": [],
        "DiskTypeColumn": [],
        "TopHeaderRow": False,
        "BottomHeaderRow": False,
    }

    top_columns = {"ServerNameColumn", "DiskSystemColumn", "OSColumn", "CPUColumn", "RAMColumn"}
    bottom_columns = {"DiskPurposeColumn", "DiskSizeColumn", "DiskTypeColumn"}

    for row, allowed_columns in ((first_row, top_columns), (second_row, bottom_columns)):
        for i, cell in enumerate(row.cells):
            recognition_result = recognize(cell.text.strip())

            if recognition_result is None or recognition_result.status == RecognitionStatus.FATAL:
                continue

            hyperclass = recognition_result.hyperclass

            if hyperclass in allowed_columns:
                result[hyperclass].append(i)

    result["TopHeaderRow"] = (
        len(result["ServerNameColumn"]) == 1
        and len(result["DiskSystemColumn"]) == 3
        and len(result["OSColumn"]) == 1
        and len(result["CPUColumn"]) == 1
        and len(result["RAMColumn"]) == 1
    )

    result["BottomHeaderRow"] = (
        len(result["DiskPurposeColumn"]) == 1
        and len(result["DiskSizeColumn"]) == 1
        and len(result["DiskTypeColumn"]) == 1
    )

    return result


