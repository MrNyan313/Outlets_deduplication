"""Address and store name normalization module."""

import re
from typing import Tuple, List, Set

# Organizational legal forms to remove from store names
LEGAL_FORMS = {
    'ооо', 'ип', 'зао', 'оао', 'ао', 'пао', 'тд', 'тк', 'маг', 'магазин',
    'см', 'с/м', 'супермаркет', 'гипермаркет', 'универсам', 'гастроном',
    'бузоо', 'црб', 'чп', 'лтд', 'ltd'
}

# Stop words in address parsing
ADDRESS_STOP_WORDS = {
    'россия', 'рф', 'федерация',
    'обл', 'область', 'край', 'респ', 'республика', 'ао', 'рн', 'район',
    'г', 'город', 'пгт', 'рп', 'п', 'поселок', 'пос', 'д', 'деревня',
    'с', 'село', 'ст', 'станица', 'х', 'хутор', 'с/с', 'с/совет',
    'ул', 'улица', 'пркт', 'проспект', 'пр', 'проезд', 'пер', 'переулок',
    'бул', 'бульвар', 'ш', 'шоссе', 'наб', 'набережная', 'пл', 'площадь',
    'тракт', 'линия', 'аллея', 'тупик', 'кв-л', 'квартал', 'мкр', 'микрорайон',
    'дом', 'кв', 'пом', 'стр', 'корп', 'здание', 'зд', 'корпус', 'строение',
    'литера', 'лит', 'помещение', 'комн', 'оф', 'офис', 'эт', 'этаж'
}

MAJOR_CITIES = {
    'москва', 'санкт-петербург', 'петербург', 'севастополь'
}

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
         '33\\19' -> ('33', '33/19')
    """
    t = normalize_text(addr)
    if not t:
        return "", ""

    # Remove 6-digit postal code
    t = re.sub(r'\b\d{6}\b', '', t)

    # Cut off interior unit info (apartment, office, room)
    t = re.split(r'\b(?:кв|квартира|пом|помещение|комн|оф|офис|эт|этаж)\b', t)[0].strip()

    # 1. House with korpus/building: e.g. "15 стр 3", "д. 15 корп 2", "зд. 7 к. 4"
    m1 = re.search(
        r'(?:(?:дом|д|зд|здание)\.?\s*(?:№\s*)?)?(\d+)\s*([а-яa-z])?(?:\s*[/\\-]\s*(\d+[а-яa-z]?))?\s*(?:к|корп|корпус|стр|строение|п|лит|литера)\.?\s*(\d+[а-яa-z]?)',
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

    # 2. Explicit marker: дом, д., зд., здание
    m2 = re.search(r'\b(?:дом|д|зд|здание)\.?\s*(?:№\s*)?(\d+)\s*([а-яa-z])?(?:\s*[/\\-]\s*(\d+[а-яa-z]?))?', t)
    if m2:
        base_num = m2.group(1)
        lit = m2.group(2) or ''
        slash = m2.group(3) or ''
        full = base_num + lit
        if slash:
            full += '/' + slash
        return base_num, full

    # 3. корпус / строение directly followed by number
    m3 = re.search(r'\b(?:корпус\s*строение|строение|корпус|корп|стр)\.?\s*(?:№\s*)?(\d+)\s*([а-яa-z])?', t)
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

    # 5. Fallback: find any standalone number that might be a house
    nums = re.findall(r'\b(\d+([а-яa-z])?)\b', t)
    if nums:
        val = nums[-1][0]
        base = re.match(r'\d+', val).group(0)
        return base, val

    return "", ""


def extract_store_code(name: str) -> str:
    """
    Extracts store code / number from a store name.
    e.g. 'Дискаунтер_H085' -> 'H085'
         'Малинка №604' -> '604'
         'Спар № 118' -> '118'
         'X5 E231' -> 'E231'
    """
    if not name:
        return ""
    t = str(name).strip()

    # 1. Look for number marker: № 604, №604, N 604, #604
    m_no = re.search(r'[№N#]\s*([0-9]+[а-яa-z]?)', t, re.IGNORECASE)
    if m_no:
        return m_no.group(1).lower()

    # 2. Look for alphanumeric store codes: H085, E231, H928, etc.
    m_code = re.search(r'(?:^|[^a-zA-Zа-яА-Я0-9])([a-zA-Zа-яА-Я]\d{3,4})(?:$|[^a-zA-Zа-яА-Я0-9])', t)
    if m_code:
        code = m_code.group(1).upper()
        return code.translate(CYR_TO_LAT)

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
    base_house, full_house = extract_house_components(t)

    # Clean address from postal code and house
    addr_clean = re.sub(r'\b\d{6}\b', '', t)
    parts = [p.strip() for p in addr_clean.split(',') if p.strip()]

    city = ""
    street_words = []

    # Detect city from parts
    for part in parts:
        words = re.findall(r'[а-яa-z0-9]+', part)
        part_set = set(words)

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

    # Extract street tokens (words that are not stop words)
    all_words = re.findall(r'[а-яa-z0-9]+', addr_clean)
    for w in all_words:
        if len(w) >= 3 and w not in ADDRESS_STOP_WORDS:
            # exclude city words from street tokens if city is known
            if not city or w not in city.split():
                street_words.append(w)

    return base_house, full_house, city, street_words


def get_address_blocking_keys(raw_addr: str) -> List[Tuple[str, str]]:
    """
    Generates multi-pass blocking keys for candidate retrieval.
    Each key is a tuple: (token, base_house)
    where token can be a distinctive street token or (city + street token).
    """
    base_house, full_house, city, street_tokens = extract_address_details(raw_addr)
    if not base_house:
        return []

    keys = []
    # If city is known, combine (city, street_token, base_house)
    if city:
        city_token = city.split()[0]
        for st in street_tokens[:3]:
            keys.append((f"{city_token}_{st}", base_house))

    # Secondary keys: (street_token, base_house)
    for st in street_tokens[:3]:
        keys.append((st, base_house))

    return keys
