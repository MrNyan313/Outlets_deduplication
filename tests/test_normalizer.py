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


def test_km_extraction_and_stemming():
    from normalizer import extract_km, stem_street_token
    assert extract_km("Москва г, Пятницкое ш, 7-й км, 2") == "7"
    assert extract_km("Московская обл, Красногорск г, 7-й (автодорога Пятницкое шоссе тер.) км, 2") == "7"
    assert extract_km("Самарская область,гСамара,24 км Московского шоссе, 5") == "24"
    assert extract_km("Московское ш., 18 км") == "18"
    assert extract_km("км 12") == "12"
    assert extract_km("г. Самара, ул. Ленина, д. 5") == ""

    assert stem_street_token("пятницкое") == "пятницк"
    assert stem_street_token("пятницкого") == "пятницк"
    assert stem_street_token("таллинское") == "таллин"
    assert stem_street_token("таллинского") == "таллин"
    assert stem_street_token("московское") == "москов"
    assert stem_street_token("московского") == "москов"


def test_highway_house_and_name_cleaning():
    from normalizer import extract_house_components, clean_store_name, extract_address_details
    # 7-й км with trailing comma must not extract 7 as house number
    assert extract_house_components("Москва г, Пятницкое ш, 7-й км,")[0] == "б/н"
    assert extract_house_components("Москва г, Пятницкое ш, 7-й км, 2")[0] == "2"
    assert extract_house_components("Московская область.,г.Москва,7 км Пятницкого ш., вл. 2")[0] == "2"
    assert extract_house_components("Московская обл, Красногорск г, 7-й (автодорога Пятницкое шоссе тер.) км, 2")[0] == "2"

    # clean_store_name strips km
    assert clean_store_name("ГМ Москва Пятницкое 7 км") == "гм москва пятницкое"
    assert clean_store_name("ГМ Москва Пятницкое") == "гм москва пятницкое"

    # extract_address_details extracts clean street and doesn't get polluted by тер
    _, _, _, streets = extract_address_details("Московская обл, Красногорск г, 7-й (автодорога Пятницкое шоссе тер.) км, 2")
    assert "пятницкое" in streets
    assert "тер" not in streets


def test_house_extraction_word_boundary_and_hyphen_litera():
    assert extract_house_components("353900, Краснодарский край, Новороссийск г, Бирюзова ул, дом № 3 СКЛАД") == ("3", "3")
    assert extract_house_components("297408, Крым Респ, Евпатория г, Токарева ул, дом № 31 маг. Гастроном") == ("31", "31")
    assert extract_house_components("г. Симферополь, ул. Героев Сталинграда, д. 3-а") == ("3", "3а")
    assert extract_house_components("г. Макеевка ул. Кирова 9 рынок РТТ место№3 (Кондитерка)") == ("9", "9")
    assert extract_house_components("Севастопольская 70 Г, бутик №15") == ("70", "70г")


def test_store_code_extraction_blocks_false_words_and_preserves_alpha_networks():
    # Regular distributors must not extract non-digit words as store codes
    for name in ("Магас Забава (Кулиева 3)", "Магазин", "ИП Юзыкаев Динис Магазович", "МИЛА ООО (Чебоксары)", "Сельмаг", "Колосок"):
        assert extract_store_code(name, "Сладкая жизнь плюс ООО") == ""
    assert extract_store_code("Лента611", "Лента ООО (take-off) с 01.04.2018") == "611"
    # Alphabetical codes preserved for ALPHA_CODE_NETWORKS
    assert extract_store_code("ЯРС", "ОКЕЙ ООО (take off)") == "ЯPC"
    assert extract_store_code("Пятерочка MSK", "ПЯТЁРОЧКА") == "MSK"
    assert extract_store_code("Ашан (MSK)", "АШАН ООО (take-off) с 01.04.2018") == ""


def test_address_details_major_city_word_boundary_and_comma_less():
    _, _, city_msk, streets_msk = extract_address_details("109125, Москва г, Саратовская ул, дом № 24")
    assert city_msk == "москва"
    assert streets_msk == ["саратовская"]

    _, _, city_eysk, _ = extract_address_details("353691, Краснодарский край, Ейский р-н, Ейск г, Шоссейный пер, дом № 2, корпус 7")
    assert city_eysk == "ейск"

    _, _, city_sochi, _ = extract_address_details("354037, Краснодарский край, Сочи г, Шоссейная ул, дом 2б")
    assert city_sochi == "сочи"

    _, _, city_vol, streets_vol = extract_address_details("г. Москва г.Москва Вольская 1-z 17 1")
    assert city_vol == "москва"
    assert "вольская" in streets_vol

    _, _, _, streets_kan = extract_address_details("Канаш ул.Чернышеского 41 кафе Халяль")
    assert streets_kan == ["чернышеского"]


def test_clean_store_name_noise_tails_leading_ids_and_fio():
    from normalizer import extract_fio_surname_patronymic

    assert clean_store_name("ИП Прокофьева Ульяна Алексеевна НАЛ") == clean_store_name("ИП Прокофьева Ульяна Алексеевна 7 дн")
    assert clean_store_name("Индивидуальный предприниматель Дерягина Татьяна Николаевна") == clean_store_name("Дерягина Татьяна Николаевна ФЛП")
    assert clean_store_name("124395 САРБАШ АЛЕКСАНДР СТЕПАНОВИЧ 30ДН.К", strip_leading_id=True) == "сарбаш александр степанович"
    assert clean_store_name("1000 Мелочей", strip_leading_id=True) == "1000 мелочей"
    assert clean_store_name("Хейрхабаров Галиб Шахали оглы -Адрес доставки_225", strip_leading_id=True) == "хейрхабаров галиб шахали оглы"

    assert extract_fio_surname_patronymic("ИП КАМАЛОВ МАЗАХИР ТЕЛЬМАН ОГЛЫ") == ("камалов", "тельман оглы")
    assert extract_fio_surname_patronymic("ИП Камалов Дилгам Тельман оглы") == ("камалов", "тельман оглы")
    assert extract_fio_surname_patronymic("ИП Бубнов Николай Николаевич") == ("бубнов", "николаевич")
    assert extract_fio_surname_patronymic("ИП Бубнова Галина Николаевна") == ("бубнов", "николаевич")
    assert extract_fio_surname_patronymic("ИП Прокофьева Ульяна Алексеевна") != extract_fio_surname_patronymic("ИП Прокофьев Алексей Валерьевич")


def test_house_letter_stroenie_slash_and_gorokrug_and_region_streets():
    # Letter stroenie/korpus and standalone slash fraction
    assert extract_house_components("350073, Краснодарский край, Краснодар г, им лётчика Позднякова ул, дом 2 стр Б") == ("2", "2кб")
    assert extract_house_components("Михайловск Ул. Войкова 399/1 м-н Белорусской косметики") == ("399", "399/1")

    # 'г.о.' must not extract 'о' as city, and must not corrupt city names starting with 'Го...'
    _, _, city_mar, _ = extract_address_details("ДНР, г.о. Мариуполь, г. Мариуполь, ул. Воинов-Освободителей, д. 94")
    assert city_mar == "мариуполь"
    assert extract_address_details("г. Горно-Алтайск, ул. Ленина, 5") == ("5", "5", "горно-алтайск", ["ленина"])
    assert extract_address_details("Нижегородская обл, г. Городец, ул. Новая, 1") == ("1", "1", "городец", ["новая"])

    # Region-named streets must be preserved in explicit street patterns, while region-only addresses have no street
    assert extract_address_details("московская улица, д. 1") == ("1", "1", "", ["московская"])
    assert extract_address_details("г. Казань, ул. Московская, д. 1") == ("1", "1", "казань", ["московская"])
    assert extract_address_details("Московская обл, г. Подольск, ул. Московская, д. 1") == ("1", "1", "подольск", ["московская"])
    assert extract_address_details("г. Москва, ул. Донецкая, д. 10") == ("10", "10", "москва", ["донецкая"])
    assert extract_address_details("Россия, Чувашская Республика - Чувашия") == ("б/н", "б/н", "", [])
    assert extract_address_details("Ханты-Мансийский автономный округ - Югра") == ("б/н", "б/н", "", [])
    assert extract_address_details("Республика Саха (Якутия)") == ("б/н", "б/н", "", [])
    assert extract_address_details("Ямало-Ненецкий автономный округ, муниципальный округ, с. Аксарка") == ("б/н", "б/н", "аксарка", [])

    # Extended trade/payment noise cleaning
    assert clean_store_name("ЭСЕНАЛИЕВ МУРАДИН ЭДО УПД") == "эсеналиев мурадин"
    assert clean_store_name("ТЕР-МАРТИРОСОВА ЭЛЬМИРА за наличку") == "тер мартиросова эльмира"
    assert clean_store_name("ЛАЛАЯН АРТУР РОЗНИЦА") == "лалаян артур"
    assert clean_store_name("ДУЩЕНКО ЕЛЕНА эл.накл. Садовая Т-12") == "дущенко елена садовая"
    assert clean_store_name("Васильева Елена РОЗНИЦА Шпаковка ЭЛ.НАКЛ.") == "васильева елена шпаковка"




