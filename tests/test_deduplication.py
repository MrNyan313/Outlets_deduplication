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


def make_row(id_val, name, addr, is_vendor, dist="Сладкая жизнь плюс ООО"):
    return (
        str(id_val),
        name,
        "ООО Тест",
        addr,
        "Россия, " + addr,
        str(is_vendor),
        "Ru_Test",
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
