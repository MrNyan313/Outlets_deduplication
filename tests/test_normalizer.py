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


def test_mn_abbr_not_house_litera_and_district_and_rural_settlement_city():
    # Hyphenated 'м-н' after house number must NOT be captured as litera 'м' (cases 5157, 5197, 5226)
    assert extract_house_components('Чувашская Республика, пгт Вурнары, пер Зеленый, д. 13 м-н "Мила 2"') == ("13", "13")
    assert extract_house_components('Республика Марий Эл, г Козьмодемьянск, ул Комсомольская, д. 29 м-н Континент') == ("29", "29")
    assert extract_house_components('425550, Республика Марий Эл, пгт Куженер, ул Совхозная д.10 м-н "ЛИДЕР"') == ("10", "10")
    # Real literas (including hyphenated '3-а' and '13а-2') must remain intact
    assert extract_house_components('ул. Ленина, д. 3-а') == ("3", "3а")
    assert extract_house_components('ул. Ленина, д. 13а-2') == ("13", "13а/2")

    # District 'р-н Волжский' / 'Волжский р-н' must NOT be hijacked by MAJOR_CITIES 'волжский' (case 5131)
    assert extract_address_details(
        '425030, Марий Эл Респ, р-н Волжский, пгт Приволжский, ул Рыночная площадь, д. 7'
    ) == ("7", "7", "приволжский", ["рыночная"])
    _, _, city_paraty, _ = extract_address_details(
        '425016, Марий Эл Респ, Волжский р-н, Новые Параты с, Центральная ул, д. 5'
    )
    assert city_paraty == "параты"
    # Real city Volzhsky must still be detected
    assert extract_address_details('Волгоградская обл, г. Волжский, ул. Ленина, 10') == ("10", "10", "волжский", ["ленина"])

    # Parenthetical rural settlement '(Верх-Ушнурское с/п)' / '(Бриляковский с/с)' must not override settlement name (case 5259)
    assert extract_address_details(
        '424039, 425418, Марий Эл Респ, Советский р-н, Верх-Ушнур (Верх-Ушнурское с/п) с, Центральная ул, дом № 1, корпус А, бокс м-н "Надежда"'
    ) == ("1", "1ка", "верх-ушнур", ["центральная"])
    assert extract_address_details(
        '606534, Нижегородская обл, Городецкий р-н, Бриляково (Бриляковский с/с) с, Мира ул, д. 5'
    ) == ("5", "5", "бриляково", ["мира"])


def test_numbered_stopword_city_and_initialed_streets_extracted_correctly():
    # 1. Numbered / lettered lines, quarters, microdistricts, lanes (cases 1071, 1181, 1238, 1091, 2273, 2863, 3947)
    assert extract_address_details('461047, Оренбургская обл, Бузулук г, 1 Линия ул, дом № 3') == ("3", "3", "бузулук", ["1_линия"])
    assert extract_address_details('Россия, Оренбургская обл, Бузулук г, 1-я Линия ул, Дом 3') == ("3", "3", "бузулук", ["1_линия"])
    assert extract_address_details('457134, Челябинская обл, Троицкий р-н, Бобровка с, 4 Квартал ул, дом № 6, кв.29') == ("6", "6", "бобровка", ["4_квартал"])
    assert extract_address_details('457105, Челябинская обл, Троицк г, 10-й кв-л, дом № 29, кв.93') == ("29", "29", "троицк", ["10_квартал"])
    assert extract_address_details('452613, Башкортостан Респ, Октябрьский г, 35-й мкр, дом № 33') == ("33", "33", "октябрьский", ["35_мкр"])
    assert extract_address_details('г. Байканур; микрорайон 5;д. 19А') == ("19", "19а", "байканур", ["5_мкр"])
    assert extract_address_details('199004, Санкт-Петербург г, 2-я В.О. линия, дом № 39/16') == ("39", "39/16", "санкт-петербург", ["2_линия"])
    assert extract_address_details('385019, Республика Адыгея (Адыгея), г Майкоп, пер 5-й, д. 2') == ("2", "2", "майкоп", ["5_пер"])
    assert extract_address_details('385730, Адыгея Респ, г. Майкоп, ул. 5-ый переулок, д. 2') == ("2", "2", "майкоп", ["5_пер"])
    assert extract_address_details('142200, Московская область обл, Серпухов г, Арнеево д, Квартал А тер., дом № 185') == ("185", "185", "серпухов", ["а_квартал"])
    assert extract_address_details('142290, Московская область обл, Пущино г, В мкр, дом № 6') == ("6", "6", "пущино", ["в_мкр"])
    assert extract_address_details('142290, Московская область обл, Пущино г, Г мкр, дом № 21б') == ("21", "21б", "пущино", ["г_мкр"])
    # Preposition 'в мкр. Северное Чертаново' must NOT become 'в_мкр'
    assert extract_address_details('г. Москва, в мкр. Северное Чертаново, д. 5') == ("5", "5", "москва", ["северное", "чертаново"])

    # 2. Stopword-named & village-named explicit streets (cases 1363, 1294, 2989, 3244, 3604)
    assert extract_address_details('462802, Оренбургская обл, Новоорский р-н, Кумак с, Набережная ул, дом № 38') == ("38", "38", "кумак", ["набережная"])
    assert extract_address_details('165514, Архангельская область, п Приозерный, ул Набережная, д. 6') == ("6", "6", "приозерный", ["набережная"])
    assert extract_address_details('457103, Челябинская обл, Троицк г, Российская ул, дом № 8') == ("8", "8", "троицк", ["российская"])
    assert extract_address_details('613050, Кировская обл, Кирово-Чепецк г., Россия пр-кт, дом № 32') == ("32", "32", "кирово-чепецк", ["россия"])
    assert extract_address_details('607404, Нижегородская область обл, Перевоз г, Шпилево с, Микрорайон ул, дом № 13б') == ("13", "13б", "перевоз", ["микрорайон"])
    assert extract_address_details('425468, Республика Марий Эл Респ, Сернурский р-н, Ананур д, Ананур ул, дом № 86') == ("86", "86", "ананур", ["ананур"])

    # 3. Initialed street names before and after surname (cases 1153, 1629, 4438, 4763, 5697, 5798, 16992)
    assert extract_address_details('453662, Башкортостан Респ, Баймакский р-н, Нижнеидрисово д, С.Юлаева ул, дом № 14') == ("14", "14", "нижнеидрисово", ["юлаева"])
    assert extract_address_details('457109, Челябинская обл, Троицк г, им Т.Д.Дерибаса ул, дом № 18А') == ("18", "18а", "троицк", ["дерибаса"])
    assert extract_address_details('Краснодарский край, Курганинский р-н, Курганинск г, Ст.Разина ул, дом 5') == ("5", "5", "курганинск", ["разина"])
    assert extract_address_details('352800, Краснодарский край, Туапсинский р-н, Туапсе г, Г.Петровой ул, дом 1') == ("1", "1", "туапсе", ["петровой"])
    assert extract_address_details('Северная Осетия - Алания Респ, Алагирский р-н, Алагир г, С.Кодоева ул, дом № 43') == ("43", "43", "алагир", ["кодоева"])
    assert extract_address_details('361820, Кабардино-Балкарская Респ, Черекский р-н, Аушигер с, Бадракова С.Х. ул, дом № 167') == ("167", "167", "аушигер", ["бадракова"])
    assert extract_address_details('368000, Дагестан Респ, Хасавюрт г, Шевелева С. С.ул, здание 37, строение 37') == ("37", "37к37", "хасавюрт", ["шевелева"])
    # 'кв. Норинского, д.2, кв.94' must extract house '2', while trailing 'кв.П2'/'кв.пом. 013' must still be cut off
    assert extract_address_details('ЛНР, г. Луганск, кв. Норинского, д.2, кв.94') == ("2", "2", "луганск", ["норинского"])
    assert extract_house_components('Нижний Новгород г, Левобережная ул, дом № 4, кв.П2') == ("4", "4")
    assert extract_house_components('Красногорск г, Игоря Мерлушкина ул, дом № 1, кв.пом. 013') == ("1", "1")
    # Anniversary / numbered streets without comma or dot after 'ул' preserve city and canonical N_лет token
    assert extract_address_details('Обл р-н. Енакиевский г. Енакиево ул. 50 лет октября 33 РТТ маг. "Ника"') == ("33", "33", "енакиево", ["50_лет", "октября"])
    assert extract_address_details('г. Енакиево ул 30 лет победы 12') == ("12", "12", "енакиево", ["30_лет", "победы"])
    assert extract_address_details('г. Енакиево ул 30-летия Победы 12') == ("12", "12", "енакиево", ["30_лет", "победы"])
    assert extract_address_details('г. Енакиево ул 40 лет октября 15') == ("15", "15", "енакиево", ["40_лет", "октября"])
    assert extract_address_details('г. Енакиево ул 60-летия СССР 10') == ("10", "10", "енакиево", ["60_лет", "ссср"])
    assert extract_address_details('г. Енакиево ул 26 Бакинских комиссаров 7') == ("7", "7", "енакиево", ["бакинских", "комиссаров"])
    assert extract_house_components('г. Енакиево, ул. 30-летия Победы') == ("б/н", "б/н")
    # Raw underscores in addresses and glued leading digits before street name must still normalize cleanly
    assert extract_address_details('286157, ДНР, г. Макеевка, ул. Московская_35055')[3] == ["московская"]
    assert extract_address_details('Чеченская Респ, Курчалоевский р-н, Курчалой г, 1Южная ул, дом № 1') == ("1", "1", "курчалой", ["южная"])


def test_fallback_street_tail_cutoff_slash_gln_quoted_litera_and_initials_in_name():
    # 1. Fallback street extraction strips trailing house/shop noise while keeping leading 'м-н' microdistricts & markets
    assert extract_address_details('Обл. Донецкая г. Макеевка кв-л Металлург 16 РТТ маг."Бытовая химия"') == ("16", "16", "макеевка", ["металлург"])
    assert extract_address_details('ДНР, г. Макеевка, Горняцкий р-н, м-н Зеленый, д.2, маг. "Бытовая химия"') == ("2", "2", "макеевка", ["зеленый"])
    assert extract_address_details('ДНР, г. Кировское, м-н Горняцкий, д. 5') == ("5", "5", "кировское", ["горняцкий"])
    assert extract_address_details('Северная Осетия - Алания Респ, Владикавказ г, Первомайский рынок') == ("б/н", "б/н", "владикавказ", ["первомайский", "рынок"])

    # 2. Trailing 5+ digit accounting/GLN code after slash is NOT a house fraction (case 3754)
    assert extract_house_components('ЕвроРитейл, "Спар № 76", г. Калининград, ул. К. Маркса, д. 18  / 390645030') == ("18", "18")
    assert extract_house_components('ЕвроРитейл, "Спар № 71", г. Калининград, ул. А. Невского, д. 137 Б  /390645024') == ("137", "137б")
    assert extract_house_components('ЕвроРитейл, "Спар № 90", г. Гурьевск, Пражский бульвар, 1 Ж   /391745002') == ("1", "1ж")
    # Real 1-4 digit house fractions remain intact
    assert extract_house_components('г. Ростов-на-Дону, 40-я линия ул, дом № 57/31') == ("57", "57/31")

    # 3. Quoted single-letter house literas are unwrapped, while quoted shop names are untouched (case 3848, 4712)
    assert extract_house_components('Лавренчук Л.В., г Калининград, ул. Ю. Бульвар, 2"А"') == ("2", "2а")
    assert extract_house_components('Ростовская обл, Батайск г, Пятигорская ул, дом № 112 "Г"') == ("112", "112г")
    assert extract_house_components('РК, Усть-Куломский р-н, с.Усть-Кулом, ул.Советская, д. 33 "Б"') == ("33", "33б")
    assert extract_house_components('692502, Приморский край, г. Уссурийск, ул. Владивостокское шоссе, 93 «А» база') == ("93", "93а")
    assert extract_house_components('г. Москва, ул. Ленина, д. 12 "Магнит"') == ("12", "12")

    # 4. clean_store_name removes initials without chopping the first letter of following words
    assert clean_store_name('ЕвроРитейл, "Спар № 76", г. Калининград, ул. К. Маркса, д. 18  / 390645030') == "евроритейл спар 76 калининград ул маркса 18 390645030"
    assert clean_store_name('Лавренчук Л.В., г Калининград, ул. Ю. Бульвар, 2"А"') == "лавренчук г калининград ул бульвар 2 а"
    assert clean_store_name('Лавренчук И.П. г. Калининград, ул. Юж.Бульвар, д. 2а') == "лавренчук калининград ул юж бульвар 2а"
    assert clean_store_name('ИП Петров А.В') == "петров"
    assert clean_store_name('ИП Петров А. В.') == "петров"




