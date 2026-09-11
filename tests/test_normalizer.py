import pytest
from normalizer import (
    extract_house_components, extract_store_code,
    clean_store_name, extract_address_details, get_address_blocking_keys
)

def test_house_extraction():
    assert extract_house_components("ул. Ленина, д. 5")[0] == "5"
    assert extract_house_components("ул. Ленина, д. 5а")[1] == "5а"
    assert extract_house_components("Татищева бульвар, 6а")[1] == "6а"
    assert extract_house_components("Братьев Радченко улица, 33\\19")[1] == "33/19"
    assert extract_house_components("Заводской проезд зд.7 к.4")[1] == "7к4"
    assert extract_house_components("Москва г, Академика Волгина ул, 15, к 3") == ("15", "15к3")
    assert extract_house_components("5268 ССИВ Москва г, ул Академика Волгина, д.15,к.3") == ("15", "15к3")
    assert extract_house_components("Москва г, Долгопрудная аллея, 15, к 4") == ("15", "15к4")
    assert extract_house_components("5282 ССИВ Москва г, аллея Долгопрудная, д.15, к. 4") == ("15", "15к4")
    assert extract_house_components("Московская обл, Наро-Фоминск г, Пожитково д, 30, стр 1") == ("30", "30к1")

def test_store_code_extraction():
    assert extract_store_code("Дискаунтер_H085") == "H085"
    assert extract_store_code("X5 H085") == "H085"
    assert extract_store_code("Люкс ООО маг.Малинка №604") == "604"
    assert extract_store_code("Перминов В.В ИП маг.Малинка № 604") == "604"
    assert extract_store_code("Спар №118") == "118"

def test_clean_store_name():
    assert "малинка 604" in clean_store_name("Люкс ООО маг.Малинка №604")
    assert "малинка 604" in clean_store_name("Перминов В.В ИП маг.Малинка № 604")
    assert "спар 118" in clean_store_name("Торговый центр Скиф ООО Спар №118")

def test_blocking_keys():
    keys = get_address_blocking_keys("Нижегородская обл, Бор г, Заводская ул, дом № 5а")
    assert len(keys) > 0
    # verify base house is '5' in all keys
    for token, base_h in keys:
        assert base_h == "5"
