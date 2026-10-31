from pathlib import Path
from docx import Document
import re

# Функция для поиска индексов ячеек, содержащих заданный шаблон
def find_cell_indices(first_row, second_row, pattern: str, found_strings: list[str]) -> list[int] | None:
    regex = re.compile(pattern, re.IGNORECASE)

    for row in (first_row, second_row):
        for cell in row.cells:
            if regex.search(cell.text):

                # Добавляем найденную строку в список found_strings
                found_strings.append(cell.text)

                # Возвращаем индексы ячеек, соответствующих найденной строке
                return [index for index, current_cell in enumerate(row.cells) if current_cell._tc is cell._tc]

    return None


# Функции для проверки наличия информации в заголовках таблицы и получения индексов соответствующих ячеек
def has_server_name(first_row, second_row, found_strings: list[str]) -> list[int] | None: # Проверка наличия информации об имени сервера
    return find_cell_indices(first_row, second_row, r"имя\s+сервера", found_strings)

def has_os_info(first_row, second_row, found_strings: list[str]) -> list[int] | None: # Проверка наличия информации об операционной системе
    return find_cell_indices(first_row, second_row, r"\bОС\b", found_strings)


def has_cpu_info(first_row, second_row, found_strings: list[str]) -> list[int] | None: # Проверка наличия информации о процессоре
    return find_cell_indices(first_row, second_row, r"\bCPU\b", found_strings)


def has_ram_info(first_row, second_row, found_strings: list[str]) -> list[int] | None: # Проверка наличия информации о оперативной памяти
    return find_cell_indices(first_row, second_row, r"\bRAM\b", found_strings)


def has_disk_info(first_row, second_row, found_strings: list[str]) -> list[int] | None: # Проверка наличия информации о дисковой подсистеме
    return find_cell_indices(first_row, second_row, r"дисковая\s+подсистема", found_strings)


# Функция для получения значений ячеек в строке таблицы
def get_row_values(row) -> list[str]:
    return [cell.text.replace("*", "").strip() for cell in row.cells]


# Функция для получения информации о заголовках таблицы серверов
def get_servers_table_header_info(table) -> dict[str, list[int] | None]:
    if len(table.rows) < 2:
        return None

    # Получаем первую и вторую строки таблицы
    first_row = table.rows[0]
    second_row = table.rows[1]

    # Инициализируем список для хранения найденных строк заголовков
    found_strings = []

    result = {
        "server_name": has_server_name(first_row, second_row, found_strings),
        "os_info": has_os_info(first_row, second_row, found_strings),
        "cpu_info": has_cpu_info(first_row, second_row, found_strings),
        "ram_info": has_ram_info(first_row, second_row, found_strings),
        "disk_info": has_disk_info(first_row, second_row, found_strings)
    }

    # Проверяем, что все значения в словаре result не равны None
    if any(value is None for value in result.values()):
        return None

    # Возвращаем словарь с информацией о заголовках таблицы и список найденных строк заголовков, 
    # который будет использоваться для фильтрации строк таблицы при извлечении информации о серверах
    return result, found_strings


# Функции для составления информации о дисках и серверах
def compose_disk_info(disk_target, disk_size, disk_type) -> dict:
    return [
        {
            "target": target.strip(),
            "size": int(size.strip()),
            "type": disk_type_value.strip()
        }
        for target, size, disk_type_value in zip(
            disk_target,
            disk_size,
            disk_type,
            strict=True
        )
    ]

# Функция для составления информации о сервере
def compose_server_info(name, os_and_software, cpu, ram, disk_info) -> dict:
    return {
        "name": name.strip(),
        "os_and_software": re.sub(r"\s+", " ", os_and_software).strip(),
        "cpu": cpu.strip(),
        "ram": ram.strip(),
        "disk": disk_info
    }
    

def extract_servers_info(table, table_info):
    index_info, found_strings = table_info
    name_index = index_info["server_name"][0]
    os_index = index_info["os_info"][0]
    cpu_index = index_info["cpu_info"][0]
    ram_index = index_info["ram_info"][0]
    disk_indices = index_info["disk_info"]

    servers = {}
    messages = []

    previous_server_name = None

    copy_count = 1  # Счетчик для создания уникальных имен серверов при дублировании

    for row in table.rows:
        cells = get_row_values(row)

        # Проверяем, что строка не является заголовком таблицы, пропуская строки, содержащие найденные строки заголовков
        if any(cell in found_strings for cell in cells):
            continue # Пропускаем строки заголовков

        name            = re.sub(r"\s+", " ", cells[name_index])
        os_and_software = cells[os_index]
        cpu             = cells[cpu_index]
        ram             = cells[ram_index]

        # Проверяем, что все значения в строке не равны друг другу, чтобы избежать обработки пустых строк или общих заголовков
        if name == os_and_software == cpu == ram:
            continue  # Пропускаем строки, где все значения одинаковы (например, пустые строки или общие заголовки)


        disk_target = [value for value in cells[disk_indices[0]].splitlines()]
        disk_size   = [value for value in cells[disk_indices[1]].splitlines()]
        disk_type   = [value for value in cells[disk_indices[2]].splitlines()]

        

        # Проверяем количество характеристик дисков
        if not (len(disk_target) == len(disk_size) == len(disk_type)):

            # Если количество элементов в столбцах дисковой подсистемы не совпадает, 
            # проверяем, есть ли только один элемент в столбцах "Цель" и "Тип", 
            # и если да, то дублируем его для соответствия количеству элементов в столбце "Размер".
            if len(disk_target) == len(disk_type) == 1:
                for i in range(len(disk_size) - 1):
                    disk_target.append(disk_target[0])
                    disk_type.append(disk_type[0])
            else:
                # Если количество элементов в столбцах дисковой подсистемы не совпадает и не выполняется условие выше,
                messages.append(f"Ошибка: Несоответствие количества элементов в столбцах дисковой подсистемы для сервера '{name}'")
                continue

        disks           = compose_disk_info(disk_target, disk_size, disk_type)
        new_server_info = compose_server_info(name, os_and_software, cpu, ram, disks)
        
        # Если сервер с таким именем уже существует, проверяем, совпадают ли его характеристики с новыми данными
        if name in servers:
            # Если имя сервера совпадает с предыдущим, объединяем информацию о дисках
            if previous_server_name == name:
                servers[name]["disk"].extend(disks)

            # Если имя сервера совпадает, но предыдущий сервер имел другое имя, проверяем характеристики
            else:
                create_copy = False
                if new_server_info["os_and_software"] != servers[name]["os_and_software"]:
                    messages.append(f"Предупреждение: Для сервера '{name}' обнаружены разные значения ОС и ПО.")
                    create_copy = True

                if new_server_info["cpu"] != servers[name]["cpu"]:
                    messages.append(f"Предупреждение: Для сервера '{name}' обнаружены разные значения CPU.")
                    create_copy = True

                if new_server_info["ram"] != servers[name]["ram"]:
                    messages.append(f"Предупреждение: Для сервера '{name}' обнаружены разные значения RAM.")
                    create_copy = True

                if new_server_info["disk"] != servers[name]["disk"]:
                    messages.append(f"Предупреждение: Для сервера '{name}' обнаружены разные значения дисковой подсистемы.")
                    create_copy = True

                # Если обнаружены различия в характеристиках, создаем копию сервера с уникальным именем
                if create_copy:
                    servers[name + " (копия " + str(copy_count) + ")"] = new_server_info
                    copy_count += 1
        else:
            # Если сервер с таким именем не существует, добавляем его в словарь servers
            servers[name] = new_server_info

        previous_server_name = name

    return servers, messages