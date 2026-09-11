"""Main entry point for Outlets Deduplication script."""

import sys
import time
from datetime import datetime
from pathlib import Path

from config import PROJECT_ROOT, RESULTS_DIR, OUTPUT_FILENAME_PATTERN
from excel_handler import find_input_excel_file, read_excel_data, write_excel_results
from deduplicator import OutletRecord, OutletsDeduplicator


def main():
    start_total_time = time.time()
    print("=" * 70)
    print("      Outlets Deduplication - Сопоставление торговых точек")
    print("=" * 70)

    # 1. Locate input file
    print(f"\n[1/4] Поиск исходного Excel-файла в корне проекта ({PROJECT_ROOT})...")
    try:
        input_file = find_input_excel_file(PROJECT_ROOT)
        print(f" -> Найден файл: {input_file.name} (размер: {input_file.stat().st_size / (1024 * 1024):.1f} MB)")
    except Exception as e:
        print(f" ОШИБКА поиска файла: {e}")
        sys.exit(1)

    # 2. Read Excel data
    print("\n[2/4] Чтение данных из Excel...")
    t0 = time.time()
    try:
        headers, rows, col_indices = read_excel_data(input_file)
        print(f" -> Загружено строк: {len(rows):,} за {time.time() - t0:.2f} сек.")
    except Exception as e:
        print(f" ОШИБКА при чтении файла: {e}")
        sys.exit(1)

    # 3. Preprocessing and Deduplication
    print("\n[3/4] Нормализация адресов и дедупликация...")
    t0 = time.time()
    records = [OutletRecord(i, r, col_indices) for i, r in enumerate(rows)]
    prep_time = time.time() - t0
    print(f" -> Подготовка и нормализация {len(records):,} записей: {prep_time:.2f} сек.")

    t0 = time.time()
    dedup = OutletsDeduplicator(records)
    results = dedup.run()
    dedup_time = time.time() - t0
    print(f" -> Сопоставление и группировка: {dedup_time:.2f} сек.")
    print(f" -> Сформировано итоговых строк: {len(results):,}")

    # Statistics
    status_counts = {}
    group_ids = set()
    for final_id, status, _ in results:
        status_counts[status] = status_counts.get(status, 0) + 1
        group_ids.add(final_id)

    print("\nСтатистика сопоставления:")
    print(f"  - Всего уникальных групп (Итоговый ID): {len(group_ids):,}")
    for st, cnt in sorted(status_counts.items()):
        print(f"  - Статус '{st}': {cnt:,} строк")

    # 4. Save results
    print("\n[4/4] Запись результатов в Excel...")
    t0 = time.time()
    completion_dt = datetime.now()
    output_filename = completion_dt.strftime(OUTPUT_FILENAME_PATTERN)
    output_path = RESULTS_DIR / output_filename

    try:
        write_excel_results(output_path, headers, results)
        write_time = time.time() - t0
        print(f" -> Файл успешно сохранен: {output_path}")
        print(f" -> Время записи: {write_time:.2f} сек.")
    except Exception as e:
        print(f" ОШИБКА при записи файла: {e}")
        sys.exit(1)

    total_time = time.time() - start_total_time
    print("\n" + "=" * 70)
    print(f" Работа завершена за {total_time:.2f} сек. ({total_time / 60:.1f} мин.)")
    print("=" * 70)


if __name__ == "__main__":
    main()
