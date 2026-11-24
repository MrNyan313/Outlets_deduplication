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


def make_row(id_val, name, addr, is_vendor, dist="Сладкая жизнь плюс ООО", subnetwork="Ru_Test", street=None):
    return (
        str(id_val),
        name,
        "ООО Тест",
        addr,
        street if street is not None else ("Россия, " + addr),
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
    r_master = make_row(100, "X5 H085", "Пермский край, г. Кудымкар, ул. 50 лет Октября, 21", 1, "ПЯТЁРОЧКА")
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
    r_master = make_row(10, "Пятерочка 304S", "Ставропольский край, Ессентуки, Октябрьская улица, б\\н", 1, "ПЯТЁРОЧКА")
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
        dist="СОЮЗ СВ. ИОАННА ВОИНА ООО (take-off) с 01.04.2018"
    )
    r_dist_5282 = make_row(
        1327, "5282", "5282 ССИВ Москва г, аллея Долгопрудная, д.15, к. 4", 0,
        dist="СОЮЗ СВ. ИОАННА ВОИНА ООО (take-off) с 01.04.2018"
    )
    r_mast_5282 = make_row(
        476963, "5282", "Москва г, Долгопрудная аллея, 15, к 4", 1,
        dist="СОЮЗ СВ. ИОАННА ВОИНА ООО (take-off) с 01.04.2018"
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


def test_perekrestok_code_and_subnetwork_matching():
    """
    Verify that ПЕРЕКРЕСТОК ТД АО matches strictly by Store Code + Подсеть:
    - Same store code in Name and same Подсеть -> identical (even if Name string differs, e.g., 'Супермаркет_2280' vs 'Перекресток 2280').
    - Same store code, different Подсеть -> do NOT merge.
    - Different store code, same Подсеть -> do NOT merge.
    """
    r1 = make_row(10, "Супермаркет_2280", "Москва г, Совхозная ул, 41", 0,
                  dist="ПЕРЕКРЕСТОК ТД АО", subnetwork="Ru_Перекресток")
    r2 = make_row(20, "Перекресток 2280", "Москва, Совхозная ул, 41", 0,
                  dist="ПЕРЕКРЕСТОК ТД АО", subnetwork="Ru_Перекресток")
    r3 = make_row(30, "ПЕРЕКРЕСТОК ТД АО 2280 | совхозная-универсам", "г. Москва, ул. Совхозная, д. 41", 0,
                  dist="ПЕРЕКРЕСТОК ТД АО", subnetwork="Ru_Перекресток")
    # Different subnetwork (Карусель)
    r4 = make_row(40, "Супермаркет_2280", "Москва г, Совхозная ул, 41", 0,
                  dist="ПЕРЕКРЕСТОК ТД АО", subnetwork="Ru_Карусель")
    # Different code (2281)
    r5 = make_row(50, "Супермаркет_2281", "Москва г, Совхозная ул, 41", 0,
                  dist="ПЕРЕКРЕСТОК ТД АО", subnetwork="Ru_Перекресток")

    records = [
        OutletRecord(0, r1, COL_INDICES),
        OutletRecord(1, r2, COL_INDICES),
        OutletRecord(2, r3, COL_INDICES),
        OutletRecord(3, r4, COL_INDICES),
        OutletRecord(4, r5, COL_INDICES),
    ]
    dedup = OutletsDeduplicator(records)
    results = dedup.run()

    assert len(results) == 5
    res1 = [r for r in results if r[2][COL_INDICES['id']] == '10'][0]
    res2 = [r for r in results if r[2][COL_INDICES['id']] == '20'][0]
    res3 = [r for r in results if r[2][COL_INDICES['id']] == '30'][0]
    res4 = [r for r in results if r[2][COL_INDICES['id']] == '40'][0]
    res5 = [r for r in results if r[2][COL_INDICES['id']] == '50'][0]

    # r1, r2, r3 merged into the same group
    assert res1[0] == res2[0] == res3[0]
    assert res1[1] == STATUS_IDENTICAL
    assert res2[1] == STATUS_IDENTICAL
    assert res3[1] == STATUS_IDENTICAL

    # r4 (different subnetwork) and r5 (different code) are separate unique groups
    assert res4[0] != res1[0]
    assert res5[0] != res1[0]
    assert res4[0] != res5[0]
    assert res4[1] == STATUS_UNIQUE
    assert res5[1] == STATUS_UNIQUE


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


def test_globus_hypermarket_full_and_short_address_matching():
    """
    For 'ГИПЕРГЛОБУС ООО (take-off)':
    - Full-address records at the same hypermarket (e.g. 'Гипер Глобус Владимир 2', 'Глобус ВЛД', 'ВЛД', 'Владимир')
      must ALL merge into the SAME group with STATUS_IDENTICAL (100%).
    - A short-address record (Name: 'ВЛД', Addr: 'ВЛД') matching a full-address group must be added to that SAME
      group, but marked as STATUS_SIMILAR.
    """
    dist = "ГИПЕРГЛОБУС ООО (take-off)"
    # 4 full-address records at Suzdalskiy pr-kt 28
    r_full1 = make_row(1, "Гипер Глобус  Владимир 2", "Владимир, Суздальский пр-т, д. 28,", 0, dist=dist, subnetwork="Ru_Globus")
    r_full2 = make_row(2, "Владимир", "Владимир, Суздальский пр-т, д. 28,", 0, dist=dist, subnetwork="Ru_Globus")
    r_full3 = make_row(3, "Глобус ВЛД", "Владимирская обл, Владимир г, Суздальский пр-кт, 28", 0, dist=dist, subnetwork="Ru_Globus")
    r_full4 = make_row(4, "ВЛД", "Владимирская обл, Владимир г, Суздальский пр-кт, 28", 0, dist=dist, subnetwork="Ru_Globus")
    # 1 short-address record
    r_short = make_row(5, "ВЛД", "ВЛД", 0, dist=dist, subnetwork="Ru_Globus")

    records = [
        OutletRecord(0, r_full1, COL_INDICES),
        OutletRecord(1, r_full2, COL_INDICES),
        OutletRecord(2, r_full3, COL_INDICES),
        OutletRecord(3, r_full4, COL_INDICES),
        OutletRecord(4, r_short, COL_INDICES),
    ]
    dedup = OutletsDeduplicator(records)
    results = dedup.run(include_similarity=True)

    assert len(results) == 5
    # All 5 must share the exact same group ID!
    group_ids = {r[0] for r in results}
    assert len(group_ids) == 1

    # Check statuses
    res_full1 = [r for r in results if r[2][COL_INDICES['id']] == '1'][0]
    res_full2 = [r for r in results if r[2][COL_INDICES['id']] == '2'][0]
    res_full3 = [r for r in results if r[2][COL_INDICES['id']] == '3'][0]
    res_full4 = [r for r in results if r[2][COL_INDICES['id']] == '4'][0]
    res_short = [r for r in results if r[2][COL_INDICES['id']] == '5'][0]

    assert res_full1[1] == STATUS_IDENTICAL
    assert res_full1[3] == 100.0
    assert res_full2[1] == STATUS_IDENTICAL
    assert res_full2[3] == 100.0
    assert res_full3[1] == STATUS_IDENTICAL
    assert res_full3[3] == 100.0
    assert res_full4[1] == STATUS_IDENTICAL
    assert res_full4[3] == 100.0

    # Short record is added to the group as SIMILAR
    assert res_short[1] == STATUS_SIMILAR
    assert res_short[3] == 75.0


def test_globus_short_address_only_matching():
    """
    If there are only short-address records (no full-address counterpart in the dataset),
    they merge with each other as STATUS_IDENTICAL.
    """
    dist = "ГИПЕРГЛОБУС ООО (take-off)"
    r1 = make_row(10, "ОДН", "ОДН", 0, dist=dist, subnetwork="Ru_Globus")
    r2 = make_row(20, "ОДН", "ОДН", 0, dist=dist, subnetwork="Ru_Globus")

    records = [
        OutletRecord(0, r1, COL_INDICES),
        OutletRecord(1, r2, COL_INDICES),
    ]
    dedup = OutletsDeduplicator(records)
    results = dedup.run(include_similarity=True)

    assert len(results) == 2
    assert results[0][0] == results[1][0]
    assert results[0][1] == STATUS_IDENTICAL
    assert results[1][1] == STATUS_IDENTICAL
    assert results[0][3] == 100.0
    assert results[1][3] == 100.0


def test_globus_dynamic_acronym_matching_unknown_city():
    """
    Verify dynamic acronym matching for a new city not present in the dictionary.
    E.g. abbreviation 'НКР' matches 'Некрасовка' at the same street/house.
    """
    dist = "ГИПЕРГЛОБУС ООО (take-off)"
    r1 = make_row(100, "Глобус НКР", "Москва, Покровская ул, 10", 0, dist=dist, subnetwork="Ru_Globus")
    r2 = make_row(200, "Гипер Глобус Некрасовка", "Москва г, ул. Покровская, дом 10", 0, dist=dist, subnetwork="Ru_Globus")

    records = [
        OutletRecord(0, r1, COL_INDICES),
        OutletRecord(1, r2, COL_INDICES),
    ]
    dedup = OutletsDeduplicator(records)
    results = dedup.run(include_similarity=True)

    assert len(results) == 2
    assert results[0][0] == results[1][0]
    assert results[0][1] == STATUS_IDENTICAL
    assert results[1][1] == STATUS_IDENTICAL


def test_globus_different_cities_never_merge():
    """
    Different Globus stores (e.g. Vladimir vs Ryazan) must NEVER merge.
    """
    dist = "ГИПЕРГЛОБУС ООО (take-off)"
    r_vld = make_row(1, "Глобус ВЛД", "Владимирская обл, Владимир г, Суздальский пр-кт, 28", 0, dist=dist, subnetwork="Ru_Globus")
    r_ryaz = make_row(2, "Глобус РЯЗ", "Рязанская обл, Рязанский р-н, Дядьково с, 1", 0, dist=dist, subnetwork="Ru_Globus")

    records = [
        OutletRecord(0, r_vld, COL_INDICES),
        OutletRecord(1, r_ryaz, COL_INDICES),
    ]
    dedup = OutletsDeduplicator(records)
    results = dedup.run()

    assert len(results) == 2
    assert results[0][0] != results[1][0]
    assert results[0][1] == STATUS_UNIQUE
    assert results[1][1] == STATUS_UNIQUE


def test_globus_elektrostal_address_variants_merge():
    """
    Records with different address formulations (e.g. 'Массив 1 тер, стр 2' vs 'массив 1, стр. 2')
    and short address records ('ЭЛС') must all merge into a single group for that hypermarket.
    """
    dist = "ГИПЕРГЛОБУС ООО (take-off)"
    r1 = make_row(101, "Гипер Глобус  Электросталь 9", "Электросталь, Ногинский р-н, пос. Случайный, массив 1, стр. 2,", 0, dist=dist, subnetwork="Ru_Globus")
    r2 = make_row(102, "ЭЛС", "Московская обл, Электросталь г, Случайный п, Массив 1 тер, стр 2", 0, dist=dist, subnetwork="Ru_Globus")
    r3 = make_row(103, "ЭЛС", "ЭЛС", 0, dist=dist, subnetwork="Ru_Globus")

    records = [
        OutletRecord(0, r1, COL_INDICES),
        OutletRecord(1, r2, COL_INDICES),
        OutletRecord(2, r3, COL_INDICES),
    ]
    dedup = OutletsDeduplicator(records)
    results = dedup.run(include_similarity=True)

    assert len(results) == 3
    # All 3 records must be in the same group!
    assert results[0][0] == results[1][0] == results[2][0]

    # Full address records must be STATUS_IDENTICAL (100.0%)
    res_full1 = [r for r in results if r[2][COL_INDICES['id']] == '101'][0]
    res_full2 = [r for r in results if r[2][COL_INDICES['id']] == '102'][0]
    res_short = [r for r in results if r[2][COL_INDICES['id']] == '103'][0]

    assert res_full1[1] == STATUS_IDENTICAL
    assert res_full1[3] == 100.0
    assert res_full2[1] == STATUS_IDENTICAL
    assert res_full2[3] == 100.0

    # Short address record must be STATUS_SIMILAR (75.0%)
    assert res_short[1] == STATUS_SIMILAR
    assert res_short[3] == 75.0


def test_detskiy_mir_different_streets_and_names_never_merge():
    """
    Two outlets in the same settlement with the same house number ('2')
    but on different streets (e.g. ул. Никитина vs ул. Хабарова) and with different mall names
    must NEVER merge into the same group.
    """
    dist = "ДЕТСКИЙ МИР ПАО"
    r1 = make_row(
        323696223217277690,
        "ДМ Московский Столица",
        "г.Москва, г.Московский,Никитина,2",
        0,
        dist=dist,
        subnetwork="Ru_Детский мир"
    )
    r2 = make_row(
        323696223217278702,
        "ДМ Московский Новомосковский",
        "Московский,ул.Хабарова,2",
        0,
        dist=dist,
        subnetwork="Ru_Детский мир"
    )

    records = [
        OutletRecord(0, r1, COL_INDICES),
        OutletRecord(1, r2, COL_INDICES),
    ]
    dedup = OutletsDeduplicator(records)
    results = dedup.run(include_similarity=True)

    assert len(results) == 2
    # Must NOT be in the same group!
    assert results[0][0] != results[1][0]
    # Both must be STATUS_UNIQUE
    assert results[0][1] == STATUS_UNIQUE
    assert results[1][1] == STATUS_UNIQUE


def test_detskiy_mir_naberezhnye_chelny_different_streets_never_merge():
    """
    Two Detskiy Mir outlets in Naberezhnye Chelny with base house '2'
    on different streets (Сююмбике пр-кт vs наб. Габдуллы Тукая)
    must NEVER merge into the same group.
    """
    dist = "ДЕТСКИЙ МИР ПАО"
    r1 = make_row(
        323696223217289820,
        "ДМ Набережные Челны Омега",
        "Набережные Челны,Сююмбике пр-кт,2/19",
        0,
        dist=dist,
        subnetwork="Ru_Детский мир"
    )
    r2 = make_row(
        323696223217290599,
        "ДМ Набережные Челны Эссен",
        "Набережные Челны,наб.Габдуллы Тукая,2",
        0,
        dist=dist,
        subnetwork="Ru_Детский мир"
    )

    records = [
        OutletRecord(0, r1, COL_INDICES),
        OutletRecord(1, r2, COL_INDICES),
    ]
    dedup = OutletsDeduplicator(records)
    results = dedup.run(include_similarity=True)

    assert len(results) == 2
    assert results[0][0] != results[1][0]
    assert results[0][1] == STATUS_UNIQUE
    assert results[1][1] == STATUS_UNIQUE


def test_detskiy_mir_identical_name_incomplete_address_matches_as_similar():
    """
    Detskiy Mir outlets with 100% identical store names but incomplete physical address
    (e.g. city only vs street only) must merge into the same group with STATUS_SIMILAR (75.0%).
    """
    dist = "ДЕТСКИЙ МИР ПАО"
    # Pair 1: Voronezh Lastochkino
    r1 = make_row(
        323696223230757975,
        "ДМ Воронеж Ласточкино",
        "г Воронеж",
        0,
        dist=dist,
        subnetwork="Ru_Детский мир"
    )
    r2 = make_row(
        323696223234410929,
        "ДМ Воронеж Ласточкино",
        "Острогожская",
        0,
        dist=dist,
        subnetwork="Ru_Детский мир"
    )
    # Pair 2: Yekaterinburg Megapolis
    r3 = make_row(
        323696223230757987,
        "ДМ Екатеринбург Мегаполис",
        "г Екатеринбург",
        0,
        dist=dist,
        subnetwork="Ru_Детский мир"
    )
    r4 = make_row(
        323696223234410937,
        "ДМ Екатеринбург Мегаполис",
        "8 марта",
        0,
        dist=dist,
        subnetwork="Ru_Детский мир"
    )

    records = [
        OutletRecord(0, r1, COL_INDICES),
        OutletRecord(1, r2, COL_INDICES),
        OutletRecord(2, r3, COL_INDICES),
        OutletRecord(3, r4, COL_INDICES),
    ]
    dedup = OutletsDeduplicator(records)
    results = dedup.run(include_similarity=True)

    assert len(results) == 4

    # Pair 1 must be in the same group
    res_vor1 = [r for r in results if r[2][COL_INDICES['id']] == '323696223230757975'][0]
    res_vor2 = [r for r in results if r[2][COL_INDICES['id']] == '323696223234410929'][0]
    assert res_vor1[0] == res_vor2[0]
    assert res_vor1[1] == STATUS_IDENTICAL
    assert res_vor2[1] == STATUS_SIMILAR
    assert res_vor2[3] == 75.0

    # Pair 2 must be in the same group
    res_ekb1 = [r for r in results if r[2][COL_INDICES['id']] == '323696223230757987'][0]
    res_ekb2 = [r for r in results if r[2][COL_INDICES['id']] == '323696223234410937'][0]
    assert res_ekb1[0] == res_ekb2[0]
    assert res_ekb1[1] == STATUS_IDENTICAL
    assert res_ekb2[1] == STATUS_SIMILAR
    assert res_ekb2[3] == 75.0

    # Pairs must be in different groups from each other
    assert res_vor1[0] != res_ekb1[0]


def test_detskiy_mir_format_separation():
    """
    Outlets of 'ДЕТСКИЙ МИР ПАО' with different format prefixes
    ('ДМ', 'ДМ МИНИ', 'ЗОО', 'РЦ') must NEVER merge with each other,
    even at the identical physical address.
    """
    dist = "ДЕТСКИЙ МИР ПАО"
    # Case 1: ДМ vs ЗОО at the exact same address (Видное, ул. Радужная, 2)
    r1 = make_row(101, "ДМ Видное Ларец", "Видное, Московской обл.,ул.Радужная,2", 0, dist=dist, subnetwork="Ru_Детский мир")
    r2 = make_row(102, "ЗОО Видное Ларец", "Видное,ул.Радужная,2", 0, dist=dist, subnetwork="Ru_Детский мир")

    # Case 2: ДМ vs ДМ МИНИ at the same address
    r3 = make_row(103, "ДМ Самара Аврора", "Самара, Аэродромная ул, д. 47", 0, dist=dist, subnetwork="Ru_Детский мир")
    r4 = make_row(104, "ДМ МИНИ Самара Аврора", "Самара, Аэродромная ул, д. 47", 0, dist=dist, subnetwork="Ru_Детский мир")

    # Case 3: ДМ vs РЦ
    r5 = make_row(105, "РЦ Крёкшино-ИМ", "д.Крекшино, Терминальный пр-зд, стр.4", 0, dist=dist, subnetwork="Ru_Детский мир")
    r6 = make_row(106, "ДМ Крёкшино-ИМ", "д.Крекшино, Терминальный пр-зд, стр.4", 0, dist=dist, subnetwork="Ru_Детский мир")

    records = [
        OutletRecord(0, r1, COL_INDICES),
        OutletRecord(1, r2, COL_INDICES),
        OutletRecord(2, r3, COL_INDICES),
        OutletRecord(3, r4, COL_INDICES),
        OutletRecord(4, r5, COL_INDICES),
        OutletRecord(5, r6, COL_INDICES),
    ]
    dedup = OutletsDeduplicator(records)
    results = dedup.run(include_similarity=True)

    # Every outlet must be in its own separate unique group
    group_ids = [r[0] for r in results]
    assert len(set(group_ids)) == 6
    for r in results:
        assert r[1] == STATUS_UNIQUE


def test_highway_km_deduplication_pyatnitskoe():
    """
    Outlets on a major highway recorded with variations (highway+km+house, km+house,
    trailing comma without house number, genitive vs nominative street forms,
    and border cities Moscow vs Krasnogorsk) must all merge into a single group.
    """
    dist = "ОКЕЙ ООО (take off)"
    r1 = make_row(1, "ГМ Москва Пятницкое", "Московская обл, Красногорск г, 7-й (автодорога Пятницкое шоссе тер.) км, 2", 0, dist=dist, subnetwork="Ru_О'Кей", street=" влд 2")
    r2 = make_row(2, "ГМ Москва Пятницкое", "Московская обл, Красногорск г, 7-й (автодорога Пятницкое шоссе тер.) км, 2", 0, dist=dist, subnetwork="Ru_О'Кей", street=" ")
    r3 = make_row(3, "ГМ Москва Пятницкое", "Московская обл, Красногорск г, 7-й км, 2", 0, dist=dist, subnetwork="Ru_О'Кей", street="Россия, Московская обл, Красногорск г, автодорога Пятницкое шоссе, 7-й км д 2")
    r4 = make_row(4, "ГМ Москва Пятницкое", "Москва г, Пятницкое ш, 7-й км, 2", 0, dist=dist, subnetwork="Ru_О'Кей", street=" ")
    r5 = make_row(5, "ГМ Москва Пятницкое", "Москва г, Пятницкое ш, 7-й км,", 0, dist=dist, subnetwork="Ru_О'Кей", street=" ")
    r6 = make_row(6, "ГМ Москва Пятницкое 7 км", "Московская область.,г.Москва,7 км Пятницкого ш., вл. 2", 0, dist=dist, subnetwork="Ru_О'Кей", street="Россия, Московская обл, Красногорск г, Отрадное п, Пятницкое ш ")

    records = [
        OutletRecord(0, r1, COL_INDICES),
        OutletRecord(1, r2, COL_INDICES),
        OutletRecord(2, r3, COL_INDICES),
        OutletRecord(3, r4, COL_INDICES),
        OutletRecord(4, r5, COL_INDICES),
        OutletRecord(5, r6, COL_INDICES),
    ]
    dedup = OutletsDeduplicator(records)
    results = dedup.run(include_similarity=True)

    # All 6 records must merge into ONE single group!
    group_ids = [r[0] for r in results]
    assert len(set(group_ids)) == 1
    # First record is group anchor (IDENTICAL), other matched records are IDENTICAL
    for r in results:
        assert r[1] == STATUS_IDENTICAL


def test_border_agglomeration_deduplication_tallinskoe():
    """
    Outlets on Tallinskoye Highway 27 recorded under Saint Petersburg vs Leningrad Oblast (Villozi / Lomonosovsky)
    must merge into one group with STATUS_IDENTICAL.
    """
    dist = "ОКЕЙ ООО (take off)"
    r1 = make_row(10, "ГМ СПб Таллинское", "Ленинградская обл, Ломоносовский р-н, Таллинское ш, 27", 0, dist=dist, subnetwork="Ru_О'Кей", street="Россия, Ленинградская обл, Ломоносовский р-н, Виллози гп, Дом 27 ")
    r2 = make_row(20, "ГМ СПб Таллинское", "Ленинградская обл, Ломоносовский р-н, Виллози гп, Таллинское ш, 27", 0, dist=dist, subnetwork="Ru_О'Кей", street="Россия, Ленинградская обл, Ломоносовский р-н, Таллинское ш д 27")
    r3 = make_row(30, "ГМ СПб Таллинское", "Ленинградская обл, Ломоносовский р-н, Виллози д, Таллинское ш, 27", 0, dist=dist, subnetwork="Ru_О'Кей", street="Россия, Ленинградская обл, Ломоносовский р-н, Виллози гп, Дом 27 ")
    r4 = make_row(40, "ГМ СПб Таллинское", "Санкт-Петербург г, Таллинское ш, 27", 0, dist=dist, subnetwork="Ru_О'Кей", street="Россия, Санкт-Петербург г, Старо-Паново, Таллинское ш д 27")
    r5 = make_row(50, "ГМ СПб Таллинское", "Ленинградская обл, Ломоносовский р-н, Таллинское ш, 27", 0, dist=dist, subnetwork="Ru_О'Кей", street="Россия, Ленинградская обл, Ломоносовский р-н, Таллинское ш д 27")

    records = [
        OutletRecord(0, r1, COL_INDICES),
        OutletRecord(1, r2, COL_INDICES),
        OutletRecord(2, r3, COL_INDICES),
        OutletRecord(3, r4, COL_INDICES),
        OutletRecord(4, r5, COL_INDICES),
    ]
    dedup = OutletsDeduplicator(records)
    results = dedup.run(include_similarity=True)

    # All 5 records must merge into ONE single group!
    group_ids = [r[0] for r in results]
    assert len(set(group_ids)) == 1
    for r in results:
        assert r[1] == STATUS_IDENTICAL


def test_national_network_coverage_scoping_semicolon_distributors():
    """
    Coverage points (IsVendor == 1) specify semicolon-separated distributor names
    in 'Дистрибьютор'. National retail networks (NATIONAL_NETWORKS) are strictly scoped:
    - Coverage point ONLY matches national distributors that are listed in its distributor column.
    - National distributors NOT listed in the semicolon string are strictly rejected (score 0.0).
    - Regular non-national distributors are NOT subject to this restriction and can match.
    """
    from deduplicator import calculate_outlet_match_score

    # 1. Master point with 2 national distributors allowed
    r_master = make_row(
        100, "Ашан 045", "Москва г, ул. Вавилова, 3", 1,
        dist="АШАН ООО (take-off) с 01.04.2018; ОКЕЙ ООО (take off)"
    )
    rec_master = OutletRecord(0, r_master, COL_INDICES)
    assert rec_master.allowed_distributors == {
        "АШАН ООО (take-off) с 01.04.2018",
        "ОКЕЙ ООО (take off)",
    }

    # 1a. Matching national distributor (АШАН)
    r_ashan = make_row(201, "АШАН 045", "Москва г, ул. Вавилова, 3", 0, dist="АШАН ООО (take-off) с 01.04.2018")
    rec_ashan = OutletRecord(1, r_ashan, COL_INDICES)
    score_ashan, exact_ashan = calculate_outlet_match_score(rec_master, rec_ashan)
    assert exact_ashan is True
    assert score_ashan >= 95.0

    # 1b. Matching national distributor (О'КЕЙ)
    r_okey = make_row(202, "ГМ ОКЕЙ Вавилова", "Москва г, ул. Вавилова, 3", 0, dist="ОКЕЙ ООО (take off)", subnetwork="Ru_О'Кей")
    rec_okey = OutletRecord(2, r_okey, COL_INDICES)
    score_okey, _ = calculate_outlet_match_score(rec_master, rec_okey)
    assert score_okey > 0.0

    # 1c. Non-allowed national distributor (ПЯТЁРОЧКА) with identical store code & address -> STRICT REJECT
    r_pyat = make_row(203, "Пятерочка 045", "Москва г, ул. Вавилова, 3", 0, dist="ПЯТЁРОЧКА")
    rec_pyat = OutletRecord(3, r_pyat, COL_INDICES)
    score_pyat, exact_pyat = calculate_outlet_match_score(rec_master, rec_pyat)
    assert exact_pyat is False
    assert score_pyat == 0.0

    # 1d. Non-allowed national distributor (ТАНДЕР / Магнит) with identical address -> STRICT REJECT
    r_magnit = make_row(204, "Магнит", "Москва г, ул. Вавилова, 3", 0, dist="ТАНДЕР АО (take-off) с 01.04.2018", subnetwork="Ru_Магнит")
    rec_magnit = OutletRecord(4, r_magnit, COL_INDICES)
    score_magnit, exact_magnit = calculate_outlet_match_score(rec_master, rec_magnit)
    assert exact_magnit is False
    assert score_magnit == 0.0

    # 2. Master point with regular distributor (Сплат?Глобал)
    r_master_splat = make_row(300, "Магазин Продукты", "Москва г, ул. Ленина, 10", 1, dist="Сплат?Глобал")
    rec_master_splat = OutletRecord(5, r_master_splat, COL_INDICES)

    # 2a. National distributor (ПЯТЁРОЧКА) -> strictly rejected
    r_pyat_splat = make_row(301, "Магазин Продукты", "Москва г, ул. Ленина, 10", 0, dist="ПЯТЁРОЧКА")
    rec_pyat_splat = OutletRecord(6, r_pyat_splat, COL_INDICES)
    score_splat_pyat, _ = calculate_outlet_match_score(rec_master_splat, rec_pyat_splat)
    assert score_splat_pyat == 0.0

    # 2b. Regular distributor (Сладкая жизнь плюс ООО) -> allowed to match
    r_reg = make_row(302, "Магазин Продукты", "Москва г, ул. Ленина, 10", 0, dist="Сладкая жизнь плюс ООО")
    rec_reg = OutletRecord(7, r_reg, COL_INDICES)
    score_reg, exact_reg = calculate_outlet_match_score(rec_master_splat, rec_reg)
    assert exact_reg is True
    assert score_reg >= 95.0

    # 3. Full end-to-end deduplication pipeline check
    dedup = OutletsDeduplicator([rec_master, rec_ashan, rec_pyat, rec_magnit])
    results = dedup.run(include_similarity=True)
    res_by_id = {r[2][0]: r for r in results}

    # rec_master (100) and rec_ashan (201) are merged into one group
    assert res_by_id["100"][0] == res_by_id["201"][0]
    assert res_by_id["201"][1] == STATUS_IDENTICAL

    # rec_pyat (203) and rec_magnit (204) are unique groups, NOT merged with rec_master
    assert res_by_id["203"][0] != res_by_id["100"][0]
    assert res_by_id["203"][1] == STATUS_UNIQUE
    assert res_by_id["204"][0] != res_by_id["100"][0]
    assert res_by_id["204"][1] == STATUS_UNIQUE


def test_kamalov_family_reregistration_same_address_identical():
    """
    Outlets with the exact same physical address + same normalized (surname, patronymic)
    merge as STATUS_IDENTICAL (100%), while same surname with different patronymic does not.
    """
    r_m = make_row(1, "ИП КАМАЛОВ МАЗАХИР ТЕЛЬМАН ОГЛЫ", "109125, Москва г, Саратовская ул, дом № 24", 1, dist="АГОРА КОМПАНИЯ ООО")
    r_d = make_row(2, "ИП Камалов Дилгам Тельман оглы", "109125, Москва г, Саратовская ул, дом № 24", 0, dist="АГОРА КОМПАНИЯ ООО")
    r_w = make_row(3, "ИП Прокофьева Ульяна Алексеевна НАЛ", "462114, Оренбургская обл, Черный Отрог с, д. 10", 0, dist="Семыкин Вадим Иванович ИП")
    r_h = make_row(4, "ИП Прокофьев Алексей Валерьевич 7 дн", "462114, Оренбургская обл, Черный Отрог с, д. 10", 0, dist="Семыкин Вадим Иванович ИП")

    records = [
        OutletRecord(0, r_m, COL_INDICES),
        OutletRecord(1, r_d, COL_INDICES),
        OutletRecord(2, r_w, COL_INDICES),
        OutletRecord(3, r_h, COL_INDICES),
    ]
    results = OutletsDeduplicator(records).run(include_similarity=True)
    res_by_id = {r[2][0]: r for r in results}

    assert res_by_id["1"][0] == res_by_id["2"][0]
    assert res_by_id["1"][1] == STATUS_IDENTICAL
    assert res_by_id["2"][1] == STATUS_IDENTICAL
    assert res_by_id["2"][3] == 100.0

    # Different patronymics are NOT merged by the family rule
    assert res_by_id["3"][0] != res_by_id["4"][0]


def test_vokzal_savelovsky_vs_kievsky_separated_and_similarity_consistent():
    """
    Savelyovsky Vokzal vs Kievsky Vokzal must NOT merge despite shared word 'вокзала'.
    One-sided stroenie ('д. 2' vs 'д. 2, стр. 16') stays STATUS_SIMILAR with Similarity % < 95.
    """
    r_sav_m = make_row(1, 'ООО "ТНП Торг"', "127015, Москва г, Савёловского Вокзала пл, дом № 2", 1, dist="АГОРА КОМПАНИЯ ООО", street="Россия, Москва г, Савёловского Вокзала пл, Дом 2")
    r_kiev_1 = make_row(2, 'ООО "ТНП Торг"', "121059, Москва г, Киевского Вокзала пл, дом № 2", 0, dist="АГОРА КОМПАНИЯ ООО", street="Россия, Москва г, Киевского Вокзала пл, Дом 2")
    r_kiev_2 = make_row(3, "ТНП ТОРГ ООО", "121059, Москва г, Киевского Вокзала пл, дом № 2", 0, dist="ЮРВЕС ООО", street="Россия, Москва г, Киевского Вокзала пл, Дом 2")
    r_sav_16 = make_row(4, "ТНП ТОРГ ООО", "г. Москва, пл. Савеловского вокзала, д. 2, стр. 16, магазин МАНДАРИН", 0, dist="ЮРВЕС ООО", street=" ")

    records = [OutletRecord(i, r, COL_INDICES) for i, r in enumerate([r_sav_m, r_kiev_1, r_kiev_2, r_sav_16])]
    results = OutletsDeduplicator(records).run(include_similarity=True)
    res_by_id = {r[2][0]: r for r in results}

    # Savelyovsky master + str. 16 share group, str. 16 is SIMILAR with < 95%
    assert res_by_id["1"][0] == res_by_id["4"][0]
    assert res_by_id["4"][1] == STATUS_SIMILAR
    assert res_by_id["4"][3] < 95.0

    # Kievsky points form their own separate IDENTICAL group
    assert res_by_id["2"][0] == res_by_id["3"][0]
    assert res_by_id["2"][0] != res_by_id["1"][0]
    assert res_by_id["2"][1] == STATUS_IDENTICAL
    assert res_by_id["3"][1] == STATUS_IDENTICAL


def test_korpus_one_sided_similar_not_100_and_sklad_not_litera():
    """
    Case 41: 'дом № 57' vs 'дом № 57, корпус 1' -> STATUS_SIMILAR with Similarity % < 95 (not 100%).
    Case 43: 'дом № 3 СКЛАД' vs 'дом № 3' -> STATUS_IDENTICAL (100%), not misparsed as '3с'.
    """
    r41_m = make_row(10, "Каминская ИП Глинки 57", "295033, Крым Респ, Симферополь г, Глинки ул, дом № 57", 1, dist="АТЛАНТ ЮГ ООО")
    r41_d1 = make_row(11, "Каминская ИП Глинки 57", "295022, Крым Респ, Симферополь г, Глинки ул, дом № 57", 0, dist="АТЛАНТ ЮГ ООО")
    r41_d2 = make_row(12, "Каминская Л.Н.ИП", "295000, Республика Крым, Симферополь г, Глинки ул, дом № 57, корпус 1", 0, dist="ТД КИНЕТИКА ООО")

    r43_m = make_row(20, "Индивидуальный предприниматель Сорокина Татьяна Александровна_2", "353900, Краснодарский край, Новороссийск г, Бирюзова ул, дом № 3 СКЛАД", 1, dist="АТЛАНТ ЮГ ООО")
    r43_d = make_row(21, "Индивидуальный предприниматель Сорокина Татьяна Александровна", "353900, Краснодарский край, Новороссийск г, Бирюзова ул, дом № 3", 0, dist="АТЛАНТ ЮГ ООО")

    records = [OutletRecord(i, r, COL_INDICES) for i, r in enumerate([r41_m, r41_d1, r41_d2, r43_m, r43_d])]
    results = OutletsDeduplicator(records).run(include_similarity=True)
    res_by_id = {r[2][0]: r for r in results}

    assert res_by_id["10"][0] == res_by_id["11"][0] == res_by_id["12"][0]
    assert res_by_id["11"][1] == STATUS_IDENTICAL
    assert res_by_id["12"][1] == STATUS_SIMILAR
    assert res_by_id["12"][3] < 95.0

    assert res_by_id["20"][0] == res_by_id["21"][0]
    assert res_by_id["20"][1] == STATUS_IDENTICAL
    assert res_by_id["21"][1] == STATUS_IDENTICAL
    assert res_by_id["21"][3] == 100.0


def test_noise_cleaning_payment_tails_identical_at_95_threshold():
    """
    Payment/legal tails ('НАЛ', '7 дн', '21дн.', 'Индивидуальный предприниматель', 'ФЛП')
    are cleaned so identical outlets merge as STATUS_IDENTICAL even at 95% threshold.
    """
    r1 = make_row(1, "ИП Прокофьева Ульяна Алексеевна НАЛ", "462114, Оренбургская обл, Черный Отрог с, Ленина ул, д. 10", 0)
    r2 = make_row(2, "ИП Прокофьева Ульяна Алексеевна 7 дн", "462114, Оренбургская обл, Черный Отрог с, Ленина ул, д. 10", 0)
    r3 = make_row(3, "Индивидуальный предприниматель Дерягина Татьяна Николаевна", "347130, Ростовская обл, Селивановская ст-ца, Кооперативная ул, дом № 48", 0)
    r4 = make_row(4, "Дерягина Татьяна Николаевна ФЛП", "347130, Ростовская обл, Селивановская ст-ца, Кооперативная ул, дом № 48", 0)

    records = [OutletRecord(i, r, COL_INDICES) for i, r in enumerate([r1, r2, r3, r4])]
    results = OutletsDeduplicator(records).run(include_similarity=True)
    res_by_id = {r[2][0]: r for r in results}

    assert res_by_id["1"][0] == res_by_id["2"][0]
    assert res_by_id["1"][1] == STATUS_IDENTICAL
    assert res_by_id["2"][1] == STATUS_IDENTICAL
    assert res_by_id["3"][0] == res_by_id["4"][0]
    assert res_by_id["3"][1] == STATUS_IDENTICAL
    assert res_by_id["4"][1] == STATUS_IDENTICAL


def test_false_merges_prevented_streets_cities_and_fake_codes():
    """
    Regression checks for false merges detected in Capitals deduplication:
    - Eysk vs Sochi in Krasnodar Krai (ID 3874)
    - Narodnaya vs Narodnogo Opolcheniya in SPb (ID 1551)
    - Inghfarma Magas (Mutalieva) vs Magas Zabava (Kulieva) (ID 4066)
    - Pyaterochka 133 (Volskaya) vs Smart_NN 133 (Glushko) (ID 1952)
    """
    pairs = [
        (
            make_row(101, "Палехова Виктория Александровна", "353691, Краснодарский край, Ейский р-н, Ейск г, Шоссейный пер, дом № 2, корпус 7", 1),
            make_row(102, "Шляхова Наталия Александровна ИП", "354037, Краснодарский край, Сочи г, Шоссейная ул, дом 2б", 0),
        ),
        (
            make_row(201, "ООО ТК Прогресс", "193079, Санкт-Петербург г., Народная ул., дом 6, Лит. А", 1),
            make_row(202, 'ООО "ТК Прогресс"', "198216, Санкт-Петербург, Народного Ополчения пр, дом 6", 0),
        ),
        (
            make_row(301, "Ингфарма, Магас", "386001, Ингушетия Респ, Магас г, Х-Б.Муталиева ул, дом № 3", 1),
            make_row(302, "Магас Забава (Кулиева 3)", "Ингушетия,г.Магас,ул.Кулиева 3", 0),
        ),
        (
            make_row(401, "133 - г.Мск, п. Некрасовка, 1- г. Москва", "г. Москва г.Москва Вольская 1-z 17 1", 1, dist="ПЯТЁРОЧКА", street=" д 17"),
            make_row(402, "133 Москва, ул,Академика Глушко, 15", "117216, Город Москва г, Академика Глушко ул", 0, dist="Сладкая жизнь плюс ООО", street="Россия, Москва г, Академика Глушко ул "),
        ),
    ]

    for row_a, row_b in pairs:
        records = [OutletRecord(0, row_a, COL_INDICES), OutletRecord(1, row_b, COL_INDICES)]
        results = OutletsDeduplicator(records).run()
        # Master has no match -> excluded; distributor row is UNIQUE
        assert len(results) == 1
        assert results[0][2][0] == str(row_b[0])
        assert results[0][1] == STATUS_UNIQUE


def test_gorohov_noise_and_missing_patronymic_become_identical():
    """
    Cases 3705, 3707, 3721, 3732, 3743:
    - Missing patronymic FIO ('ЭСЕНАЛИЕВ МУРАДИН' vs 'ЭСЕНАЛИЕВ МУРАДИН РАМАЗАНОВИЧ') -> IDENTICAL.
    - 'за наличку', 'РОЗНИЦА', 'Т-12', 'эл.накл.', 'ЭДО' cleaned -> IDENTICAL.
    """
    pairs = [
        (
            make_row(1, "ЭСЕНАЛИЕВ МУРАДИН РАМАЗАНОВИЧ", "357015, Ставропольский край, м.о. Кочубеевский, с Балахоновское, ул Свободы, двлд. 153 пом 1-5", 1, street="Россия, Ставропольский край, Кочубеевский р-н, Балахоновское с, Свободы ул, Домовладение 153"),
            make_row(2, "ЭСЕНАЛИЕВ МУРАДИН ЭДО УПД", "357015, Ставропольский край, р-н Кочубеевский, с Балахоновское, ул Свободы, двлд. 153, м.о. Кочубеев", 0, street="Россия, Ставропольский край, Кочубеевский р-н, Балахоновское с, Свободы ул, Домовладение 153"),
        ),
        (
            make_row(3, "ТЕР-МАРТИРОСОВА ЭЛЬМИРА за наличку", "Александровское с, Красноармейская ул, д 618В", 1),
            make_row(4, "ТЕР-МАРТИРОСОВА ЭЛЬМИРА РОЗНИЦА", "Александровское с, Красноармейская ул, д 618В", 0),
        ),
        (
            make_row(5, "ДУЩЕНКО ЕЛЕНА эл.накл. Садовая Т-12", "Невинномысск ул.Садовая 8 магазин «АВС»", 1),
            make_row(6, "ДУЩЕНКО ЕЛЕНА эл.накл. Садовая розница", "Невинномысск ул.Садовая 8 магазин «АВС»", 0),
        ),
        (
            make_row(7, "Васильева Елена Т-12 Шпаковка  ЭЛ.НАКЛ.", "Михайловск Ул. Войкова 399/1 м-н Белорусской косметики Красотка", 1, street="Россия, Ставропольский край, Михайловск г, Войкова ул д 399/1М"),
            make_row(8, "Васильева Елена РОЗНИЦА  Шпаковка  ЭЛ.НАКЛ.", "Михайловск Ул. Войкова 399/1 м-н Белорусской косметики Косметичка", 0, street="Россия, Ставропольский край, Михайловск г, Войкова ул д 399/1М"),
        ),
    ]
    for m_row, d_row in pairs:
        records = [OutletRecord(0, m_row, COL_INDICES), OutletRecord(1, d_row, COL_INDICES)]
        results = OutletsDeduplicator(records).run(include_similarity=True)
        assert len(results) == 2
        assert results[0][0] == results[1][0]
        assert results[0][1] == STATUS_IDENTICAL
        assert results[1][1] == STATUS_IDENTICAL
        assert results[1][3] == 100.0


def test_conflicting_house_litera_and_korpus_never_merge_and_slash_korpus_equivalent():
    """
    Cases 3848, 3905, 3955:
    - 40А vs 40 Б -> NEVER merge (not even as Похожая).
    - дом 2 стр Б vs дом 2, корп. 16 vs корп. 24 -> NEVER merge across different korpus/stroenie.
    - дом № 35, корпус 12А vs дом 35/12А -> equivalent, merge as STATUS_IDENTICAL.
    """
    # 3848: 40А vs 40 Б
    r_40a = make_row(1, "Ярус ООО (Алексеевка)", "309850, Белгородская обл, Алексеевка г, 1-й Народный пер, дом № 40А", 1)
    r_40b = make_row(2, "Ярус ООО", "309850, Белгородская обл, Алексеевка г, Народный пер, дом № 40 Б", 0)
    res_3848 = OutletsDeduplicator([OutletRecord(0, r_40a, COL_INDICES), OutletRecord(1, r_40b, COL_INDICES)]).run()
    assert len(res_3848) == 1
    assert res_3848[0][1] == STATUS_UNIQUE

    # 3905: стр Б vs корп. 16 vs корп. 24
    r_strb = make_row(10, "Амизян Артур А. ИП", "350073, Краснодарский край, Краснодар г, им лётчика Позднякова ул, дом 2 стр Б", 1)
    r_k16 = make_row(11, "Амизян Артур А. ИП", "350073, Краснодарский край, Краснодар г, им лётчика Позднякова ул, дом 2, корп. 16", 0)
    r_k24 = make_row(12, "Амизян Артур А. ИП", "350073, Краснодарский край, Краснодар г, им лётчика Позднякова ул, дом 2, корп. 24", 0)
    res_3905 = OutletsDeduplicator([OutletRecord(i, r, COL_INDICES) for i, r in enumerate([r_strb, r_k16, r_k24])]).run()
    assert len(res_3905) == 2
    assert res_3905[0][0] != res_3905[1][0]
    assert res_3905[0][1] == STATUS_UNIQUE
    assert res_3905[1][1] == STATUS_UNIQUE

    # 3955: корпус 12А vs /12А -> IDENTICAL
    r_k12a = make_row(20, "Новый Квартал ООО", "354008, Краснодарский край, Сочи г, Рахманинова пер, дом № 35, корпус 12А", 1)
    r_s12a = make_row(21, "Новый-Квартал ООО", "354008, Краснодарский край, Сочи г, Рахманинова пер, дом 35/12А", 0)
    res_3955 = OutletsDeduplicator([OutletRecord(0, r_k12a, COL_INDICES), OutletRecord(1, r_s12a, COL_INDICES)]).run(include_similarity=True)
    assert len(res_3955) == 2
    assert res_3955[0][0] == res_3955[1][0]
    assert res_3955[1][1] == STATUS_IDENTICAL
    assert res_3955[1][3] == 100.0


def test_region_only_address_different_people_never_merge():
    """
    Case 13216: Identical region-only string ('Чувашская Республика') without city/street/house
    must not treat address as complete location -> different IP owners stay separate.
    """
    r1 = make_row(1, "Малахова Татьяна Леонидовна ИП", "Чувашская Республика", 0, street="Россия, Чувашская Республика - Чувашия ")
    r2 = make_row(2, "Москвина Светлана Леонидовна ИП", "Чувашская Республика", 0, street="Россия, Чувашская Республика - Чувашия ")
    results = OutletsDeduplicator([OutletRecord(0, r1, COL_INDICES), OutletRecord(1, r2, COL_INDICES)]).run()
    assert len(results) == 2
    assert results[0][0] != results[1][0]
    assert results[0][1] == STATUS_UNIQUE
    assert results[1][1] == STATUS_UNIQUE


def test_single_letter_litera_and_korpus_equivalence_and_conflict():
    """
    Cases 1218 & 1262:
    - Single-letter house litera ('7а', '1а') matches identical single-letter korpus ('7, корпус А', '1, корпус а') -> IDENTICAL.
    - Conflicting single-letter litera vs single-letter korpus ('7а' vs '7, корпус Б') -> NEVER merge.
    """
    # 1218: 7а vs 7, корпус А
    m1 = make_row(1, "ИП Алибекова Алиса Хаирбековна 30 дн", "462800, Оренбургская обл, Новоорский р-н, Новоорск п, Красноуральская ул, дом № 7а", 1, dist="Семыкин Вадим Иванович ИП; СПЛАТ ГЛОБАЛ")
    d1 = make_row(2, "ИП Алибекова Алиса Хаирбековна 21 дн", "462800, Оренбургская обл, Новоорский р-н, Новоорск п, Красноуральская ул, дом № 7, корпус А", 0, dist="Семыкин Вадим Иванович ИП")
    res1 = OutletsDeduplicator([OutletRecord(0, m1, COL_INDICES), OutletRecord(1, d1, COL_INDICES)]).run(include_similarity=True)
    assert len(res1) == 2
    assert res1[0][0] == res1[1][0]
    assert res1[0][1] == STATUS_IDENTICAL
    assert res1[1][1] == STATUS_IDENTICAL
    assert res1[1][3] == 100.0

    # 1262: д. 1а, кв. 8 vs дом № 1, корпус а, кв.8
    m2 = make_row(3, "ИП Сарсенова Альбина Ризовна", "РБ, г. Баймак, ул. Мира, д. 1а, кв. 8", 1, dist="Семыкин Вадим Иванович ИП; СПЛАТ ГЛОБАЛ")
    d2 = make_row(4, "ИП Сарсенова Альбина Ризовна 21 дн", "453632, Башкортостан Респ, Баймакский р-н, Баймак г, Мира ул, дом № 1, корпус а, кв.8", 0, dist="Семыкин Вадим Иванович ИП")
    res2 = OutletsDeduplicator([OutletRecord(0, m2, COL_INDICES), OutletRecord(1, d2, COL_INDICES)]).run(include_similarity=True)
    assert len(res2) == 2
    assert res2[0][0] == res2[1][0]
    assert res2[0][1] == STATUS_IDENTICAL
    assert res2[1][1] == STATUS_IDENTICAL
    assert res2[1][3] == 100.0

    # Negative: 7а vs 7, корпус Б -> NEVER merge
    d_conflict = make_row(5, "ИП Алибекова Алиса Хаирбековна 21 дн", "462800, Оренбургская обл, Новоорский р-н, Новоорск п, Красноуральская ул, дом № 7, корпус Б", 0, dist="Семыкин Вадим Иванович ИП")
    res3 = OutletsDeduplicator([OutletRecord(0, m1, COL_INDICES), OutletRecord(1, d_conflict, COL_INDICES)]).run()
    assert len(res3) == 1
    assert res3[0][1] == STATUS_UNIQUE


def test_no_house_addresses_aligned_to_similar():
    """
    Case 4108: Addresses without a house number ('б/н') must consistently be marked as STATUS_SIMILAR (75.0%),
    even when raw address strings happen to be literally identical ('г Москва, ул Наташи Ковшовой').
    """
    m = make_row(1, "ПЛЕС-С", "г Москва, ул Наташи Ковшовой", 1, dist="АГУР ООО; СПЛАТ ГЛОБАЛ", street="Россия, Москва г, Наташи Ковшовой ул ")
    d1 = make_row(2, "ПЛЕС-С", "г Москва, ул Наташи Ковшовой", 0, dist="АГУР ООО", street="Россия, Москва г, Наташи Ковшовой ул ")
    d2 = make_row(3, "ПЛЕС-С", "г. Москва, ул Наташи Ковшовой", 0, dist="АГУР ООО", street="Россия, Москва г, Наташи Ковшовой ул ")
    results = OutletsDeduplicator([
        OutletRecord(0, m, COL_INDICES),
        OutletRecord(1, d1, COL_INDICES),
        OutletRecord(2, d2, COL_INDICES),
    ]).run(include_similarity=True)

    assert len(results) == 3
    assert results[0][0] == results[1][0] == results[2][0]
    assert results[0][1] == STATUS_SIMILAR
    assert results[1][1] == STATUS_SIMILAR and results[1][3] == 75.0
    assert results[2][1] == STATUS_SIMILAR and results[2][3] == 75.0


def test_empty_address_rows_do_not_swallow_real_addresses_and_group_as_similar():
    """
    Cases 13157 & 18023:
    - Empty-address rows ('Чувашская Республика') must NEVER swallow real-addressed outlets of the same name.
    - Real-addressed outlets at 'Йошкар-Ола, ул Строителей 29А' across distributors merge into ONE IDENTICAL group.
    - Other cities stay separate.
    - Empty-address rows of the same (distributor, clean_name) group ONLY among themselves as STATUS_SIMILAR (75.0%).
    """
    rows = [
        make_row(1, "ПЛЕС-С", "Чувашская Республика", 0, dist="АГУР ООО", street="Россия, Чувашская Республика - Чувашия "),
        make_row(2, "ПЛЕС-С", "Чувашская Республика", 0, dist="АГУР ООО", street="Россия, Чувашская Республика - Чувашия "),
        make_row(3, "ПЛЕС-С", "Марий Эл, г Йошкар-Ола, ул Строителей 29А", 0, dist="АГУР ООО", street="Россия, Марий Эл Респ, Йошкар-Ола г, Строителей ул, Дом 29А "),
        make_row(4, "ПЛЕС-С", "Марий Эл, г Йошкар-Ола, ул Строителей 29А", 0, dist="АГУР ООО", street="Россия, Марий Эл Респ, Йошкар-Ола г, Строителей ул, Дом 29А "),
        make_row(5, "ПЛЕС-С", "г Барнаул, снт Кораблик, д 42", 0, dist="АГУР ООО", street="Россия, Алтайский край, Барнаул г, Кораблик снт д 42"),
        make_row(6, "ПЛЕС-С", "Марий Эл, г Йошкар-Ола, ул Строителей 29А", 0, dist="ОНАР-12 ООО", street="Россия, Марий Эл Респ, Йошкар-Ола г, Строителей ул, Дом 29А "),
        make_row(7, "ПЛЕС-С", "Марий Эл, г Йошкар-Ола, ул Строителей 29А", 0, dist="ОНАР-12 ООО", street="Россия, Марий Эл Респ, Йошкар-Ола г, Строителей ул, Дом 29А "),
    ]
    results = OutletsDeduplicator([OutletRecord(i, r, COL_INDICES) for i, r in enumerate(rows)]).run(include_similarity=True)
    by_id = {r[2][COL_INDICES['id']]: r for r in results}

    # 4 Yoshkar-Ola rows from both distributors -> ONE IDENTICAL group
    yoshkar_gids = {by_id[str(i)][0] for i in (3, 4, 6, 7)}
    assert len(yoshkar_gids) == 1
    for i in (3, 4, 6, 7):
        assert by_id[str(i)][1] == STATUS_IDENTICAL
        assert by_id[str(i)][3] == 100.0

    # Barnaul -> separate UNIQUE
    assert by_id['5'][1] == STATUS_UNIQUE
    assert by_id['5'][0] not in yoshkar_gids

    # 2 empty rows -> ONE group, both SIMILAR (75.0%), separate from real addresses
    assert by_id['1'][0] == by_id['2'][0]
    assert by_id['1'][0] not in yoshkar_gids
    assert by_id['1'][0] != by_id['5'][0]
    assert by_id['1'][1] == STATUS_SIMILAR and by_id['1'][3] == 75.0
    assert by_id['2'][1] == STATUS_SIMILAR and by_id['2'][3] == 75.0


def test_multilocation_name_key_disabled_while_single_location_preserved():
    """
    Multi-location regular (distributor, clean_name) disables the name-only blocking key so empty rows
    never attach randomly to one of multiple stores, while genuinely single-location IP owners still match.
    """
    # 1. Multi-location IP (2 stores + 2 empty rows): empty rows group only with each other as SIMILAR
    multi_rows = [
        make_row(10, "Гусева Елизавета Николаевна ИП", "Чувашская Республика", 0, dist="АГУР ООО", street="Россия, Чувашская Республика - Чувашия "),
        make_row(11, "Гусева Елизавета Николаевна ИП", "425450, Республика Марий Эл, пгт Сернур, ул Казанская, д. 15", 0, dist="АГУР ООО"),
        make_row(12, "Гусева Елизавета Николаевна ИП", "424000, Республика Марий Эл, г Йошкар-Ола, ул Ленина, д. 20", 0, dist="АГУР ООО"),
        make_row(13, "ГУСЕВА Елизавета Николаевна ИП", "Чувашская Республика", 0, dist="АГУР ООО", street="Россия, Чувашская Республика - Чувашия "),
    ]
    res_multi = OutletsDeduplicator([OutletRecord(i, r, COL_INDICES) for i, r in enumerate(multi_rows)]).run(include_similarity=True)
    by_id_m = {r[2][COL_INDICES['id']]: r for r in res_multi}
    assert by_id_m['11'][1] == STATUS_UNIQUE
    assert by_id_m['12'][1] == STATUS_UNIQUE
    assert by_id_m['10'][0] == by_id_m['13'][0]
    assert by_id_m['10'][0] not in {by_id_m['11'][0], by_id_m['12'][0]}
    assert by_id_m['10'][1] == STATUS_SIMILAR and by_id_m['10'][3] == 75.0
    assert by_id_m['13'][1] == STATUS_SIMILAR and by_id_m['13'][3] == 75.0

    # 2. Single-location IP (1 store + 1 empty row): still matches as SIMILAR with real store as leader
    single_rows = [
        make_row(20, "Малахова Татьяна Леонидовна ИП", "Чувашская Республика", 0, dist="АГУР ООО", street="Россия, Чувашская Республика - Чувашия "),
        make_row(21, "Малахова Татьяна Леонидовна ИП", "424019, Республика Марий Эл, г Йошкар-Ола, ул Красноармейская, д. 120Б", 0, dist="АГУР ООО"),
    ]
    res_single = OutletsDeduplicator([OutletRecord(i, r, COL_INDICES) for i, r in enumerate(single_rows)]).run(include_similarity=True)
    by_id_s = {r[2][COL_INDICES['id']]: r for r in res_single}
    assert by_id_s['20'][0] == by_id_s['21'][0]
    assert by_id_s['21'][1] == STATUS_IDENTICAL
    assert by_id_s['20'][1] == STATUS_SIMILAR and by_id_s['20'][3] == 75.0

    # 3. Multi-location spanning master + distrib (house 23 in master, house 25 in distrib + 1 empty row)
    mixed_rows = [
        make_row(30, "Кропотов Дмитрий Васильевич ИП", "425550, Марий Эл Респ, пгт Куженер, ул Советская, д. 23", 1, dist="АГУР ООО; СПЛАТ ГЛОБАЛ"),
        make_row(31, "Кропотов Дмитрий Васильевич ИП", "425550, Марий Эл Респ, пгт Куженер, ул Советская, д. 25", 0, dist="АГУР ООО"),
        make_row(32, "Кропотов Дмитрий Васильевич ИП", "Чувашская Республика", 0, dist="АГУР ООО", street="Россия, Чувашская Республика - Чувашия "),
    ]
    res_mixed = OutletsDeduplicator([OutletRecord(i, r, COL_INDICES) for i, r in enumerate(mixed_rows)]).run(include_similarity=True)
    by_id_x = {r[2][COL_INDICES['id']]: r for r in res_mixed}
    assert by_id_x['31'][0] != by_id_x['32'][0]
    assert by_id_x['31'][1] == STATUS_UNIQUE
    assert by_id_x['32'][1] == STATUS_UNIQUE


def test_mn_litera_volzhskiy_district_and_rural_settlement_become_identical():
    """
    Cases 5131, 5157, 5197, 5226, 5259 -> STATUS_IDENTICAL (100%):
    - 5131: 'р-н Волжский, пгт Приволжский' matches 'пос.Приволжский'.
    - 5157, 5197, 5226: 'д. 13 м-н', 'д. 29 м-н', 'д.10 м-н' do not turn into house literas '13м'/'29м'/'10м'.
    - 5259: 'Верх-Ушнур (Верх-Ушнурское с/п) с, дом № 1, корпус А' matches 'Верх-УШНУР с, д 1 А'.
    """
    pairs = [
        # 5131
        (
            make_row(1, "Кузьмина Елена Рудольфовна Договор 2022", "пос.Приволжский, ул.Рыночная площадь,7", 1, dist="АГУР ООО; СПЛАТ ГЛОБАЛ"),
            make_row(2, "Кузьмина Елена Рудольфовна ИП", "425030, Марий Эл Респ, р-н Волжский, пгт Приволжский, ул Рыночная площадь, д. 7", 0, dist="ОНАР-12 ООО"),
        ),
        # 5157
        (
            make_row(3, "Мила ООО (Чебоксары)", 'Чувашская Республика - Чувашия, р-н Вурнарский, пгт Вурнары, пер Зеленый, д. 13 м-н "Мила 2"', 1, dist="АГУР ООО; СПЛАТ ГЛОБАЛ", street="Россия, Чувашская Республика - Чувашия, Вурнарский р-н, Вурнары пгт, Зеленый пер д 13М"),
            make_row(4, "МИЛА ООО (Чебоксары)", "Чувашская Республика  пгт Вурнары, пер Зеленый, д. 13", 0, dist="ОНАР-12 ООО"),
        ),
        # 5197
        (
            make_row(5, "Яшина Людмила Викторовна ИП (Козьмодемьянск)", "425350, Марий Эл Респ, Козьмодемьянск г, Комсомольская 29,Континент", 1, dist="АГУР ООО; СПЛАТ ГЛОБАЛ"),
            make_row(6, "Яшина Людмила Викторовна ИП (Козьмодемьянск)", "Республика Марий Эл, г Козьмодемьянск, ул Комсомольская, д. 29 м-н Континент", 0, dist="ОНАР-12 ООО"),
        ),
        # 5226
        (
            make_row(7, "Иванова Алевтина Юрьевна", "Марий Эл Респ, р-н Куженерский, пгт Куженер, ул Совхозная, Дом 10", 1, dist="АГУР ООО; СПЛАТ ГЛОБАЛ"),
            make_row(8, "ИВАНОВА Алевтина Юрьевна", '425550, Республика Марий Эл, р-н Куженерский, пгт Куженер,  ул Совхозная д.10 м-н "ЛИДЕР"', 0, dist="ОНАР-12 ООО"),
        ),
        # 5259
        (
            make_row(9, "Михайлов Алексей Вадимович", '424039, 425418, Марий Эл Респ, Советский р-н, Верх-Ушнур (Верх-Ушнурское с/п) с, Центральная ул, дом № 1, корпус А, бокс м-н "Надежда"', 1, dist="АГУР ООО; СПЛАТ ГЛОБАЛ"),
            make_row(10, "МИХАЙЛОВ Алексей Вадимович", '424039, 425418, Марий Эл Респ, Советский р-н,  Верх-УШНУР с, Центральная ул, д 1 А,  м-н "Надежда"', 0, dist="ОНАР-12 ООО"),
        ),
        # Streetless village addresses (with and without parenthetical с/с) must still block & match identically
        (
            make_row(11, "Пестова О.Ю ИП", "606471, Нижегородская обл, Бор г, Рекшино (Кантауровский с/с) д, дом № 13", 1, dist="Сладкая жизнь плюс ООО; СПЛАТ ГЛОБАЛ"),
            make_row(12, "Пестова О.Ю ИП", "606471, Нижегородская обл, Бор г, Рекшино (Кантауровский с/с) д, дом № 13", 0, dist="Сладкая жизнь плюс ООО"),
        ),
    ]
    for m_row, d_row in pairs:
        results = OutletsDeduplicator([OutletRecord(0, m_row, COL_INDICES), OutletRecord(1, d_row, COL_INDICES)]).run(include_similarity=True)
        assert len(results) == 2
        assert results[0][0] == results[1][0]
        assert results[0][1] == STATUS_IDENTICAL
        assert results[1][1] == STATUS_IDENTICAL
        assert results[1][3] == 100.0


def test_numbered_and_lettered_streets_match_variants_and_reject_different_numbers():
    """
    - Matching numbered street variants ('1 Линия ул' vs '1-я Линия ул', 'пер 5-й' vs 'ул. 5-ый переулок',
      'микрорайон 5' vs '5-й мкр') merge as STATUS_IDENTICAL (100%).
    - Different numbered/lettered units in the same city with the same house number
      ('1 Линия д. 3' vs '2 Линия д. 3', 'В мкр д. 6' vs 'Г мкр д. 6') NEVER merge.
    """
    # Positive: 1 Линия == 1-я Линия, пер 5-й == ул. 5-ый переулок
    pos_pairs = [
        (
            make_row(1, "ИП Шарикова Светлана Юрьевна НАЛ.", "461047, Оренбургская обл, Бузулук г, 1 Линия ул, дом № 3", 1),
            make_row(2, "ИП Шарикова Светлана Юрьевна НАЛ", "461047, Оренбургская обл, Бузулук г, 1-я Линия ул, д. 3", 0),
        ),
        (
            make_row(3, "Думанов Константин Сергеевич", "385019, Республика Адыгея, г Майкоп, пер 5-й, д. 2", 1),
            make_row(4, "ДУМАНОВ КОНСТАНТИН СЕРГЕЕВИЧ", "385730, Адыгея Респ, г. Майкоп, ул. 5-ый переулок, д. 2", 0),
        ),
        (
            make_row(5, "Продпоставка ООО", "г. Байканур; микрорайон 5;д. 19А", 1),
            make_row(6, "Продпоставка ООО", "г. Байканур, 5-й мкр, д. 19А", 0),
        ),
        (
            make_row(7, "Магазин Продукты", "г. Енакиево, ул. 30 лет Победы, д. 12", 1),
            make_row(8, "Магазин Продукты", "г. Енакиево ул 30-летия Победы 12", 0),
        ),
    ]
    for m_row, d_row in pos_pairs:
        res = OutletsDeduplicator([OutletRecord(0, m_row, COL_INDICES), OutletRecord(1, d_row, COL_INDICES)]).run(include_similarity=True)
        assert len(res) == 2
        assert res[0][0] == res[1][0]
        assert res[0][1] == STATUS_IDENTICAL
        assert res[1][1] == STATUS_IDENTICAL
        assert res[1][3] == 100.0

    # Negative: 1 Линия vs 2 Линия, В мкр vs Г мкр, and 40 лет Октября vs 50 лет Октября must NEVER merge
    neg_pairs = [
        (
            make_row(10, "Магазин Продукты", "461047, Оренбургская обл, Бузулук г, 1 Линия ул, дом № 3", 0),
            make_row(11, "Магазин Продукты", "461047, Оренбургская обл, Бузулук г, 2 Линия ул, дом № 3", 0),
        ),
        (
            make_row(12, "Магазин Продукты", "142290, Московская область обл, Пущино г, В мкр, дом № 6", 0),
            make_row(13, "Магазин Продукты", "142290, Московская область обл, Пущино г, Г мкр, дом № 6", 0),
        ),
        (
            make_row(14, "Магазин Продукты", "г. Енакиево, ул. 40 лет Октября, д. 10", 0),
            make_row(15, "Магазин Продукты", "г. Енакиево, ул. 50 лет Октября, д. 10", 0),
        ),
        (
            make_row(16, "Магазин Продукты", "г. Енакиево, ул. 30 лет Победы, д. 10", 0),
            make_row(17, "Магазин Продукты", "г. Енакиево, ул. 50 лет Победы, д. 10", 0),
        ),
    ]
    for r1, r2 in neg_pairs:
        res = OutletsDeduplicator([OutletRecord(0, r1, COL_INDICES), OutletRecord(1, r2, COL_INDICES)]).run()
        assert len(res) == 2
        assert res[0][0] != res[1][0]
        assert res[0][1] == STATUS_UNIQUE
        assert res[1][1] == STATUS_UNIQUE









