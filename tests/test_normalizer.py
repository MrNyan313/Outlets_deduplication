import pytest
from normalizer import (
    extract_house_components, extract_store_code,
    clean_store_name, extract_address_details, get_address_blocking_keys,
    extract_detskiy_mir_format
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
    assert extract_store_code("Атак 548") == "548"
    assert extract_store_code("АТАК ООО 465") == "465"
    assert extract_store_code("Верный 2177") == "2177"
    assert extract_store_code("Пятёрочка 7242") == "7242"
    assert extract_store_code("Дискаунтер_31Y6") == "31Y6"
    assert extract_store_code("Дискаунтер_HA3A") == "HA3A"
    assert extract_store_code("5268") == "5268"
    assert extract_store_code("1", "АШАН ООО (take-off) с 01.04.2018") == "001"
    assert extract_store_code("(001) MYTISHI", "АШАН ООО (take-off) с 01.04.2018") == "001"
    assert extract_store_code("36", "АШАН ООО (take-off) с 01.04.2018") == "036"
    assert extract_store_code("Ашан (036) KUNCEVO", "АШАН ООО (take-off) с 01.04.2018") == "036"
    assert extract_store_code("Лента 1", "Лента ООО (take-off) с 01.04.2018") == "001"
    assert extract_store_code("Лента 36", "Лента ООО (take-off) с 01.04.2018") == "036"
    assert extract_store_code("Лента 4521", "Лента ООО (take-off) с 01.04.2018") == "4521"
    assert extract_store_code("ДИКСИ-77007", "Дикси Юг АО (take-off) с 01.04.2018") == "77007"
    assert extract_store_code("Дикси ДИКСИ-78510", "Дикси Юг АО (take-off) с 01.04.2018") == "78510"
    assert extract_store_code("77531 Дикси", "Дикси Юг АО (take-off) с 01.04.2018") == "77531"
    assert extract_store_code("МЕТРО 52", "МЕТРО КЭШ ЭНД КЕРРИ ООО (take-off) с 01.04.2018") == "52"
    assert extract_store_code("88", "МЕТРО КЭШ ЭНД КЕРРИ ООО (take-off) с 01.04.2018") == "88"

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


def test_extract_address_details_city_prefix_not_treated_as_street():
    base_h1, full_h1, city1, streets1 = extract_address_details("Набережные Челны,Сююмбике пр-кт,2/19")
    assert city1 == "набережные челны"
    assert "сююмбике" in streets1
    assert "ережные" not in streets1
    assert base_h1 == "2"
    assert full_h1 == "2/19"

    base_h2, full_h2, city2, streets2 = extract_address_details("Набережные Челны,наб.Габдуллы Тукая,2")
    assert city2 == "набережные челны"
    assert "тукая" in streets2 or "габдуллы" in streets2
    assert "ережные" not in streets2
    assert base_h2 == "2"
    assert full_h2 == "2"


def test_date_street_house_extraction_and_region_detection():
    # "8 марта" without explicit house must not extract 8 as house
    base_h, full_h = extract_house_components("8 марта")
    assert base_h == "б/н"
    assert full_h == "б/н"

    # Address with region name must not extract region as street
    base_h_reg, _, city_reg, streets_reg = extract_address_details("Россия, Тюменская обл, Заводоуковск г")
    assert "тюменская" not in streets_reg
    assert city_reg == "заводоуковск"


def test_extract_detskiy_mir_format():
    assert extract_detskiy_mir_format("ДМ Видное Ларец") == "ДМ"
    assert extract_detskiy_mir_format("ДМ МИНИ Медногорск на Гайдара") == "ДМ МИНИ"
    assert extract_detskiy_mir_format("ЗОО ТАМБОВ КАРЛА МАРКСА 2947") == "ЗОО"
    assert extract_detskiy_mir_format("РЦ \"Крёкшино-ИМ\"") == "РЦ"
    assert extract_detskiy_mir_format("дм мини самара") == "ДМ МИНИ"
    assert extract_detskiy_mir_format("зоо москва") == "ЗОО"
    assert extract_detskiy_mir_format("рц бекасово") == "РЦ"
    assert extract_detskiy_mir_format("Магазин Продукты") == ""



