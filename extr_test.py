
from pathlib import Path
from docx import Document

from packages.DocLex import recognize
from packages.document_analyzer.parsers.servers_info import extract_servers_info


DOCX_FOLDER = "documents"
DOCX_PATHS = [
    Path(DOCX_FOLDER) / "20260409_ТП Эра-Пик 2026_v2.0 (1).docx",
    Path(DOCX_FOLDER) / "iAdviser Технический проект-v1.0.docx",
    Path(DOCX_FOLDER) / "Технический проект v.1.3.docx",
    Path(DOCX_FOLDER) / "Технический проект ИТ-решение U210001934 v2.7.4_2.docx",
    Path(DOCX_FOLDER) / "ТП U200001733 Создание общекорпоративной платформы BPMS_Миграция ИС УПЦ_v3.2.docx",
    Path(DOCX_FOLDER) / "ТП на ИТ-решения ПУЛЬСАР Релиз 4.1 версия документа 4.2.1.docx",
]


def format_value(data):
    value, message_number = data
    return f"{value} ({message_number})" if message_number is not None else str(value)


def print_global_messages(messages):
    if not messages:
        print("    Нет сообщений")
        return

    for hyperclass, items in messages.items():
        print(f"    {hyperclass}:")

        for status, message in items:
            print(f"      [{status.value}] {message}")


def print_server_messages(messages):
    if not messages:
        return

    print("      Сообщения:")

    for number, (status, message) in messages.items():
        print(f"        №{number} [{status.value}] {message}")


def print_server(server, index):
    name = format_value(server["name"])
    occurrence = server.get("occurrence", 1)
    rows = ", ".join(str(i + 1) for i in server.get("source_rows", []))

    print(f"\n  [{index}] {name} — упоминание №{occurrence}, строки: {rows}")
    print(f"      ОС:  {format_value(server['os'])}")
    print(f"      CPU: {format_value(server['cpu'])}")
    print(f"      RAM: {format_value(server['ram'])}")

    disks = server.get("disks", [])

    if disks:
        print(f"      Диски:")

        disk_rows = [
            (
                format_value(disk["purpose"]),
                format_value(disk["size"]),
                format_value(disk["type"]),
            )
            for disk in disks
        ]

        purpose_width = max(11, *(len(row[0]) for row in disk_rows))
        size_width = max(6, *(len(row[1]) for row in disk_rows))


        for i, (purpose, size, disk_type) in enumerate(disk_rows, start=1):
            print(
                f"      {i:>2}. {purpose:<{purpose_width}}  "
                f"{size:>{size_width}}  {disk_type}"
            )
    else:
        print("      Диски: не найдены")

    print_server_messages(server.get("messages", {}))


def main():
    total_tables = 0
    total_servers = 0
    total_global_messages = 0
    total_server_messages = 0

    for docx_path in DOCX_PATHS:
        print(f"\n{'=' * 90}")
        print(f"ДОКУМЕНТ: {docx_path.name}")
        print(f"{'=' * 90}")

        if not docx_path.is_file():
            print("Файл не найден")
            continue

        document = Document(docx_path)

        print(f"Всего таблиц: {len(document.tables)}")

        document_tables = 0
        document_servers = 0

        for table_index, table in enumerate(document.tables, start=1):
            result = extract_servers_info(table)

            if result is None:
                continue

            servers_info, global_messages = result

            document_tables += 1
            document_servers += len(servers_info)

            total_tables += 1
            total_servers += len(servers_info)
            total_global_messages += sum(
                len(items) for items in global_messages.values()
            )

            print(f"\n{'-' * 90}")
            print(f"ТАБЛИЦА №{table_index}")
            print(f"Строк: {len(table.rows)}, столбцов: {len(table.columns)}")
            print(f"Упоминаний серверов: {len(servers_info)}")
            print(f"{'-' * 90}")

            print("\nГЛОБАЛЬНЫЕ СООБЩЕНИЯ:")
            print_global_messages(global_messages)

            print("\nНАЙДЕННЫЕ СЕРВЕРЫ:")

            if not servers_info:
                print("    Серверы не найдены")

            for server_index, server in enumerate(servers_info, start=1):
                print_server(server, server_index)
                total_server_messages += len(server.get("messages", {}))

        print(f"\n{'=' * 90}")
        print("ИТОГО ПО ДОКУМЕНТУ:")
        print(f"  Найдено таблиц серверов: {document_tables}")
        print(f"  Найдено упоминаний серверов: {document_servers}")
        print(f"{'=' * 90}")

    print(f"\n{'=' * 90}")
    print("ОБЩИЕ РЕЗУЛЬТАТЫ")
    print(f"{'=' * 90}")
    print(f"Найдено таблиц серверов: {total_tables}")
    print(f"Найдено упоминаний серверов: {total_servers}")
    print(f"Глобальных сообщений: {total_global_messages}")
    print(f"Сообщений серверов: {total_server_messages}")
    print(f"Всего сообщений: {total_global_messages + total_server_messages}")
    print(f"{'=' * 90}")


if __name__ == "__main__":
    main()
