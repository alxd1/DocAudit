
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

    top_columns = ["ServerNameColumn", "DiskSystemColumn", "OSColumn", "CPUColumn", "RAMColumn"]
    bottom_columns = ["DiskPurposeColumn", "DiskSizeColumn", "DiskTypeColumn"]

    # Распознаём заголовки первой строки
    for i, cell in enumerate(first_row.cells):
        recognition_result = recognize(cell.text.strip(), hyperclass=top_columns)

        if recognition_result is None or recognition_result.status == RecognitionStatus.FATAL:
            continue

        recognition_result.set_index(i)
        result[recognition_result.hyperclass].append(recognition_result)

    # Распознаём подзаголовки только внутри дисковой подсистемы
    for item in result["DiskSystemColumn"]:
        index = item.index

        recognition_result = recognize(second_row.cells[index].text.strip(), hyperclass=bottom_columns)

        if recognition_result is None or recognition_result.status == RecognitionStatus.FATAL:
            continue

        recognition_result.set_index(index)
        result[recognition_result.hyperclass].append(recognition_result)

    # Проверка верхнего заголовка
    result["TopHeaderRow"] = (
        len(result["ServerNameColumn"]) == 1
        and len(result["DiskSystemColumn"]) >= 3
        and len(result["OSColumn"]) == 1
        and len(result["CPUColumn"]) == 1
        and len(result["RAMColumn"]) == 1
    )

    # Проверка нижнего заголовка
    disk_indices = sorted(item.index for item in result["DiskSystemColumn"])
    subcolumn_indices = sorted(item.index for name in bottom_columns for item in result[name])

    result["BottomHeaderRow"] = (
        len(result["DiskPurposeColumn"]) == 1
        and len(result["DiskSizeColumn"]) == 1
        and len(result["DiskTypeColumn"]) == 1
    )

    return result