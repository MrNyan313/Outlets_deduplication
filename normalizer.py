"""Address and store name normalization module."""

import re
from typing import Tuple, List, Set, Optional

# Organizational legal forms and generic chain words to remove from store names
LEGAL_FORMS = {
    'ооо', 'ип', 'зао', 'оао', 'ао', 'пао', 'тд', 'тк', 'маг', 'магазин',
    'см', 'с/м', 'супермаркет', 'гипермаркет', 'дискаунтер', 'универсам',
    'гастроном', 'бузоо', 'црб', 'чп', 'лтд', 'ltd', 'ссив', 'тт'
}

# Regional adjectives and words that must NOT be treated as street names
REGION_WORDS = {
    'московская', 'ленинградская', 'нижегородская', 'самарская', 'владимирская',
    'свердловская', 'ростовская', 'челябинская', 'воронежская', 'волгоградская',
    'краснодарский', 'ставропольский', 'пермский', 'алтайский', 'приморский',
    'башкортостан', 'татарстан', 'дагестан', 'удмуртская', 'чувашская',
    'область', 'обл', 'край', 'респ', 'республика', 'ао', 'район', 'рн',
    'р-н', 'россия', 'рф', 'федерация'
}

# Stop words in address parsing
ADDRESS_STOP_WORDS = REGION_WORDS | {
    'г', 'город', 'пгт', 'рп', 'п', 'поселок', 'пос', 'д', 'деревня',
    'с', 'село', 'ст', 'станица', 'х', 'хутор', 'с/с', 'с/совет',
    'ул', 'улица', 'пркт', 'проспект', 'пр', 'проезд', 'пер', 'переулок',
    'бул', 'бульвар', 'ш', 'шоссе', 'наб', 'набережная', 'пл', 'площадь',
    'тракт', 'линия', 'аллея', 'тупик', 'кв-л', 'квартал', 'мкр', 'микрорайон',
    'дом', 'кв', 'пом', 'стр', 'корп', 'здание', 'зд', 'корпус', 'строение',
    'литера', 'лит', 'помещение', 'комн', 'оф', 'офис', 'эт', 'этаж',
    'ссив', 'дискаунтер', 'гипермаркет', 'супермаркет'
}

MAJOR_CITIES = {
    'москва', 'санкт-петербург', 'петербург', 'севастополь'
}

STREET_PATTERNS = [
    r'\b(?:ул|улица|пр-кт|проспект|проезд|пер|переулок|бул|бульвар|шоссе|ш|наб|набережная|аллея|тракт|тупик)\.?\s+([а-яa-z0-9\-]+(?:\s+[а-яa-z0-9\-]+){0,2})',
    r'([а-яa-z0-9\-]+(?:\s+[а-яa-z0-9\-]+){0,2})\s+\b(?:ул|улица|пр-кт|проспект|проезд|пер|переулок|бул|бульвар|шоссе|ш|наб|набережная|аллея|тракт|тупик)\b'
]

# Mapping Cyrillic lookalikes to Latin for store codes
CYR_TO_LAT = str.maketrans('АВЕКМНОРСТУХ', 'ABEKMHOPCTYX')


def normalize_text(text: str) -> str:
    """Basic text normalization: lowercase, 'ё'->'е', uniform whitespace."""
    if not text:
        return ""
    t = str(text).lower().replace("ё", "е")
    t = re.sub(r'[\s\u00a0\u202f]+', ' ', t)
    return t.strip()


def extract_house_components(addr: str) -> Tuple[str, str]:
    """
    Extracts house number components from an address string.
    Returns: (base_house, full_house)
    e.g. 'дом № 5а' -> ('5', '5а')
         'зд.7 к.4' -> ('7', '7к4')
         '15 стр 3' -> ('15', '15к3')
         '15, к 3' -> ('15', '15к3')
         '33\\19' -> ('33', '33/19')
         'б\\н' or no house -> ('б/н', 'б/н')
    """
    t = normalize_text(addr)
    if not t:
        return "б/н", "б/н"

    # Explicit marker: б/н, б\н, б.н., без номера, n/a, n\a
    if re.search(r'\b(?:б\s*[/\\.]\s*н|без\s+номера|n\s*[/\\.]\s*a)\b', t):
        return "б/н", "б/н"

    # Remove 6-digit postal code
    t = re.sub(r'\b\d{6}\b', '', t)

    # Strip trailing annotations in parentheses like "(А)", "(К)", "(пом. 3)"
    t = re.sub(r'[\s,]*\([а-яa-z0-9\s\.\-]+\)\s*$', '', t).strip()

    # Cut off interior unit info (apartment, office, room)
    t = re.split(r'\b(?:кв|квартира|пом|помещение|комн|оф|офис|эт|этаж)\b', t)[0].strip()

    # 1. House with korpus/building/stroenie: e.g. "15, к 3", "д.15,к.3", "15 стр 3", "д. 15 корп 2", "зд. 7 к. 4"
    m1 = re.search(
        r'(?:(?:дом|д|зд|здание)\.?\s*(?:№\s*)?)?'
        r'(\d+)\s*([а-яa-z])?(?:\s*[/\\-]\s*(\d+[а-яa-z]?))?'
        r'(?:[,\s/\\-]+|(?<=\d))'
        r'(?:к|корп|корпус|стр|строение|п|лит|литера)\.?\s*(\d+[а-яa-z]?)',
        t
    )
    if m1:
        base_num = m1.group(1)
        lit = m1.group(2) or ''
        slash = m1.group(3) or ''
        korp = m1.group(4) or ''
        full = base_num + lit
        if slash:
            full += '/' + slash
        if korp:
            full += 'к' + korp
        return base_num, full

    # 2. Explicit marker: дом, д., зд., здание, вл, влд, владение, уч, участок
    m2 = re.search(
        r'\b(?:дом|д|зд|здание|вл|влд|владение|уч|участок)\.?\s*(?:№\s*)?'
        r'(\d+)\s*([а-яa-z])?(?:\s*[/\\-]\s*(\d+[а-яa-z]?))?',
        t
    )
    if m2:
        base_num = m2.group(1)
        lit = m2.group(2) or ''
        slash = m2.group(3) or ''
        full = base_num + lit
        if slash:
            full += '/' + slash
        return base_num, full

    # 3. корпус / строение directly followed by number (standalone, e.g. "стр 15", "к514")
    m3 = re.search(r'\b(?:корпус\s*строение|строение|корпус|корп|стр|к)\.?\s*(?:№\s*)?(\d+)\s*([а-яa-z])?', t)
    if m3:
        base_num = m3.group(1)
        lit = m3.group(2) or ''
        return base_num, base_num + lit

    # 4. Number at end of address string or after comma: e.g. "Татищева бульвар, 6а" or "ул 21"
    m4 = re.search(r'[, ]+(\d+)\s*([а-яa-z])?(?:\s*[/\\-]\s*(\d+[а-яa-z]?))?\s*$', t)
    if m4:
        base_num = m4.group(1)
        lit = m4.group(2) or ''
        slash = m4.group(3) or ''
        full = base_num + lit
        if slash:
            full += '/' + slash
        return base_num, full

    # 5. Standalone number that is not postal code
    nums = re.findall(r'\b(\d+([а-яa-z])?)\b', t)
    if nums:
        val = nums[-1][0]
        base = re.match(r'\d+', val).group(0)
        return base, val

    # If no number at all is specified in address: "б/н"
    return "б/н", "б/н"


def extract_store_code(name: str) -> str:
    """
    Extracts store code / number from a store name.
    e.g. 'Дискаунтер_363H' -> '363H'
         'Дискаунтер_5181' -> '5181'
         '5268' -> '5268'
         '5282' -> '5282'
         'Дискаунтер_304S' -> '304S'
         'Пятерочка 304S' -> '304S'
         'X5 H085' -> 'H085'
         'Малинка №604' -> '604'
         'Спар № 118' -> '118'
         'X5 2680' -> '2680'
    """
    if not name:
        return ""
    t = str(name).strip()

    # 1. Number marker: № 604, №604, N 604, #604
    m_no = re.search(r'[№N#]\s*([0-9]+[а-яa-z]?)', t, re.IGNORECASE)
    if m_no:
        return m_no.group(1).lower()

    # 2. Alphanumeric store codes: e.g. H085, E231 (letter + digits) or 304S (digits + letter)
    m_code = re.search(r'(?:^|[^a-zA-Zа-яА-Я0-9])([a-zA-Zа-яА-Я]\d{2,5}|\d{2,5}[a-zA-Zа-яА-Я])(?:$|[^a-zA-Zа-яА-Я0-9])', t)
    if m_code:
        code = m_code.group(1).upper()
        return code.translate(CYR_TO_LAT)

    # 3. X5 store number: "X5 2680" or "Х5 2680"
    m_x5 = re.search(r'\b(?:x5|х5)\s*(\d{2,5})\b', t, re.IGNORECASE)
    if m_x5:
        return m_x5.group(1)

    # 4. Chain prefix followed by number: e.g. "Дискаунтер_5181", "Дискаунтер_5268"
    m_chain_num = re.search(r'\b(?:дискаунтер|гипермаркет|супермаркет|магазин|маг|тт)[_ ]+(\d{2,6})\b', t, re.IGNORECASE)
    if m_chain_num:
        return m_chain_num.group(1)

    # 5. Pure numeric store name / code: e.g. "5268", "5282", "2111"
    if re.match(r'^\d{2,6}$', t.strip()):
        return t.strip()

    return ""


def clean_store_name(name: str) -> str:
    """
    Cleans a store name by removing legal forms (ООО, ИП), punctuation, and initials.
    """
    if not name:
        return ""
    t = str(name).lower().replace("ё", "е")
    # Remove quotes, brackets, store symbols
    t = re.sub(r'["\'\(\)\[\]«»„“”№#_]', ' ', t)
    # Remove person initials like "в.в.", "е.а."
    t = re.sub(r'\b[а-яa-z]\s*\.\s*[а-яa-z]?\s*\.?', ' ', t)
    words = re.findall(r'[а-яa-z0-9]+', t)
    cleaned = [w for w in words if w not in LEGAL_FORMS]
    return ' '.join(cleaned)


def extract_address_details(raw_addr: str) -> Tuple[str, str, str, List[str]]:
    """
    Extracts normalized address details:
    Returns: (base_house, full_house, city, street_tokens)
    """
    t = normalize_text(raw_addr)
    # Strip trailing annotations in parentheses
    t = re.sub(r'[\s,]*\([а-яa-z0-9\s\.\-]+\)\s*$', '', t).strip()
    base_house, full_house = extract_house_components(t)

    # Clean address from postal code and house
    addr_clean = re.sub(r'\b\d{6}\b', '', t)
    parts = [p.strip() for p in addr_clean.split(',') if p.strip()]

    city = ""

    # Detect city
    for part in parts:
        words = re.findall(r'[а-яa-z0-9]+', part)

        # Check major city
        for mc in MAJOR_CITIES:
            if mc in part:
                city = mc
                break
        if city:
            break

        # Check city indicators
        if any(w in {'г', 'город', 'пгт', 'рп', 'п', 'поселок'} for w in words):
            c_words = [w for w in words if w not in ADDRESS_STOP_WORDS and not w.isdigit()]
            if c_words:
                city = ' '.join(c_words)
                break

    # Extract clean street tokens using explicit street patterns
    street_words = []
    for pat in STREET_PATTERNS:
        m = re.search(pat, addr_clean)
        if m:
            cand = m.group(1).strip()
            cand = re.sub(r'^\d+\s*|\s*\d+$', '', cand).strip()
            words = [w for w in re.findall(r'[а-яa-z0-9]+', cand) if len(w) >= 3 and w not in ADDRESS_STOP_WORDS]
            if words:
                street_words = words
                break

    # Fallback if street pattern didn't match: take words that are not region/city/stop words
    if not street_words:
        all_words = re.findall(r'[а-яa-z0-9]+', addr_clean)
        for w in all_words:
            if len(w) >= 3 and w not in ADDRESS_STOP_WORDS:
                if not city or w not in city.split():
                    street_words.append(w)

    return base_house, full_house, city, street_words


def get_address_blocking_keys(
    raw_addr: str = "",
    store_name: str = "",
    base_house: Optional[str] = None,
    city: Optional[str] = None,
    street_tokens: Optional[List[str]] = None,
    store_code: Optional[str] = None,
) -> List[Tuple[str, str]]:
    """
    Generates multi-pass blocking keys for candidate retrieval.
    All keys are geographically anchored to prevent cross-region false matches.
    Can use pre-extracted features or extract them on the fly from raw_addr.
    """
    if base_house is None or city is None or street_tokens is None:
        b_h, _, c, s_tokens = extract_address_details(raw_addr)
        base_house = base_house if base_house is not None else b_h
        city = city if city is not None else c
        street_tokens = street_tokens if street_tokens is not None else s_tokens

    if not base_house:
        base_house = "б/н"

    keys = []
    city_token = city.split()[0] if city else ""

    if not store_code and store_name:
        store_code = extract_store_code(store_name)

    # Geographically anchored code keys (city + code or street + code)
    if store_code:
        if city_token:
            keys.append((f"{city_token}_code_{store_code}", "code"))
        for st in street_tokens[:2]:
            keys.append((f"{st}_code_{store_code}", "code"))

    # Street and city keys with house number
    if city_token:
        for st in street_tokens[:3]:
            keys.append((f"{city_token}_{st}", base_house))

    for st in street_tokens[:3]:
        keys.append((st, base_house))

    return keys
