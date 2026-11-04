import re

from packages.DocLex import recognize

from packages.DocLex.models import RecognitionStatus

STATUS_PRIORITY = {
    RecognitionStatus.GOOD: 0,
    RecognitionStatus.NORMAL: 1,
    RecognitionStatus.WARNING: 2,
    RecognitionStatus.CRITICAL: 3,
    RecognitionStatus.FATAL: 4,
}

COLUMNS = [
    "ServerNameColumn",
    "DiskSystemColumn",
    "OSColumn",
    "CPUColumn",
    "RAMColumn",
    "DiskPurposeColumn",
    "DiskSizeColumn",
    "DiskTypeColumn",
]

DISK_VALUE_COLUMNS = {
    "DiskPurposeValue": "DiskPurposeColumn",
    "DiskSizeValue": "DiskSizeColumn",
    "DiskTypeValue": "DiskTypeColumn",
}


COLUMN_LABELS = {
    "ServerNameColumn": "\"Имя сервера\"",
    "DiskSystemColumn": "\"Дисковая подсистема\"",
    "OSColumn": "\"Операционная система\"",
    "CPUColumn": "\"Количество ядер CPU\"",
    "RAMColumn": "\"Объём оперативной памяти\"",
    "DiskPurposeColumn": "\"Назначение диска\"",
    "DiskSizeColumn": "\"Объём диска\"",
    "DiskTypeColumn": "\"Тип диска\"",
}


def clean_value(value):
    return re.sub(r"\*+", "", value).strip()


def get_table_indices(first_row, second_row):
    result = {class_name: [] for class_name in COLUMNS}
    result["TopHeaderRow"] = False
    result["BottomHeaderRow"] = False
    for class_name in COLUMNS:
        for row in (first_row, second_row):
            for i, cell in enumerate(row.cells):
                recognition_result = recognize(clean_value(cell.text), hyperclass=class_name)
                if recognition_result is None or recognition_result.status == RecognitionStatus.FATAL:
                    continue
                recognition_result.set_index(i)
                result[class_name].append(recognition_result)
    # Проверяем принадлежность подзаголовков дисковой подсистеме
    if result["DiskSystemColumn"]:
        disk_indices = {item.index for item in result["DiskSystemColumn"]}
        for class_name in DISK_VALUE_COLUMNS.values():
            result[class_name] = [
                item for item in result[class_name]
                if item.index in disk_indices
            ]
    # Оставляем лучшее совпадение для каждого гиперкласса
    for class_name in COLUMNS:
        if class_name == "DiskSystemColumn" or not result[class_name]:
            continue
        best_result = min(
            result[class_name],
            key=lambda item: STATUS_PRIORITY[item.status]
        )
        result[class_name] = [best_result]
    result["TopHeaderRow"] = (
        len(result["ServerNameColumn"]) >= 1
        and len({item.index for item in result["DiskSystemColumn"]}) >= 3
        and len(result["OSColumn"]) >= 1
        and len(result["CPUColumn"]) >= 1
        and len(result["RAMColumn"]) >= 1
    )
    result["BottomHeaderRow"] = any(
        result[class_name] for class_name in DISK_VALUE_COLUMNS.values()
    )
    return result


def is_header_row(row, indices):
    matches = 0
    for class_name in COLUMNS:
        if class_name == "DiskSystemColumn":
            continue
        for index in indices[class_name]:
            if index >= len(row.cells):
                continue
            value = clean_value(row.cells[index].text)
            recognition_result = recognize(value, hyperclass=class_name)
            if recognition_result is not None and recognition_result.status != RecognitionStatus.FATAL:
                matches += 1
                break
    return matches >= 2


def get_row_values(row):
    return [clean_value(cell.text) for cell in row.cells]


def is_department_row(row):
    values = get_row_values(row)
    return bool(values) and bool(values[0]) and all(
        value == values[0] for value in values
    )


def is_vertical_merge_continuation(row, index):
    grid_index = getattr(row, "grid_cols_before", 0)
    for tc in row._tr.tc_lst:
        grid_span = tc.grid_span
        if grid_index <= index < grid_index + grid_span:
            return tc.vMerge == "continue"
        grid_index += grid_span
    return False


def split_disk_values(value):
    values = [clean_value(item) for item in value.splitlines()]
    while values and not values[-1]:
        values.pop()
    return values


def normalize_value(value):
    return " ".join(clean_value(value).split())


def add_server_message(messages, status, message):
    number = len(messages) + 1
    messages[number] = (status, message)
    return number


def add_global_message(messages, hyperclass, status, message):
    messages.setdefault(hyperclass, []).append((status, message))


def recognize_value(value, hyperclass, server_name, label, messages):
    value = normalize_value(value)
    if not value:
        number = add_server_message(
            messages, RecognitionStatus.CRITICAL,
            f'Не указано значение {label}.'
        )
        return "n/a", number
    recognition_result = recognize(value, hyperclass=hyperclass)
    if recognition_result is None:
        number = add_server_message(
            messages, RecognitionStatus.CRITICAL,
            f'Не удалось распознать значение {label} "{value}"'
        )
        return value, number
    if recognition_result.status == RecognitionStatus.FATAL:
        comment = f", {recognition_result.comment}" if recognition_result.comment else ""
        number = add_server_message(
            messages, RecognitionStatus.FATAL,
            f'Недопустимое значение {label} "{value}"{comment}'
        )
        return value, number
    if recognition_result.status != RecognitionStatus.GOOD:
        comment = f", {recognition_result.comment}" if recognition_result.comment else ""
        number = add_server_message(
            messages, recognition_result.status,
            f'Найдено значение {label} "{value}"{comment}'
        )
        return recognition_result.base_value, number
    return recognition_result.base_value, None


def extract_disks(row, indices, server_name, messages):
    disk_columns = {
        "purpose": ("DiskPurposeColumn", "DiskPurposeValue"),
        "size": ("DiskSizeColumn", "DiskSizeValue"),
        "type": ("DiskTypeColumn", "DiskTypeValue"),
    }
    raw_values = {}
    for name, (column_class, _) in disk_columns.items():
        if not indices[column_class]:
            raw_values[name] = []
            continue
        index = indices[column_class][0]
        raw_values[name] = split_disk_values(row.cells[index].text)
    if not any(any(value for value in values) for values in raw_values.values()):
        return []
    disk_count = max(len(values) for values in raw_values.values())
    disks = []
    for i in range(disk_count):
        disk = {}
        for name, (column_class, value_class) in disk_columns.items():
            values = raw_values[name]
            value = values[i] if i < len(values) else ""
            disk[name] = recognize_value(
                value, value_class, server_name,
                f"{COLUMN_LABELS[column_class]} (диск №{i + 1})", messages
            )
        disks.append(disk)
    return disks


def find_missing_disk_columns(table, indices):
    disk_indices = sorted(set(indices["DiskSystemColumn"]))
    occupied_indices = {
        index
        for class_name in DISK_VALUE_COLUMNS.values()
        for index in indices[class_name]
    }
    candidates = []
    for value_class, column_class in DISK_VALUE_COLUMNS.items():
        if indices[column_class]:
            continue
        for index in disk_indices:
            if index in occupied_indices:
                continue
            matches = 0
            good_matches = 0
            for row in table.rows:
                if is_department_row(row) or is_header_row(row, indices):
                    continue
                if index >= len(row.cells):
                    continue
                for value in split_disk_values(row.cells[index].text):
                    if not value:
                        continue
                    recognition_result = recognize(value, hyperclass=value_class)
                    if recognition_result is None or recognition_result.status == RecognitionStatus.FATAL:
                        continue
                    matches += 1
                    if recognition_result.status == RecognitionStatus.GOOD:
                        good_matches += 1
            if matches:
                candidates.append((
                    -matches,
                    -good_matches,
                    value_class,
                    column_class,
                    index,
                ))
    candidates.sort()
    found_columns = {}
    for negative_matches, negative_good_matches, value_class, column_class, index in candidates:
        if indices[column_class] or index in occupied_indices:
            continue
        indices[column_class].append(index)
        occupied_indices.add(index)
        found_columns[column_class] = (index, -negative_matches, -negative_good_matches)
    return found_columns


def extract_servers_info(table):
    if table is None or len(table.rows) < 2:
        return None
    table_info = get_table_indices(table.rows[0], table.rows[1])
    if not table_info["TopHeaderRow"]:
        return None
    indices = {
        class_name: [item.index for item in table_info[class_name]]
        for class_name in COLUMNS
    }
    servers_info = []
    global_messages = {}
    server_counts = {}
    current_server = None
    for class_name in COLUMNS:
        for item in table_info[class_name]:
            if item.status != RecognitionStatus.GOOD:
                comment = f", {item.comment}" if item.comment else ""
                add_global_message(
                    global_messages, class_name, item.status,
                    f'Найдено название "{item.value}"{comment}'
                )
    disk_columns = {
        class_name: COLUMN_LABELS[class_name]
        for class_name in DISK_VALUE_COLUMNS.values()
    }
    missing_columns = {
        class_name: name
        for class_name, name in disk_columns.items()
        if not indices[class_name]
    }
    if missing_columns:
        names = ", ".join(f'{name}' for name in missing_columns.values())
        add_global_message(
            global_messages, "DiskSystemColumn", RecognitionStatus.WARNING,
            f"Не удалось распознать заголовки дисковой подсистемы: {names}. "
            "Выполняется поиск колонок по значениям."
        )
        found_columns = find_missing_disk_columns(table, indices)
        for class_name, name in missing_columns.items():
            if class_name in found_columns:
                index, matches, good_matches = found_columns[class_name]
                add_global_message(
                    global_messages, class_name, RecognitionStatus.NORMAL,
                    f'Столбец {name} найден по значениям: индекс {index}, '
                    f'совпадений {matches} (полных: {good_matches}).'
                )
            else:
                add_global_message(
                    global_messages, class_name, RecognitionStatus.WARNING,
                    f'Не удалось найти столбец {name} по значениям.'
                )
    name_index = indices["ServerNameColumn"][0]
    os_index = indices["OSColumn"][0]
    cpu_index = indices["CPUColumn"][0]
    ram_index = indices["RAMColumn"][0]
    for row_number, row in enumerate(table.rows):
        if is_department_row(row) or is_header_row(row, indices):
            current_server = None
            continue
        cells = get_row_values(row)
        if not any(cells):
            current_server = None
            continue
        server_name = normalize_value(cells[name_index])
        os_text = cells[os_index]
        cpu_text = cells[cpu_index]
        ram_text = cells[ram_index]
        merged_name = is_vertical_merge_continuation(row, name_index)
        empty_name_continuation = (
            not server_name and not any((os_text, cpu_text, ram_text))
        )
        merged_fields_continuation = (
            not server_name and any(
                is_vertical_merge_continuation(row, index)
                for index in (os_index, cpu_index, ram_index)
            )
        )
        is_continuation = (
            current_server is not None
            and (merged_name or empty_name_continuation or merged_fields_continuation)
        )
        if is_continuation:
            current_server["disks"].extend(extract_disks(
                row, indices, current_server["name"][0], current_server["messages"]
            ))
            current_server["source_rows"].append(row_number)
            continue
        messages = {}
        if server_name:
            name_value = (server_name, None)
        else:
            number = add_server_message(
                messages, RecognitionStatus.WARNING, "Пустое значение названия сервера."
            )
            server_name = "n/a"
            name_value = (server_name, number)
        os = recognize_value(os_text, "OSValue", server_name, "ОС", messages)
        cpu = recognize_value(cpu_text, "CPUValue", server_name, "CPU", messages)
        ram = recognize_value(ram_text, "RAMValue", server_name, "RAM", messages)
        disks = extract_disks(row, indices, server_name, messages)
        server_counts[server_name] = server_counts.get(server_name, 0) + 1
        current_server = {
            "name": name_value,
            "occurrence": server_counts[server_name],
            "os": os,
            "cpu": cpu,
            "ram": ram,
            "disks": disks,
            "messages": messages,
            "source_rows": [row_number],
        }
        servers_info.append(current_server)
    return servers_info, global_messages
