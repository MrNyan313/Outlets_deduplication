"""Comprehensive integration and unit tests for Outlets Deduplication."""

import pytest
from deduplicator import OutletRecord, OutletsDeduplicator
from config import STATUS_IDENTICAL, STATUS_SIMILAR, STATUS_UNIQUE

COL_INDICES = {
    'id': 0,
    'Name': 1,
    'Юридическое название': 2,
    'AccountingSystemAddress': 3,
    'Street': 4,
    'IsVendor': 5,
    'Подсеть': 6,
    'Формат ТТ': 7,
    'Направление дистрибуции': 8,
    'Дистрибьютор': 9,
    'minDate': 10,
}


def make_row(id_val, name, addr, is_vendor, dist="Сладкая жизнь плюс ООО", subnetwork="Ru_Test"):
    return (
        str(id_val),
        name,
        "ООО Тест",
        addr,
        "Россия, " + addr,
        str(is_vendor),
        subnetwork,
        "MD",
        "food",
        dist,
        "2020-01-01"
    )


def test_different_house_numbers_never_merge():
    """Points with different house numbers must NEVER merge."""
    r1 = make_row(1, "Магазин Магнит", "г. Москва, ул. Ленина, д. 5", 0)
    r2 = make_row(2, "Магазин Магнит", "г. Москва, ул. Ленина, д. 7", 0)

    records = [OutletRecord(0, r1, COL_INDICES), OutletRecord(1, r2, COL_INDICES)]
    dedup = OutletsDeduplicator(records)
    results = dedup.run()

    assert len(results) == 2
    # Different groups
    id1, status1, _ = results[0]
    id2, status2, _ = results[1]
    assert id1 != id2
    assert status1 == STATUS_UNIQUE
    assert status2 == STATUS_UNIQUE


def test_matching_by_store_code_identical():
    """Outlets matching by internal store code at the same address get STATUS_IDENTICAL."""
    # Master point
    r_master = make_row(100, "X5 H085", "Пермский край, г. Кудымкар, ул. 50 лет Октября, 21", 1, "Сплат?Глобал")
    # Distributor point
    r_distrib = make_row(200, "Дискаунтер_H085", "Пермский край, Кудымкар, 50 лет Октября ул 21", 0, "ПЯТЁРОЧКА")

    records = [OutletRecord(0, r_master, COL_INDICES), OutletRecord(1, r_distrib, COL_INDICES)]
    dedup = OutletsDeduplicator(records)
    results = dedup.run()

    assert len(results) == 2
    id1, status1, row1 = results[0]
    id2, status2, row2 = results[1]

    # Both in same group
    assert id1 == id2
    assert status1 == STATUS_IDENTICAL
    assert status2 == STATUS_IDENTICAL
    # Master point is first in group
    assert row1[COL_INDICES['IsVendor']] == '1'
    assert row2[COL_INDICES['IsVendor']] == '0'


def test_national_network_isolation_between_competitors():
    """National networks (Tander vs Pyaterochka) at same address must NOT merge with each other."""
    r_magnit = make_row(1, "Магнит", "г. Самара, ул. Мира, 10", 0, "ТАНДЕР АО (take-off) с 01.04.2018")
    r_pyaterochka = make_row(2, "Пятерочка", "г. Самара, ул. Мира, 10", 0, "ПЯТЁРОЧКА")

    records = [OutletRecord(0, r_magnit, COL_INDICES), OutletRecord(1, r_pyaterochka, COL_INDICES)]
    dedup = OutletsDeduplicator(records)
    results = dedup.run()

    assert len(results) == 2
    assert results[0][0] != results[1][0]  # Different group IDs


def test_new_national_networks_isolation():
    """Verify that 'ДЕТСКИЙ МИР ПАО' and 'Атак take off c 01.01.2019' are recognized as national networks."""
    r_dm = make_row(1, "Детский мир", "г. Москва, ул. Ленина, 10", 0, "ДЕТСКИЙ МИР ПАО")
    r_atak = make_row(2, "Атак", "г. Москва, ул. Ленина, 10", 0, "Атак take off c 01.01.2019")
    r_reg = make_row(3, "Магазин", "г. Москва, ул. Ленина, 10", 0, "Сладкая жизнь плюс ООО")

    rec_dm = OutletRecord(0, r_dm, COL_INDICES)
    rec_atak = OutletRecord(1, r_atak, COL_INDICES)
    rec_reg = OutletRecord(2, r_reg, COL_INDICES)

    assert rec_dm.is_national is True
    assert rec_atak.is_national is True
    assert rec_reg.is_national is False

    dedup = OutletsDeduplicator([rec_dm, rec_atak, rec_reg])
    results = dedup.run()

    # None of the 3 should merge into the same group
    group_ids = {res[0] for res in results}
    assert len(group_ids) == 3


def test_regular_distributors_can_merge():
    """Different regular distributors delivering to the same store can merge."""
    r_dist1 = make_row(1, "Продукты Малинка №604", "г. Бор, Заводская ул, д. 5а", 0, "Сладкая жизнь плюс ООО")
    r_dist2 = make_row(2, "Маг. Малинка №604", "г. Бор, Заводская ул, д. 5а", 0, "ХИМБЫТОПТТОРГ ООО")

    records = [OutletRecord(0, r_dist1, COL_INDICES), OutletRecord(1, r_dist2, COL_INDICES)]
    dedup = OutletsDeduplicator(records)
    results = dedup.run()

    assert len(results) == 2
    assert results[0][0] == results[1][0]  # Same group ID


def test_unmatched_master_records_are_excluded():
    """Master records (IsVendor = 1) that did not match any distributor records are excluded from results."""
    r_master_unmatched = make_row(999, "Одиночный Магазин X", "г. Казань, ул. Баумана, 1", 1, "Сплат?Глобал")
    r_distrib_other = make_row(111, "Продукты", "г. Уфа, ул. Ленина, 15", 0, "Сладкая жизнь плюс ООО")

    records = [OutletRecord(0, r_master_unmatched, COL_INDICES), OutletRecord(1, r_distrib_other, COL_INDICES)]
    dedup = OutletsDeduplicator(records)
    results = dedup.run()

    # The master record must NOT be in the results!
    assert len(results) == 1
    assert results[0][2][COL_INDICES['id']] == '111'
    assert results[0][1] == STATUS_UNIQUE


def test_multiple_distributors_match_single_master():
    """Multiple distributor outlets can match to the same master outlet."""
    r_master = make_row(1, "Малинка №592", "г. Нижний Новгород, Кировская ул, 9а", 1, "Сплат?Глобал")
    r_d1 = make_row(2, "Стелс ООО маг.Малинка №592", "Нижегородская обл, Нижний Новгород г, Кировская ул, дом № 9А", 0, "Сладкая жизнь плюс ООО")
    r_d2 = make_row(3, "Горшкова Е.А ИП маг.Малинка № 592", "Нижегородская область обл, Нижний Новгород г, Кировская ул, дом № 9а", 0, "ХИМБЫТОПТТОРГ ООО")

    records = [
        OutletRecord(0, r_master, COL_INDICES),
        OutletRecord(1, r_d1, COL_INDICES),
        OutletRecord(2, r_d2, COL_INDICES)
    ]
    dedup = OutletsDeduplicator(records)
    results = dedup.run()

    assert len(results) == 3
    # All 3 have the same group ID
    assert results[0][0] == results[1][0] == results[2][0]
    # Master row is first
    assert results[0][2][COL_INDICES['IsVendor']] == '1'


def test_individual_row_status_with_different_legal_entities():
    """
    If a distributor outlet matches master by name exactly, it gets STATUS_IDENTICAL.
    If another distributor outlet at the same store has a different legal entity (e.g. Перминов vs Люкс),
    it gets STATUS_SIMILAR.
    """
    r_master = make_row(1, "Люкс ООО маг.Малинка №604", "Нижегородская обл, Бор г, Заводская ул, дом № 5а", 1, "Сплат?Глобал")
    r_d_exact = make_row(2, "Люкс ООО маг.Малинка №604", "Нижегородская обл, Бор г, Заводская ул, дом № 5а", 0, "Сладкая жизнь плюс ООО")
    r_d_diff_entity = make_row(3, "Перминов В.В ИП маг.Малинка № 604", "Нижегородская область обл, Бор г, Заводская ул, дом № 5А", 0, "Сладкая жизнь плюс ООО")

    records = [
        OutletRecord(0, r_master, COL_INDICES),
        OutletRecord(1, r_d_exact, COL_INDICES),
        OutletRecord(2, r_d_diff_entity, COL_INDICES),
    ]
    dedup = OutletsDeduplicator(records)
    results = dedup.run()

    assert len(results) == 3
    # All share the same group ID
    assert results[0][0] == results[1][0] == results[2][0]

    # Master is IDENTICAL because it has an exact match
    assert results[0][1] == STATUS_IDENTICAL
    # Exact distributor point is IDENTICAL
    assert results[1][1] == STATUS_IDENTICAL
    # Distributor point with different legal entity is SIMILAR
    assert results[2][1] == STATUS_SIMILAR


def test_missing_house_and_alphanumeric_store_codes():
    """
    Outlets with missing house numbers ('б/н', 'n/a' or omitted) and alphanumeric store codes
    (like '304S') from national networks must merge with status STATUS_IDENTICAL.
    """
    r_master = make_row(10, "Пятерочка 304S", "Ставропольский край, Ессентуки, Октябрьская улица, б\\н", 1, "Сплат?Глобал")
    r_d1 = make_row(20, "Дискаунтер_304S", "Ставропольский край г.Ессентуки, Октябрьская ул", 0, "ПЯТЁРОЧКА")
    r_d2 = make_row(30, "Дискаунтер_304S", "Ставропольский край, Ессентуки, Октябрьская улица, n\\a", 0, "ПЯТЁРОЧКА")

    records = [
        OutletRecord(0, r_master, COL_INDICES),
        OutletRecord(1, r_d1, COL_INDICES),
        OutletRecord(2, r_d2, COL_INDICES),
    ]
    dedup = OutletsDeduplicator(records)
    results = dedup.run()

    assert len(results) == 3
    # All share the same group ID
    assert results[0][0] == results[1][0] == results[2][0]
    # All get STATUS_IDENTICAL
    assert results[0][1] == STATUS_IDENTICAL
    assert results[1][1] == STATUS_IDENTICAL
    assert results[2][1] == STATUS_IDENTICAL


def test_same_code_different_cities_never_merge():
    """
    Outlets that share a store number (e.g. №118 or №149) but are in different cities/streets
    must NEVER merge together!
    """
    # Master outlet 1 in Dimitrovgrad
    r_dimitrovgrad = make_row(100, "№118 - Димитровград 1", "г. Димитровград, ул. Московска", 1, "Сплат?Глобал")
    # Distributor outlet in Arzamas
    r_arzamas = make_row(200, "Торговый центр Скиф ООО Спар №118", "607247, Нижегородская обл, Арзамасский р-н, Выездное рп, Куликова ул, дом № 28а", 0, "Сладкая жизнь плюс ООО")

    records = [
        OutletRecord(0, r_dimitrovgrad, COL_INDICES),
        OutletRecord(1, r_arzamas, COL_INDICES),
    ]
    dedup = OutletsDeduplicator(records)
    results = dedup.run()

    # Dimitrovgrad master has no matches, so it must be excluded!
    # Arzamas distributor point is unmatched, so it must be UNIQUE!
    assert len(results) == 1
    assert results[0][2][COL_INDICES['id']] == '200'
    assert results[0][1] == STATUS_UNIQUE


def test_different_store_codes_never_merge():
    """
    Two outlets of the same national distributor with different store codes
    (e.g. 5268 vs 5282) must NEVER merge.
    """
    r1 = make_row(1, "5268", "5268 ССИВ Москва г, ул Академика Волгина, д.15,к.3", 0, "СОЮЗ СВ. ИОАННА ВОИНА ООО (take-off) с 01.04.2018")
    r2 = make_row(2, "5282", "5282 ССИВ Москва г, аллея Долгопрудная, д.15, к. 4", 0, "СОЮЗ СВ. ИОАННА ВОИНА ООО (take-off) с 01.04.2018")

    records = [OutletRecord(0, r1, COL_INDICES), OutletRecord(1, r2, COL_INDICES)]
    dedup = OutletsDeduplicator(records)
    results = dedup.run()

    assert len(results) == 2
    # Must have different group IDs
    assert results[0][0] != results[1][0]
    assert results[0][1] == STATUS_UNIQUE
    assert results[1][1] == STATUS_UNIQUE


def test_same_house_number_different_streets_never_merge():
    """
    Two outlets with the same house number in the same city but on different streets
    (e.g. Arbat 24 vs Osennyaya 24) must NEVER merge.
    """
    r1 = make_row(1, "Дискаунтер_363H", "Московская обл. г.Москва, Арбат ул 24", 0, "ПЯТЁРОЧКА")
    r2 = make_row(2, "Дискаунтер_6905", "Московская обл. г.Москва, Осенняя ул. 24", 0, "ПЯТЁРОЧКА")

    records = [OutletRecord(0, r1, COL_INDICES), OutletRecord(1, r2, COL_INDICES)]
    dedup = OutletsDeduplicator(records)
    results = dedup.run()

    assert len(results) == 2
    assert results[0][0] != results[1][0]
    assert results[0][1] == STATUS_UNIQUE
    assert results[1][1] == STATUS_UNIQUE


def test_ssiv_stores_match_with_master_coverage_points():
    """
    Distributor stores for 'СОЮЗ СВ. ИОАННА ВОИНА ООО' (e.g. 5268 and 5282)
    must match with their corresponding master coverage points, while remaining in
    distinct groups from each other.
    """
    r_dist_5268 = make_row(
        1314, "5268", "5268 ССИВ Москва г, ул Академика Волгина, д.15,к.3", 0,
        dist="СОЮЗ СВ. ИОАННА ВОИНА ООО (take-off) с 01.04.2018"
    )
    r_mast_5268 = make_row(
        476912, "5268", "Москва г, Академика Волгина ул, 15, к 3", 1,
        dist="Сплат?Глобал"
    )
    r_dist_5282 = make_row(
        1327, "5282", "5282 ССИВ Москва г, аллея Долгопрудная, д.15, к. 4", 0,
        dist="СОЮЗ СВ. ИОАННА ВОИНА ООО (take-off) с 01.04.2018"
    )
    r_mast_5282 = make_row(
        476963, "5282", "Москва г, Долгопрудная аллея, 15, к 4", 1,
        dist="Сплат?Глобал"
    )

    records = [
        OutletRecord(0, r_dist_5268, COL_INDICES),
        OutletRecord(1, r_mast_5268, COL_INDICES),
        OutletRecord(2, r_dist_5282, COL_INDICES),
        OutletRecord(3, r_mast_5282, COL_INDICES),
    ]
    dedup = OutletsDeduplicator(records)
    results = dedup.run()

    assert len(results) == 4

    # Find rows for 5268 and 5282
    group_5268 = [r for r in results if r[2][COL_INDICES['Name']] == "5268"]
    group_5282 = [r for r in results if r[2][COL_INDICES['Name']] == "5282"]

    assert len(group_5268) == 2
    assert len(group_5282) == 2

    # Group 5268 checks
    id_5268_1, status_5268_1, row_5268_1 = group_5268[0]
    id_5268_2, status_5268_2, row_5268_2 = group_5268[1]
    assert id_5268_1 == id_5268_2
    assert status_5268_1 == STATUS_IDENTICAL
    assert status_5268_2 == STATUS_IDENTICAL
    assert row_5268_1[COL_INDICES['IsVendor']] == "1"
    assert row_5268_2[COL_INDICES['IsVendor']] == "0"

    # Group 5282 checks
    id_5282_1, status_5282_1, row_5282_1 = group_5282[0]
    id_5282_2, status_5282_2, row_5282_2 = group_5282[1]
    assert id_5282_1 == id_5282_2
    assert status_5282_1 == STATUS_IDENTICAL
    assert status_5282_2 == STATUS_IDENTICAL
    assert row_5282_1[COL_INDICES['IsVendor']] == "1"
    assert row_5282_2[COL_INDICES['IsVendor']] == "0"

    # Different groups
    assert id_5268_1 != id_5282_1


def test_tander_strict_subnetwork_isolation():
    """
    For 'ТАНДЕР АО (take-off) с 01.04.2018', outlets with different 'Подсеть'
    (e.g. Ru_Магнит vs Ru_Аптека Магнит) must NEVER merge.
    """
    # Master point has Ru_Магнит
    r_master = make_row(
        281475778144109, "Аптека Санья", "Коми, Ухта г, Комсомольская пл, 8/12", 1,
        dist="Сплат?Глобал", subnetwork="Ru_Магнит"
    )
    # Distributor point has Ru_Аптека Магнит
    r_dist = make_row(
        166633189115438379, "Аптека Санья", "Коми, Ухта г, Комсомольская пл, 8/12", 0,
        dist="ТАНДЕР АО (take-off) с 01.04.2018", subnetwork="Ru_Аптека Магнит"
    )

    records = [OutletRecord(0, r_master, COL_INDICES), OutletRecord(1, r_dist, COL_INDICES)]
    dedup = OutletsDeduplicator(records)
    results = dedup.run()

    # The master record with no matches is excluded.
    # The distributor record is UNIQUE.
    assert len(results) == 1
    assert results[0][2][COL_INDICES['id']] == "166633189115438379"
    assert results[0][1] == STATUS_UNIQUE


def test_atak_code_matching_rule():
    """
    For 'Атак take off c 01.01.2019':
    - Outlets with identical codes match as IDENTICAL (even with different address formats).
    - Outlets with different codes NEVER merge (even at the exact same address).
    """
    # Same code 548, different address formats
    r1 = make_row(1, "Атак 548", "Московская обл, Одинцово г, Горки-10 п, 24А", 0, dist="Атак take off c 01.01.2019")
    r2 = make_row(2, "548", "(548) GORKI", 0, dist="Атак take off c 01.01.2019")
    # Different code 204
    r3 = make_row(3, "Атак 204", "Московская обл, Одинцово г, Горки-10 п, 24А", 0, dist="Атак take off c 01.01.2019")

    records = [
        OutletRecord(0, r1, COL_INDICES),
        OutletRecord(1, r2, COL_INDICES),
        OutletRecord(2, r3, COL_INDICES),
    ]
    dedup = OutletsDeduplicator(records)
    results = dedup.run()

    assert len(results) == 3
    # r1 and r2 are grouped together
    id1, s1, row1 = results[0]
    id2, s2, row2 = results[1]
    id3, s3, row3 = results[2]

    assert id1 == id2
    assert s1 == STATUS_IDENTICAL
    assert s2 == STATUS_IDENTICAL

    # r3 is in a separate group
    assert id3 != id1
    assert s3 == STATUS_UNIQUE


def test_pyaterochka_code_matching_rule():
    """
    For 'ПЯТЁРОЧКА':
    - Outlets with identical alphanumeric codes (e.g. S088) match as IDENTICAL.
    - Outlets with different codes NEVER merge.
    """
    r1 = make_row(10, "Пятерочка S088", "Московская обл. г.Москва, Масловка В.ул 4", 0, dist="ПЯТЁРОЧКА")
    r2 = make_row(20, "Дискаунтер_S088", "Москва г, Верхняя Масловка ул, 4", 0, dist="ПЯТЁРОЧКА")
    r3 = make_row(30, "Дискаунтер_3242", "Москва г, Верхняя Масловка ул, 4", 0, dist="ПЯТЁРОЧКА")

    records = [
        OutletRecord(0, r1, COL_INDICES),
        OutletRecord(1, r2, COL_INDICES),
        OutletRecord(2, r3, COL_INDICES),
    ]
    dedup = OutletsDeduplicator(records)
    results = dedup.run()

    assert len(results) == 3
    assert results[0][0] == results[1][0]
    assert results[0][1] == STATUS_IDENTICAL
    assert results[1][1] == STATUS_IDENTICAL

    assert results[2][0] != results[0][0]
    assert results[2][1] == STATUS_UNIQUE


def test_tander_name_and_subnetwork_matching_rule():
    """
    For 'ТАНДЕР АО (take-off) с 01.04.2018':
    - Outlets match IF AND ONLY IF both Name and Подсеть match identically!
    - If Name matches but Подсеть differs -> DO NOT MERGE.
    - If Подсеть matches but Name differs -> DO NOT MERGE.
    """
    # Identical Name and Subnetwork
    r1 = make_row(1, "Шаровница", "Московская обл, Воскресенск г, Виноградово п, стр 1", 0,
                  dist="ТАНДЕР АО (take-off) с 01.04.2018", subnetwork="Ru_Магнит")
    r2 = make_row(2, "Шаровница", "140230, Московская обл, Коммунистическая ул, д. 1", 0,
                  dist="ТАНДЕР АО (take-off) с 01.04.2018", subnetwork="Ru_Магнит")
    # Same Name, different Subnetwork
    r3 = make_row(3, "Шаровница", "Московская обл, Воскресенск г, Виноградово п, стр 1", 0,
                  dist="ТАНДЕР АО (take-off) с 01.04.2018", subnetwork="Ru_Магнит Косметика")
    # Different Name, same Subnetwork
    r4 = make_row(4, "Турома", "Московская обл, Воскресенск г, Виноградово п, стр 1", 0,
                  dist="ТАНДЕР АО (take-off) с 01.04.2018", subnetwork="Ru_Магнит")

    records = [
        OutletRecord(0, r1, COL_INDICES),
        OutletRecord(1, r2, COL_INDICES),
        OutletRecord(2, r3, COL_INDICES),
        OutletRecord(3, r4, COL_INDICES),
    ]
    dedup = OutletsDeduplicator(records)
    results = dedup.run()

    assert len(results) == 4
    # r1 and r2 are merged into one group
    assert results[0][0] == results[1][0]
    assert results[0][1] == STATUS_IDENTICAL
    assert results[1][1] == STATUS_IDENTICAL

    # r3 and r4 are each in their own separate unique groups
    assert results[2][0] != results[0][0]
    assert results[3][0] != results[0][0]
    assert results[2][0] != results[3][0]
    assert results[2][1] == STATUS_UNIQUE
    assert results[3][1] == STATUS_UNIQUE


def test_similarity_percentage_option(tmp_path):
    """
    Test include_similarity=True:
    - deduplicator.run returns 4-tuples with similarity scores.
    - write_excel_results outputs 'Similarity %' as the last column.
    """
    from excel_handler import write_excel_results, read_excel_data
    import openpyxl

    r1 = make_row(1, "Дискаунтер_S088", "Москва г, ул. Масловка, 4", 0, dist="ПЯТЁРОЧКА")
    r2 = make_row(2, "Пятерочка S088", "Москва г, ул. Масловка, 4", 0, dist="ПЯТЁРОЧКА")
    r3 = make_row(3, "Пятерочка 9999", "Москва г, ул. Ленина, 10", 0, dist="ПЯТЁРОЧКА")

    records = [
        OutletRecord(0, r1, COL_INDICES),
        OutletRecord(1, r2, COL_INDICES),
        OutletRecord(2, r3, COL_INDICES),
    ]
    dedup = OutletsDeduplicator(records)
    results = dedup.run(include_similarity=True)

    assert len(results) == 3
    # Check 4-tuple: (final_id, status, raw_row, sim_score)
    assert len(results[0]) == 4
    assert results[0][3] == 100.0
    assert results[1][3] == 100.0
    assert results[2][3] == 0.0

    # Write to Excel and verify
    out_file = tmp_path / "test_out.xlsx"
    headers = list(COL_INDICES.keys())
    write_excel_results(out_file, headers, results, include_similarity=True)

    wb = openpyxl.load_workbook(out_file, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))

    # Check header
    assert rows[0][0] == "Итоговый ID"
    assert rows[0][1] == "Статус"
    assert rows[0][-1] == "Similarity %"

    # Check data rows: identical rows have 1.0 (100%), unique has 0.0 (0%)
    assert rows[1][-1] == 1.0
    assert rows[2][-1] == 1.0
    assert rows[3][-1] == 0.0


def test_dixi_and_metro_code_matching():
    """
    Verify that Дикси and МЕТРО match by store code in isolation:
    - Same code -> identical.
    - Different code -> cannot merge.
    """
    # Dixi
    r_d1 = make_row(1, "Дикси ДИКСИ-77007", "Москва г, Тверская ул, 1", 0, dist="Дикси Юг АО (take-off) с 01.04.2018")
    r_d2 = make_row(2, "ДИКСИ-77007", "Москва г, ул. Тверская, дом 1", 0, dist="Дикси Юг АО (take-off) с 01.04.2018")
    r_d3 = make_row(3, "ДИКСИ-50879", "Москва г, Тверская ул, 1", 0, dist="Дикси Юг АО (take-off) с 01.04.2018")

    # Metro
    r_m1 = make_row(4, "МЕТРО 52", "Москва г, Ленинградское ш, 71", 0, dist="МЕТРО КЭШ ЭНД КЕРРИ ООО (take-off) с 01.04.2018")
    r_m2 = make_row(5, "52", "Москва г, Ленинградское ш, 71", 0, dist="МЕТРО КЭШ ЭНД КЕРРИ ООО (take-off) с 01.04.2018")
    r_m3 = make_row(6, "МЕТРО 318", "Москва г, Ленинградское ш, 71", 0, dist="МЕТРО КЭШ ЭНД КЕРРИ ООО (take-off) с 01.04.2018")

    records = [
        OutletRecord(0, r_d1, COL_INDICES),
        OutletRecord(1, r_d2, COL_INDICES),
        OutletRecord(2, r_d3, COL_INDICES),
        OutletRecord(3, r_m1, COL_INDICES),
        OutletRecord(4, r_m2, COL_INDICES),
        OutletRecord(5, r_m3, COL_INDICES),
    ]
    dedup = OutletsDeduplicator(records)
    results = dedup.run()

    assert len(results) == 6

    # Dixi groups
    d1 = [r for r in results if r[2][COL_INDICES['id']] == '1'][0]
    d2 = [r for r in results if r[2][COL_INDICES['id']] == '2'][0]
    d3 = [r for r in results if r[2][COL_INDICES['id']] == '3'][0]

    assert d1[0] == d2[0]
    assert d1[1] == STATUS_IDENTICAL
    assert d2[1] == STATUS_IDENTICAL
    assert d3[0] != d1[0]
    assert d3[1] == STATUS_UNIQUE

    # Metro groups
    m1 = [r for r in results if r[2][COL_INDICES['id']] == '4'][0]
    m2 = [r for r in results if r[2][COL_INDICES['id']] == '5'][0]
    m3 = [r for r in results if r[2][COL_INDICES['id']] == '6'][0]

    assert m1[0] == m2[0]
    assert m1[1] == STATUS_IDENTICAL
    assert m2[1] == STATUS_IDENTICAL
    assert m3[0] != m1[0]
    assert m3[1] == STATUS_UNIQUE


def test_perekrestok_strict_subnetwork_matching():
    """
    Verify that ПЕРЕКРЕСТОК ТД АО matches strictly by Name + Подсеть:
    - Same Name and same Подсеть -> identical.
    - Same Name, different Подсеть -> do NOT merge.
    - Different Name -> do NOT merge.
    """
    r1 = make_row(10, "Супермаркет_2196", "Ростовская обл, Новочеркасск г, Платовский пр-кт, 59А", 0,
                  dist="ПЕРЕКРЕСТОК ТД АО", subnetwork="Ru_Перекресток")
    r2 = make_row(20, "Супермаркет_2196", "Ростовская обл. г.Новочеркасск, Платовский пр-т 59 А", 0,
                  dist="ПЕРЕКРЕСТОК ТД АО", subnetwork="Ru_Перекресток")
    # Different subnetwork (Карусель)
    r3 = make_row(30, "Супермаркет_2196", "Ростовская обл, Новочеркасск г, Платовский пр-кт, 59А", 0,
                  dist="ПЕРЕКРЕСТОК ТД АО", subnetwork="Ru_Карусель")
    # Different name
    r4 = make_row(40, "Супермаркет_2116", "Ростовская обл, Новочеркасск г, Платовский пр-кт, 59А", 0,
                  dist="ПЕРЕКРЕСТОК ТД АО", subnetwork="Ru_Перекресток")

    records = [
        OutletRecord(0, r1, COL_INDICES),
        OutletRecord(1, r2, COL_INDICES),
        OutletRecord(2, r3, COL_INDICES),
        OutletRecord(3, r4, COL_INDICES),
    ]
    dedup = OutletsDeduplicator(records)
    results = dedup.run()

    assert len(results) == 4
    # r1 and r2 merged
    assert results[0][0] == results[1][0]
    assert results[0][1] == STATUS_IDENTICAL
    assert results[1][1] == STATUS_IDENTICAL

    # r3 and r4 in separate unique groups
    assert results[2][0] != results[0][0]
    assert results[3][0] != results[0][0]
    assert results[2][0] != results[3][0]
    assert results[2][1] == STATUS_UNIQUE
    assert results[3][1] == STATUS_UNIQUE


def test_auchan_and_lenta_3digit_code_padding():
    """
    Verify 1- and 2-digit store codes are padded to 3 digits for Ашан and Лента:
    - ID 88664618376834150 (name '1') and ID 88664618385207909 (name '(001) MYTISHI') merge!
    - ID 88664618376833599 (name '36') and ID 88664617663859091 (name 'Ашан (036) KUNCEVO') merge!
    - Lenta 'Лента 1' and 'Лента 001' merge!
    """
    # Auchan example 1: 1 and (001) MYTISHI
    r_a1 = make_row("88664618376834150", "1", "Московская обл, Мытищи г, Осташковское ш, 1", 0,
                    dist="АШАН ООО (take-off) с 01.04.2018")
    r_a2 = make_row("88664618385207909", "(001) MYTISHI", "Московская область,гМытищи,Осташковское шоссе, 1, МКАД 91 км", 0,
                    dist="АШАН ООО (take-off) с 01.04.2018")

    # Auchan example 2: 36 and Ашан (036) KUNCEVO
    r_a3 = make_row("88664618376833599", "36", "Москва г, Ярцевская ул, 19", 0,
                    dist="АШАН ООО (take-off) с 01.04.2018")
    r_a4 = make_row("88664617663859091", "Ашан (036) KUNCEVO", "Московская область,гМосква,ул. Ярцевская, д.19,стр.1", 0,
                    dist="АШАН ООО (take-off) с 01.04.2018")

    # Lenta example: Лента 5 and Лента 005
    r_l1 = make_row("101", "Лента 5", "г. Санкт-Петербург, ул. Савушкина, 112", 0,
                    dist="Лента ООО (take-off) с 01.04.2018")
    r_l2 = make_row("102", "Лента 005", "Санкт-Петербург, Савушкина ул, 112", 0,
                    dist="Лента ООО (take-off) с 01.04.2018")

    records = [
        OutletRecord(0, r_a1, COL_INDICES),
        OutletRecord(1, r_a2, COL_INDICES),
        OutletRecord(2, r_a3, COL_INDICES),
        OutletRecord(3, r_a4, COL_INDICES),
        OutletRecord(4, r_l1, COL_INDICES),
        OutletRecord(5, r_l2, COL_INDICES),
    ]
    dedup = OutletsDeduplicator(records)
    results = dedup.run()

    assert len(results) == 6

    # Auchan group 1: 1 and 001
    res_a1 = [r for r in results if r[2][COL_INDICES['id']] == "88664618376834150"][0]
    res_a2 = [r for r in results if r[2][COL_INDICES['id']] == "88664618385207909"][0]
    assert res_a1[0] == res_a2[0]
    assert res_a1[1] == STATUS_IDENTICAL
    assert res_a2[1] == STATUS_IDENTICAL

    # Auchan group 2: 36 and 036
    res_a3 = [r for r in results if r[2][COL_INDICES['id']] == "88664618376833599"][0]
    res_a4 = [r for r in results if r[2][COL_INDICES['id']] == "88664617663859091"][0]
    assert res_a3[0] == res_a4[0]
    assert res_a3[1] == STATUS_IDENTICAL
    assert res_a4[1] == STATUS_IDENTICAL

    # Auchan groups are distinct
    assert res_a1[0] != res_a3[0]

    # Lenta group: 5 and 005
    res_l1 = [r for r in results if r[2][COL_INDICES['id']] == "101"][0]
    res_l2 = [r for r in results if r[2][COL_INDICES['id']] == "102"][0]
    assert res_l1[0] == res_l2[0]
    assert res_l1[1] == STATUS_IDENTICAL
    assert res_l2[1] == STATUS_IDENTICAL


