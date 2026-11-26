"""Address and store name normalization module."""

import re
from typing import Tuple, List, Set, Optional

from config import PAD_3DIGIT_CODE_NETWORKS, ALPHA_CODE_NETWORKS

# Organizational legal forms and generic chain/payment noise words to remove from store names
LEGAL_FORMS = {
    'ооо', 'ип', 'зао', 'оао', 'ао', 'пао', 'тд', 'тк', 'маг', 'магазин',
    'см', 'с/м', 'супермаркет', 'гипермаркет', 'дискаунтер', 'универсам',
    'гастроном', 'бузоо', 'црб', 'чп', 'лтд', 'ltd', 'ссив', 'тт',
    'флп', 'фл', 'спд', 'ртт', 'нал', 'безнал', 'упд', 'эдо', 'зк',
    'закрытые', 'закрыт', 'закрыта', 'долг', 'предоплата',
}

# Regional adjectives, republic names, and regional abbreviations of Russia
# Excluded in fallback street parsing, while preserved inside explicit street patterns (e.g. 'ул. Московская')
REGION_ADJECTIVES = {
    # Областные и краевые прилагательные
    'амурская', 'архангельская', 'астрахангельская', 'астраханская',
    'белгородская', 'брянская', 'владимирская', 'волгоградская', 'вологодская',
    'воронежская', 'еврейская', 'запорожская', 'ивановская', 'иркутская',
    'калининградская', 'калужская', 'кемеровская', 'кировская', 'костромская',
    'курганская', 'курская', 'ленинградская', 'липецкая', 'магаданская',
    'московская', 'мурманская', 'нижегородская', 'новгородская', 'новосибирская',
    'омская', 'оренбургская', 'орловская', 'пензенская', 'петербургская',
    'псковская', 'ростовская', 'рязанская', 'самарская', 'саратовская',
    'сахалинская', 'свердловская', 'смоленская', 'тамбовская', 'тверская',
    'томская', 'тульская', 'тюменская', 'ульяновская', 'херсонская',
    'челябинская', 'ярославская',
    'алтайский', 'забайкальский', 'камчатский', 'краснодарский', 'красноярский',
    'пермский', 'приморский', 'ставропольский', 'хабаровский',
    'ненецкий', 'ханты', 'мансийский', 'чукотский', 'ямало',
    # Республики, ДНР/ЛНР, автономные округа и их устоявшиеся формы/аббревиатуры
    'адыгея', 'адыгейская', 'алтай', 'башкортостан', 'башкирия', 'башкирская',
    'бурятия', 'бурятская', 'дагестан', 'дагестанская', 'донецкая', 'днр',
    'ингушетия', 'ингушская', 'кабардино', 'балкарская', 'балкария', 'кбр',
    'калмыкия', 'калмыцкая', 'карачаево', 'черкесская', 'черкесия', 'кчр',
    'карелия', 'карельская', 'коми', 'крым', 'крымская', 'кузбасс',
    'луганская', 'лнр', 'марий', 'марийская', 'эл', 'рмэ',
    'мордовия', 'мордовская', 'саха', 'якутия', 'якутская',
    'северная', 'осетия', 'осетинская', 'алания', 'рсо',
    'татарстан', 'татарская', 'тува', 'тувинская', 'тыва',
    'удмуртия', 'удмуртская', 'хакасия', 'хакасская',
    'чечня', 'чеченская', 'чувашия', 'чувашская', 'чуваш',
    'югра', 'чукотка',
    'рб', 'рд', 'ри', 'рт', 'ур', 'чр', 'еао', 'нао', 'хмао', 'чао', 'янао',
}
REGION_ADMIN_UNITS = {
    'область', 'области', 'обл', 'край', 'края',
    'респ', 'республика', 'республики',
    'ао', 'мо', 'ло', 'го', 'мр', 'рф',
    'автономная', 'автономный', 'автономного', 'авт',
    'район', 'района', 'рн', 'р-н', 'р-он',
    'округ', 'округа', 'городской', 'городское', 'городского',
    'муниципальный', 'муниципальное', 'муниципального',
    'сельский', 'сельское', 'сельского', 'поселение', 'поселения',
    'внутригородская', 'внутригородской', 'образование',
    'российская', 'российской', 'россия', 'федерация', 'федерации',
}
REGION_WORDS = REGION_ADJECTIVES | REGION_ADMIN_UNITS

# Stop words in address parsing
ADDRESS_STOP_WORDS = REGION_WORDS | {
    'г', 'город', 'пгт', 'рп', 'гп', 'сп', 'п', 'поселок', 'пос', 'д', 'деревня',
    'с', 'село', 'ст', 'станица', 'х', 'хутор', 'с/с', 'с/совет',
    'ул', 'улица', 'пркт', 'пр-кт', 'пр-т', 'просп', 'проспект', 'пр', 'пр-д', 'проезд',
    'пер-к', 'пер', 'переулок', 'бул', 'б-р', 'бульвар', 'ш', 'шоссе', 'наб', 'набережная',
    'пл', 'площадь', 'тракт', 'линия', 'аллея', 'туп', 'тупик', 'кв-л', 'квартал',
    'мкр', 'микрорайон', 'автодорога', 'а/д', 'территория', 'тер', 'км', 'километр',
    'дом', 'кв', 'пом', 'стр', 'корп', 'здание', 'зд', 'корпус', 'строение',
    'литера', 'лит', 'помещение', 'комн', 'оф', 'офис', 'эт', 'этаж',
    'ссив', 'дискаунтер', 'гипермаркет', 'супермаркет', 'индекс'
}

MAJOR_CITIES = {
    'москва', 'санкт-петербург', 'петербург', 'севастополь',
    'новосибирск', 'екатеринбург', 'казань', 'нижний новгород', 'челябинск',
    'красноярск', 'самара', 'уфа', 'ростов-на-дону', 'краснодар', 'омск',
    'воронеж', 'пермь', 'волгоград', 'саратов', 'тюмень', 'тольятти',
    'барнаул', 'ижевск', 'хабаровск', 'ульяновск', 'иркутск', 'ярославль',
    'владивосток', 'махачкала', 'томск', 'оренбург', 'кемерово', 'новокузнецк',
    'рязань', 'астрахань', 'набережные челны', 'пенза', 'липецк', 'киров',
    'чебоксары', 'тула', 'калининград', 'курск', 'сочи', 'ставрополь',
    'улан-удэ', 'тверь', 'магнитогорск', 'иваново', 'брянск', 'белгород',
    'сургут', 'владимир', 'чита', 'архангельск', 'калуга', 'смоленск',
    'волжский', 'саранск', 'череповец', 'курган', 'подольск', 'вологда',
    'орел', 'орёл'
}

STREET_TYPES = r'(?:улица|ул|проспект|просп|пр-кт|пр-т|пр-д|проезд|пр|переулок|пер-к|пер|бульвар(?!\s+(?:ул|улица)\b)|бул|б-р|шоссе|ш|набережная(?!\s+(?:ул|улица|пер-к|пер|переулок|пр-кт|пр-т|проспект|просп)\b)|наб|площадь(?!\s+(?:ул|улица)\b)|пл|аллея(?!\s+(?:ул|улица)\b)|тракт|тупик|туп|автодорога|а/д)'

_STREET_INITIALS = r'(?:[а-яa-z]{1,2}\.\s*){1,2}'

STREET_PATTERNS = [
    rf'\b{STREET_TYPES}(?:\.\s*|\s+)((?:{_STREET_INITIALS})?[а-яa-z0-9\-_]+(?:\s+(?:{_STREET_INITIALS}|[а-яa-z0-9\-_]+)){{0,2}})',
    rf'((?:{_STREET_INITIALS})?[а-яa-z0-9\-_]+(?:\s+(?:{_STREET_INITIALS}|[а-яa-z0-9\-_]+)){{0,2}})(?:[,\s]+|(?<=\.))\b{STREET_TYPES}(?:\.|\b)'
]

# Stop-words that can legitimately be standalone street names inside an explicit street pattern (e.g. 'Набережная ул', 'Российская ул')
NAMED_STOPWORD_STREETS = {
    'набережная', 'российская', 'россия', 'микрорайон',
    'городская', 'городской', 'окружная', 'окружной',
    'районная', 'районный', 'сельская', 'сельский',
    'областная', 'краевая', 'республиканская', 'федеральная',
    'площадь', 'линия', 'квартал', 'бульвар', 'бульварная', 'аллея', 'тракт',
}

_NUM_UNIT_CANON = {
    'линия': 'линия',
    'квартал': 'квартал', 'кв-л': 'квартал', 'квл': 'квартал',
    'мкр': 'мкр', 'мкр-н': 'мкр', 'микрорайон': 'мкр',
    'пер': 'пер', 'переулок': 'пер',
    'пр-д': 'пр-д', 'проезд': 'пр-д',
    'ул': 'ул', 'улица': 'ул',
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


def extract_km(text: str) -> str:
    """
    Extracts kilometer marker from an address or store name string.
    e.g. '7-й км, 2' -> '7'
         '7-й (автодорога Пятницкое шоссе тер.) км, 2' -> '7'
         '7 км Пятницкого ш.' -> '7'
         '24й км. МКАД' -> '24'
         'Московское ш., 18 км' -> '18'
         'км 12' -> '12'
    """
    if not text:
        return ""
    t = normalize_text(text)
    # 1. '7-й км', '7 км', '24й км', '18-й километр' (supports parenthetical insertions like '7-й (...) км')
    m1 = re.search(
        r'(?:^|[,\s(])(\d+)[- ]*(?:й|ой|ий|ый|ая)?\s*(?:\([^)]*\)\s*)?(?:км|километр)\b',
        t, re.IGNORECASE
    )
    if m1:
        return m1.group(1)
    # 2. 'км 7', 'километр 12'
    m2 = re.search(r'\b(?:км|километр)\.?\s*(\d+)\b', t, re.IGNORECASE)
    if m2:
        return m2.group(1)
    return ""


def stem_street_token(token: str) -> str:
    """
    Stems Russian street/highway adjective endings to a canonical root.
    e.g. 'пятницкое' / 'пятницкого' -> 'пятницк'
         'таллинское' / 'таллинского' -> 'таллин'
         'московское' / 'московского' -> 'москов'
         'осташковское' / 'осташковского' -> 'осташков'
         'октябрьская' / 'октябрьской' -> 'октябрь'
    """
    if not token:
        return ""
    t = token.lower()
    for suffix in (
        'ского', 'ской', 'ском', 'ское', 'ская', 'ский', 'скому', 'скую', 'ские', 'ских',
        'ного', 'ной', 'ном', 'ное', 'ная', 'ный', 'ному', 'ную', 'ные', 'ных',
        'ового', 'овой', 'овом', 'овое', 'овая', 'овый', 'овому', 'овую', 'овые', 'овых',
        'ого', 'ому', 'ым', 'им', 'ом', 'ем', 'ой', 'ей', 'ая', 'яя', 'ое', 'ее', 'ый', 'ий', 'ые', 'ие', 'ую', 'юю'
    ):
        if t.endswith(suffix) and len(t) - len(suffix) >= 3:
            return t[:-len(suffix)]
    return t


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

    # Strip trailing 5+ digit internal accounting/GLN codes after slash (e.g. 'д. 18 / 390645030')
    t = re.sub(r'\s*[/\\]\s*\d{5,}\b.*$', '', t).strip()

    # Unwrap single-letter house literas enclosed in quotes (e.g. '2"А"' -> '2а', '93 «А» база' -> '93а база', 'лит. "А"' -> 'лит. а')
    t = re.sub(r'(\d)\s*["\'«„“]([а-яa-z])["\'»“”]', r'\1\2', t)
    t = re.sub(
        r'(\b(?:к|корп|корпус|стр|строение|лит|литера)\.?)\s*["\'«„“]([а-яa-z])["\'»“”]',
        r'\1 \2',
        t,
    )

    # Strip trailing annotations in parentheses like "(А)", "(К)", "(пом. 3)"
    t = re.sub(r'[\s,]*\([а-яa-z0-9\s\.\-]+\)\s*$', '', t).strip()

    # Mask km phrases (e.g. "7-й км", "24 км", "км 18") so kilometer numbers are not mistaken for house numbers
    pat_km = r'(?:^|[,\s(])\d+[- ]*(?:й|ой|ий|ый|ая)?\s*(?:\([^)]*\)\s*)?(?:км|километр)\b|\b(?:км|километр)\.?\s*\d+\b'
    t = re.sub(pat_km, ' ', t, flags=re.IGNORECASE)

    # Cut off interior unit info (apartment, office, room, market stall/booth)
    # Skip 'кв-л' and 'кв. <quarter>, д. <num>' so quarter prefixes before a house number are not cut off
    t = re.split(
        r'\b(?:кв(?!-л)(?![^,]*,\s*(?:дом|д|зд|здание)\.?\s*(?:№\s*)?\d)|квартира|пом|помещение|комн|оф|офис|эт|этаж|место|контейнер|бутик|павильон|секция)\b',
        t
    )[0].strip()

    # 1. House with korpus/building/stroenie: e.g. "15, к 3", "д.15,к.3", "15 стр 3", "дом 2 стр Б", "д. 15 корп 2"
    m1 = re.search(
        r'(?:(?:дом|д|зд|здание)\.?\s*(?:№\s*)?)?'
        r'(\d+)\s*(?:[-\s]*(?!й\b)([а-яa-z])(?![а-яa-z]|-[а-яa-z]))?(?:\s*[/\\-]\s*(\d{1,4}(?!\d)(?:[а-яa-z](?![а-яa-z]|-[а-яa-z]))?))?'
        r'(?:[,\s/\\-]+|(?<=\d))'
        r'(?:(?:к|корп|корпус|стр|строение|лит|литера)\.?\s*(\d+(?:[а-яa-z](?![а-яa-z]|-[а-яa-z]))?|[а-яa-z](?![а-яa-z]|-[а-яa-z]))|п\.?\s*(\d+(?:[а-яa-z](?![а-яa-z]|-[а-яa-z]))?))',
        t
    )
    if m1:
        base_num = m1.group(1)
        lit = m1.group(2) or ''
        slash = m1.group(3) or ''
        korp = m1.group(4) or m1.group(5) or ''
        full = base_num + lit
        if slash:
            full += '/' + slash
        if korp:
            full += 'к' + korp
        return base_num, full

    # 2. Explicit marker: дом, д., зд., здание, вл, влд, владение, уч, участок
    m2 = re.search(
        r'\b(?:дом|д|зд|здание|вл|влд|владение|уч|участок)\.?\s*(?:№\s*)?'
        r'(\d+)\s*(?:[-\s]*(?!й\b)([а-яa-z])(?![а-яa-z]|-[а-яa-z]))?(?:\s*[/\\-]\s*(\d{1,4}(?!\d)(?:[а-яa-z](?![а-яa-z]|-[а-яa-z]))?))?',
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
    m3 = re.search(
        r'\b(?:корпус\s*строение|строение|корпус|корп|стр|к)\.?\s*(?:№\s*)?(\d+)\s*(?:[-\s]*(?!й\b)([а-яa-z])(?![а-яa-z]|-[а-яa-z]))?',
        t
    )
    if m3:
        base_num = m3.group(1)
        lit = m3.group(2) or ''
        return base_num, base_num + lit

    # Strip date/anniversary numbers (e.g. "8 марта", "9 мая", "1905 года", "30-летия Победы") so they are not treated as house numbers
    pat_date = r'\b\d+[- ]*(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря|года|лет(?:ия)?(?:\s+[а-яa-z]+)?)\b'
    t_no_date = re.sub(pat_date, '', t, flags=re.IGNORECASE)

    # 4. Number at end of address string or after comma: e.g. "Татищева бульвар, 6а" or "ул 21"
    # Strip trailing punctuation before checking end of string
    t_no_date = t_no_date.rstrip(' ,.;')
    m4 = re.search(
        r'[, ]+(\d+)\s*(?:[-\s]*(?!й\b)([а-яa-z])(?![а-яa-z]|-[а-яa-z]))?(?:\s*[/\\-]\s*(\d{1,4}(?!\d)(?:[а-яa-z](?![а-яa-z]|-[а-яa-z]))?))?\s*$',
        t_no_date
    )
    if m4:
        base_num = m4.group(1)
        lit = m4.group(2) or ''
        slash = m4.group(3) or ''
        full = base_num + lit
        if slash:
            full += '/' + slash
        return base_num, full

    # 5. Standalone number (with optional slash fraction like 399/1) that is not postal code
    nums = re.findall(
        r'\b(\d+(?:[а-яa-z](?![а-яa-z]|-[а-яa-z]))?(?:\s*[/\\]\s*\d{1,4}(?!\d)(?:[а-яa-z](?![а-яa-z]|-[а-яa-z]))?)?)\b',
        t_no_date
    )
    if nums:
        val = re.sub(r'\s*[/\\]\s*', '/', nums[-1])
        base = re.match(r'\d+', val).group(0)
        return base, val

    # If no number at all is specified in address: "б/н"
    return "б/н", "б/н"


NON_ALPHA_CODE_NOISE = {
    'ооо', 'рц', 'ао', 'зао', 'ип', 'фл', 'флп', 'спд', 'общий', 'бонус',
    'опт', 'розница', 'склад', 'рынок', 'долг', 'нал', 'упд', 'ртт',
    'магазин', 'сельмаг', 'колосок', 'продукты', 'аптека', 'весна',
    'универсам', 'гастроном', 'палатка', 'киоск', 'ларек',
}
GENERIC_STORE_PREFIXES = {
    'дискаунтер', 'гипермаркет', 'супермаркет', 'магазин', 'маг', 'тт',
}


def _format_store_code(raw_code: str, distributor: str = "") -> str:
    """Normalizes extracted store code and applies 3-digit zero-padding where configured."""
    code = raw_code.upper().translate(CYR_TO_LAT)
    if distributor in PAD_3DIGIT_CODE_NETWORKS and code.isdigit() and len(code) in (1, 2):
        code = code.zfill(3)
    return code


def extract_store_code(
    name: str,
    distributor: str = "",
    allow_alpha_code: Optional[bool] = None,
) -> str:
    """
    Extracts store code / number from a store name.
    Purely alphabetical codes (without digits) are restricted to ALPHA_CODE_NETWORKS.
    """
    if not name:
        return ""
    t = str(name).strip().replace("ё", "е").replace("Ё", "Е")
    allow_alpha = (distributor in ALPHA_CODE_NETWORKS) if allow_alpha_code is None else allow_alpha_code

    # 1. Number marker: № 604, №604, N 604, #604
    m_no = re.search(r'(?:[№#]|\bN\.?)\s*(\d+[а-яa-z0-9]*)', t, re.IGNORECASE)
    if m_no:
        return _format_store_code(m_no.group(1), distributor)

    # 2. Parentheses code: e.g. '(001) MYTISHI', 'Ашан (036) KUNCEVO', '(023) ADYGEYA', '(719) REUTOV'
    m_paren = re.search(r'\(([0-9a-zA-Zа-яА-Я]+)\)', t)
    if m_paren:
        raw_code = m_paren.group(1)
        if any(c.isdigit() for c in raw_code) or (
            allow_alpha and raw_code.lower() not in NON_ALPHA_CODE_NOISE
        ):
            return _format_store_code(raw_code, distributor)

    # 3. Known chain prefixes followed by explicit separator or digits:
    # e.g. 'Дикси ДИКСИ-78510', 'ДИКСИ-47122', 'МЕТРО 52', 'Ашан 25', 'Лента 8', 'Лента611'
    m_pref = re.search(
        r'\b(дискаунтер|гипермаркет|супермаркет|магазин|маг|тт|пятерочка|верный|атак(?:\s+ооо)?|чижик|даркстор|x5|х5|дикси|метро|metro|ашан|лента)(?:[_ \-]+|(?=\d))(?:дикси[_ \-]+)?([0-9a-zA-Zа-яА-Я]+)\b',
        t, re.IGNORECASE
    )
    if m_pref:
        prefix, raw_code = m_pref.group(1).lower(), m_pref.group(2)
        if raw_code.lower() not in {'ооо', 'рц', 'ао', 'зао'}:
            has_digit = any(c.isdigit() for c in raw_code)
            if has_digit or (
                allow_alpha
                and prefix not in GENERIC_STORE_PREFIXES
                and raw_code.lower() not in NON_ALPHA_CODE_NOISE
            ):
                return _format_store_code(raw_code, distributor)

    # 4. Pure code: 1 to 7 alphanumeric characters (e.g. '1', '36', '5268', '548', '363H', 'HA3A', '204', 'ЯРС')
    if re.match(r'^[0-9a-zA-Zа-яА-Я]{1,7}$', t):
        if any(c.isdigit() for c in t) or (allow_alpha and t.lower() not in NON_ALPHA_CODE_NOISE):
            return _format_store_code(t, distributor)

    # 5. Digits/code followed by chain name: e.g. '77531 Дикси'
    m_trail = re.search(r'^([0-9a-zA-Zа-яА-Я]+)\s+(?:дикси|метро|metro|ашан|лента)\b', t, re.IGNORECASE)
    if m_trail:
        raw_code = m_trail.group(1)
        if any(c.isdigit() for c in raw_code) or (allow_alpha and raw_code.lower() not in NON_ALPHA_CODE_NOISE):
            return _format_store_code(raw_code, distributor)

    # 6. Alphanumeric store codes in mixed text: e.g. H085, 304S, 31Y6, E231
    m_code = re.search(r'(?:^|[^a-zA-Zа-яА-Я0-9])([a-zA-Zа-яА-Я0-9]{3,6})(?:$|[^a-zA-Zа-яА-Я0-9])', t)
    if m_code:
        raw_code = m_code.group(1)
        if any(c.isdigit() for c in raw_code):
            return _format_store_code(raw_code, distributor)

    return ""


def _strip_leading_accounting_id(text: str) -> str:
    """Removes leading distributor numeric accounting IDs (e.g. '3907.', '124395 '), keeping '1000 Мелочей'."""
    stripped = re.sub(
        r'^\s*(?:\d{4,7}\s*[.,_-]+\s*|\d{5,7}\s+(?=[а-яa-z])|\d{4}\s+(?!мелочей\b|год|лет)(?=[а-яa-z]))',
        ' ',
        text,
    )
    return stripped if re.search(r'[а-яa-z]', stripped) else text


def clean_store_name(name: str, strip_leading_id: bool = False) -> str:
    """
    Cleans a store name by removing legal forms (ООО, ИП, ФЛП, Индивидуальный предприниматель),
    payment/accounting noise tails, punctuation, initials, and km markers.
    """
    if not name:
        return ""
    t = str(name).lower().replace("ё", "е")
    if strip_leading_id:
        t = _strip_leading_accounting_id(t)
    # Remove leading country prefix 'РФ ...'
    t = re.sub(r'^\s*рф\b[\s,.-]*(?=[а-яa-z0-9])', ' ', t)
    # Remove delivery/status annotations
    t = re.sub(r'-?\s*адрес\s+доставки(?:_\d+)?', ' ', t)
    t = re.sub(r'\(\s*(?:нет\s+договора|общий|бонус|зк|закрыт[оаы]?|нал|безнал|долг|упд)\s*\)', ' ', t)
    t = re.sub(r'\bиндивидуальн(?:ый|ого)\s+предпринимател[ья]\b', ' ', t)
    t = re.sub(r'\b\d+\s*%\s*п\s*[/\\.]?\s*о\b', ' ', t)
    t = re.sub(r'\bп\s*[/\\.]\s*о\b', ' ', t)
    t = re.sub(r'\b\d+\s*упд\s*\+\s*\d+\s*расх\b', ' ', t)
    t = re.sub(r'\b\d+\s*(?:дн(?:ей|я)?|дн)\b(?:\s*\.\s*[а-я](?![а-я]))?', ' ', t)
    t = re.sub(r'\b(?:нет\s+договора|чек\s+ккм|за\s+наличк[уа]|наличк[уа])\b', ' ', t)
    t = re.sub(r'\b(?:эл\.?\s*накл\.?|(?:торг|т)[- ]?12)\b', ' ', t)
    t = re.sub(r'\b(?:т|тел)\.?\s*[:\-]?\s*(?:\+7|8|7)?[\d\-]{7,12}\b', ' ', t)
    # Remove quotes, brackets, store symbols
    t = re.sub(r'["\'\(\)\[\]«»„“”№#_]', ' ', t)
    # Remove person initials like "в.в.", "е.а.", "а.в" without chopping the first letter of following words (e.g. "г. Калининград")
    t = re.sub(r'\b[а-яa-z]\s*\.\s*(?:[а-яa-z]\s*\.?(?![а-яa-z]))?', ' ', t)
    # Remove km phrases (e.g. "7 км", "7-й км") so "ГМ Москва Пятницкое 7 км" -> "гм москва пятницкое"
    t = re.sub(r'\b\d+[- ]*(?:й|ой|ий|ый|ая)?\s*(?:км|километр)\b', ' ', t, flags=re.IGNORECASE)
    words = re.findall(r'[а-яa-z0-9]+', t)
    cleaned = [w for w in words if w not in LEGAL_FORMS]
    # Remove format word 'розница' only if other meaningful tokens remain
    if any(w != 'розница' for w in cleaned):
        cleaned = [w for w in cleaned if w != 'розница']
    return ' '.join(cleaned)


PATRONYMIC_ENDINGS = ('ович', 'евич', 'ич', 'овна', 'евна', 'ична', 'инична', 'оглы', 'кызы')
NON_SURNAME_WORDS = LEGAL_FORMS | ADDRESS_STOP_WORDS | {
    'индивидуальный', 'предприниматель', 'продукты', 'аптека', 'торг', 'рынок',
    'павильон', 'место', 'контейнер', 'бутик', 'отдел', 'секция', 'ларек',
    'киоск', 'хозяин', 'хозяюшка', 'галамарт', 'краснодар', 'москва', 'россия',
    'украина', 'розница', 'опт', 'общий', 'бонус', 'договора', 'нет', 'бывш',
}


def normalize_surname(surname: str) -> str:
    """Normalizes Russian feminine surname endings to masculine base for family matching."""
    s = surname.lower().replace('ё', 'е')
    for f_end, m_end in (
        ('ова', 'ов'), ('ева', 'ев'), ('ина', 'ин'), ('ына', 'ын'),
        ('ская', 'ский'), ('цкая', 'цкий'),
    ):
        if s.endswith(f_end) and len(s) > len(f_end) + 2:
            return s[:-len(f_end)] + m_end
    return s


def normalize_patronymic(patronymic: str) -> str:
    """Normalizes patronymic gender endings (e.g. 'арменовна' -> 'арменович', 'кызы' -> 'оглы')."""
    p = patronymic.lower().replace('ё', 'е').strip()
    for f_end, m_end in (
        ('овна', 'ович'), ('евна', 'евич'), ('ична', 'ич'), ('инична', 'ич'),
    ):
        if p.endswith(f_end) and len(p) > len(f_end) + 2:
            return p[:-len(f_end)] + m_end
    if p.endswith(' кызы'):
        return p[:-5] + ' оглы'
    return p


def extract_fio_surname_patronymic(name: str) -> Optional[Tuple[str, str]]:
    """
    Extracts normalized (surname, patronymic) from a full Cyrillic FIO in store name.
    Returns None if the record does not contain a recognizable Surname + Name + Patronymic
    or appears to be an LLC/corporate entity (ООО/ЗАО/ОАО/ПАО without ИП/ФЛП/СПД).
    """
    if not name:
        return None
    t = str(name).lower().replace('ё', 'е')
    if re.search(r'\b(?:ооо|зао|оао|пао)\b', t) and not re.search(
        r'\b(?:ип|индивидуальн(?:ый|ого)\s+предпринимател[ья]|флп|фл|спд)\b', t
    ):
        return None
    t = _strip_leading_accounting_id(t)
    t = re.sub(r'\bиндивидуальн(?:ый|ого)\s+предпринимател[ья]\b', ' ', t)
    t = re.sub(r'\b\d+\s*(?:дн(?:ей|я)?|дн)\b', ' ', t)
    words = [w for w in re.findall(r'[а-я]+', t) if len(w) >= 2 and w not in NON_SURNAME_WORDS]
    if len(words) < 3:
        return None
    for idx in range(2, min(len(words), 6)):
        w = words[idx]
        if w in ('оглы', 'кызы') and idx >= 3:
            surname, first_name, raw_pat = words[idx - 3], words[idx - 2], f"{words[idx - 1]} {w}"
        elif w.endswith(PATRONYMIC_ENDINGS) and w not in ('оглы', 'кызы'):
            surname, first_name, raw_pat = words[idx - 2], words[idx - 1], w
        else:
            continue
        if len(surname) >= 3 and len(first_name) >= 2:
            return normalize_surname(surname), normalize_patronymic(raw_pat)
    return None


def extract_detskiy_mir_format(name: str) -> str:
    """
    Extracts store format prefix for 'ДЕТСКИЙ МИР ПАО'.
    Returns one of: 'ДМ МИНИ', 'ДМ', 'ЗОО', 'РЦ', or ''.
    """
    if not name:
        return ""
    n = str(name).strip().upper().replace("Ё", "Е")
    if re.match(r'^ДМ\s+МИНИ\b', n):
        return "ДМ МИНИ"
    if re.match(r'^ДМ\b', n):
        return "ДМ"
    if re.match(r'^ЗОО\b', n):
        return "ЗОО"
    if re.match(r'^РЦ\b', n):
        return "РЦ"
    return ""


def _extract_numbered_or_lettered_street(text: str) -> List[str]:
    """
    Extracts canonical numbered/lettered street or microdistrict tokens when no word-named street exists.
    e.g. '1 Линия ул' / '1-я Линия ул' -> ['1_линия']
         '4 Квартал ул' / '4-й кв-л' / 'кв-л 4' -> ['4_квартал']
         '35-й мкр' / '24 мкр' / 'микрорайон 5' -> ['35_мкр'], ['24_мкр'], ['5_мкр']
         'пер 5-й' / 'ул. 5-ый переулок' -> ['5_пер']
         'Квартал А' / 'В мкр' -> ['а_квартал'], ['в_мкр']
    """
    m = re.search(
        r'(?:^|[^а-яa-z0-9])(\d+)(?:-?(?:й|я|ый|ая|ой|ий|е|ое))?\s*'
        r'(?:в\.?\s*о\.?\s*)?(линия|квартал|кв-л|квл|мкр-н|мкр|микрорайон)\b',
        text,
    )
    if m:
        return [f"{m.group(1)}_{_NUM_UNIT_CANON[m.group(2)]}"]

    m = re.search(
        r'\b(линия|квартал|кв-л|квл|мкр-н|мкр|микрорайон)\.?\s*(?:№\s*)?(\d+)(?:-?(?:й|я|ый|ая|ой|ий|е|ое))?(?=$|[^а-яa-z0-9])',
        text,
    )
    if m:
        return [f"{m.group(2)}_{_NUM_UNIT_CANON[m.group(1)]}"]

    m = re.search(
        r'(?:^|[^а-яa-z0-9])(\d+)(?:-?(?:й|я|ый|ая|ой|ий)\s*(переулок|пер|проезд|пр-д|улица|ул)\b|\s+(переулок|пер|проезд|пр-д)\s+(?:ул|улица)\b)',
        text,
    )
    if m:
        unit = m.group(2) or m.group(3)
        return [f"{m.group(1)}_{_NUM_UNIT_CANON[unit]}"]

    m = re.search(
        r'\b(переулок|пер|проезд|пр-д|улица|ул)\.?\s*(\d+)-?(?:й|я|ый|ая|ой|ий)\b',
        text,
    )
    if m:
        return [f"{m.group(2)}_{_NUM_UNIT_CANON[m.group(1)]}"]

    m = re.search(
        r'(?:^|[,\s])([а-яa-z])\s+(квартал|кв-л|мкр-н|мкр|микрорайон)'
        r'(?:\.?\s*(?:,|$|\b(?:дом|д|зд|стр|корп|к|тер|территория)\b|\d))',
        text,
    )
    if m:
        return [f"{m.group(1)}_{_NUM_UNIT_CANON[m.group(2)]}"]

    m = re.search(
        r'\b(квартал|кв-л|мкр-н|мкр|микрорайон)\.?\s+([а-яa-z])(?=$|[\s,])(?!\s*\d)',
        text,
    )
    if m:
        return [f"{m.group(2)}_{_NUM_UNIT_CANON[m.group(1)]}"]

    return []


def extract_address_details(raw_addr: str) -> Tuple[str, str, str, List[str]]:
    """
    Extracts normalized address details:
    Returns: (base_house, full_house, city, street_tokens)
    """
    t = normalize_text(raw_addr)
    # Strip trailing annotations in parentheses
    t = re.sub(r'[\s,]*\([а-яa-z0-9\s\.\-]+\)\s*$', '', t).strip()
    base_house, full_house = extract_house_components(t)

    # Clean address from postal code, municipal 'г.о.' prefix, parenthetical rural-settlement annotations, and unroll internal parentheses
    addr_clean = re.sub(r'\b\d{6}\b', '', t)
    addr_clean = re.sub(r'\bг\.?\s*о\.?(?=$|[^а-яa-z])', ' ', addr_clean)
    addr_clean = re.sub(
        r'\(\s*[^)]*\b(?:с/п|с/с|с/о|г/п|с/пос|сельсовет|поселение)\b[^)]*\)',
        ' ',
        addr_clean,
    )
    addr_clean_raw_parens = addr_clean
    addr_clean = addr_clean.replace('(', ' , ').replace(')', ' , ').replace('_', ' ')
    # Mask km phrases before street extraction so km digits/units don't pollute street tokens
    pat_km = r'(?:^|[,\s(])\d+[- ]*(?:й|ой|ий|ый|ая)?\s*(?:\([^)]*\)\s*)?(?:км|километр)\b|\b(?:км|километр)\.?\s*\d+\b'
    addr_clean_no_km = re.sub(pat_km, ' ', addr_clean, flags=re.IGNORECASE)
    # Canonicalize anniversary street numbers ('30 лет Победы' / '30-летия Победы' -> '30_лет победы')
    addr_clean_no_km = re.sub(r'\b(\d+)[- ]*лет(?:ия)?\b', r'\1_лет', addr_clean_no_km)

    parts = [p.strip() for p in addr_clean.split(',') if p.strip()]

    city = ""
    settlement_words = set()

    # Check major cities deterministically with word boundaries (supports glued 'гМосква')
    # Skip matches used as street names or districts/regions (e.g. 'р-н Волжский', 'Волжский р-н')
    city_matches = []
    for mc in sorted(MAJOR_CITIES, key=len, reverse=True):
        for m_city in re.finditer(rf'(?:^|[^а-яa-z])(?:г\.?\s*)?({re.escape(mc)})(?=$|[^а-яa-z])', t):
            prefix_ctx = t[max(0, m_city.start(1) - 16):m_city.start(1)]
            suffix_ctx = t[m_city.end(1):min(len(t), m_city.end(1) + 16)]
            if re.search(
                rf'\b(?:{STREET_TYPES}|р-н|р\.?\s*н|район|района|м\.?\s*р-н|обл|область|области|край|края|респ|республика|республики|с/п|с/с|с/о|г/п)\.?\s*$',
                prefix_ctx,
            ):
                continue
            if not re.search(r'\bг\.?\s*$', prefix_ctx) and re.search(
                r'^\s+(?:р-н|район|района)\b\s*(?:,|$)|^\s+(?:обл|область|области|край|края|респ|республика|республики|с/п|с/с|с/о|г/п)\b',
                suffix_ctx,
            ):
                continue
            city_matches.append((m_city.start(1), mc))
            break
    if city_matches:
        city_matches.sort(key=lambda item: (item[0], -len(item[1])))
        best_city = city_matches[0][1]
        settlement_words.update(best_city.split())
        if not city:
            city = best_city

    # Check settlement indicators (ignore slash admin abbreviations like 'с/п', 'с/с', 'с/о', 'г/п'
    # and person initials inside street names like 'С.Юлаева ул', 'Г.Петровой ул', 'Ст.Разина ул')
    for pat_idx, pat in enumerate([
        r'\b(?:город|поселок|пос|село|деревня|станица|хутор|пгт|рп|гп|сп)(?:\.\s*|\s+)([а-яa-z0-9\-]+)',
        r'(?<![/\\])\b(?:г|п|с|д|х|ст)\.(?![/\\])[\s]*([а-яa-z0-9\-]+)',
        r'(?<![/\\])\b(?:г|п|с|х|ст)\s+([а-яa-z0-9\-]+)',
        r'\b([а-яa-z0-9\-]+)\s+(?:г|п|с|д|пгт|рп|гп|сп)\b(?![/\\])'
    ]):
        for m in re.finditer(pat, addr_clean):
            if pat_idx in (1, 2):
                before_ctx = addr_clean[max(0, m.start() - 20):m.start()]
                after_ctx = addr_clean[m.end():min(len(addr_clean), m.end() + 30)]
                if re.search(rf'(?:\b(?:{STREET_TYPES}|им|имени)\.?\s*|\b[а-яa-z]\.\s*)$', before_ctx):
                    continue
                if re.search(
                    rf'^\s+(?:[а-яa-z]\.\s*)*{STREET_TYPES}(?:\.?\s*(?:,|$|\b(?:дом|д|зд|здание|стр|корп|к)\b)|\s+\d+[а-яa-z]?(?:[/\\]\d+)?(?:\s*(?:,|$|\b(?:к|корп|корпус|стр|строение|лит|литера|кв|пом|оф|маг|м-н|тц|трц|тк)\b)))',
                    after_ctx,
                ):
                    continue
            w = m.group(1).strip()
            if len(w) >= 2 and w not in {'ул', 'улица', 'дом', 'стр', 'корп', 'кв', 'пом', 'обл', 'область', 'край', 'район', 'рн', 'р-н'}:
                settlement_words.add(w)
                if not city and w not in ADDRESS_STOP_WORDS and not w.isdigit():
                    city = w

    # Detect administrative regions and districts to prevent them from leaking into street tokens
    for pat in [
        r'\b([а-яa-z0-9\-]+)\s+(?:обл|область|области|край|края|респ|республика|республики|р-н|район|района|округ|округа|ао|с/п|с/с|с/о|г/п)\b',
        r'\b(?:обл|область|области|край|края|респ|республика|республики|р-н|район|района|округ|округа|ао|с/п|с/с|с/о|г/п)\.?\s*([а-яa-z0-9\-]+)',
    ]:
        for m in re.finditer(pat, addr_clean):
            w = m.group(1).strip()
            if len(w) >= 2 and w not in {'ул', 'улица', 'дом', 'стр', 'корп', 'кв', 'пом'}:
                settlement_words.add(w)

    # Detect city from comma-separated parts if not found (skip street/house-bearing or comma-less whole strings)
    for part in parts:
        if re.search(rf'\b(?:{STREET_TYPES}|дом|д|зд|здание|стр|корп|кв|рынок)\b', part):
            continue
        words = re.findall(r'[а-яa-z0-9]+', part)
        if len(parts) == 1 and len(words) > 4:
            continue
        if any(w in {'г', 'город', 'пгт', 'рп', 'гп', 'сп', 'п', 'поселок'} for w in words):
            c_words = [w for w in words if len(w) >= 2 and w not in ADDRESS_STOP_WORDS and not w.isdigit()]
            if c_words:
                settlement_words.update(c_words)
                if not city:
                    city = ' '.join(c_words)

    # Extract clean street tokens using explicit street patterns on text without km
    # Inside explicit street patterns (e.g. 'ул. Московская'), region adjectives are valid street names
    explicit_street_stop_words = ADDRESS_STOP_WORDS - REGION_ADJECTIVES
    city_tokens = set(city.split()) if city else set()
    street_words = []
    explicit_fallback_words = []
    for pat in STREET_PATTERNS:
        for m in re.finditer(pat, addr_clean_no_km):
            cand = m.group(1).strip()
            cand = re.split(
                r'(?<=[а-яa-z])\s+\d+(?!-[а-яa-z])\b|\s+\b(?:дом|д|зд|стр|корп|к|пом|оф|кв|ртт|маг|магазин|рынок|кафе|павильон|место|бутик|контейнер|тц|трц|тк)\b',
                cand,
            )[0]
            cand = re.sub(r'^\d+(?![\d_])\s*|(?:\s+|^)\d+$', '', cand).strip()
            cand_tokens = re.findall(r'[а-яa-z0-9_]+', cand)
            words = [
                w for w in cand_tokens
                if len(w) >= 3 and w not in explicit_street_stop_words and w not in settlement_words and ('_' in w or not any(c.isdigit() for c in w))
            ]
            if not words:
                # Preserve street names matching an oblast adjective (e.g. 'Московская обл, Подольск, ул. Московская')
                words = [
                    w for w in cand_tokens
                    if len(w) >= 3 and w not in explicit_street_stop_words and w not in city_tokens and ('_' in w or not any(c.isdigit() for c in w))
                ]
            if words:
                street_words = words
                break
            if not explicit_fallback_words and ',' not in m.group(0):
                # Remember stopword/city-named explicit street (e.g. 'Набережная ул', 'Российская ул', 'Ананур ул')
                # to use only if the address is not a numbered line/quarter/lane (e.g. '1 Линия ул', '4 Квартал ул')
                cand_fb = [
                    w for w in cand_tokens
                    if len(w) >= 3 and not any(c.isdigit() for c in w) and (
                        w in NAMED_STOPWORD_STREETS or (w in city_tokens and w not in ADDRESS_STOP_WORDS)
                    )
                ]
                if cand_fb:
                    explicit_fallback_words = cand_fb
        if street_words:
            break

    # Numbered/lettered lines, quarters, microdistricts, lanes (e.g. '1 Линия ул', '4 Квартал ул', '35-й мкр', 'пер 5-й', 'В мкр')
    if not street_words:
        street_words = _extract_numbered_or_lettered_street(addr_clean_no_km)

    # Restore explicit stopword or village-named street (e.g. 'Набережная ул', 'Российская ул', 'Россия пр-кт', 'Ананур ул')
    if not street_words and explicit_fallback_words:
        street_words = explicit_fallback_words

    # Fallback if street pattern didn't match: exclude all region/city/settlement/stop words
    if not street_words:
        # Cut off trailing house/shop details (e.g. 'кв-л Металлург 16 РТТ маг."Бытовая химия"' -> '... Металлург',
        # 'мкр Зелёный, д. 64, Новые ряды маг Бытовая Химия' -> '... зеленый')
        # Preserve leading microdistricts ('м-н Горняцкий, д. 5') and standalone landmarks ('Первомайский рынок')
        fb_tail_re = (
            r'\b(?:дом|здание|ртт|магазин|павильон|контейнер|бутик|тц|трц|тк)\b'
            r'|\b(?:д|зд)\.?\s*(?:№\s*)?\d+[а-яa-z]?\b'
            r'|\bмаг(?:\.|(?=\s|$|["«„,]))'
            r'|\b\d+[а-яa-z]?(?:[/\\]\d+)?\s+(?:ртт|маг|магазин|тц|трц|тк|павильон)\b'
        )
        addr_no_parens = re.sub(r'\([^)]*\)', ' ', addr_clean_raw_parens).replace('_', ' ')
        addr_no_parens_no_km = re.sub(pat_km, ' ', addr_no_parens, flags=re.IGNORECASE)
        addr_no_parens_no_km = re.sub(r'\b(\d+)[- ]*лет(?:ия)?\b', r'\1_лет', addr_no_parens_no_km)
        fb_no_parens = re.split(fb_tail_re, addr_no_parens_no_km)[0]
        fb_text = re.split(fb_tail_re, addr_clean_no_km)[0]
        for candidate_src in (fb_no_parens, fb_text, addr_clean_no_km):
            all_words = re.findall(r'[а-яa-z0-9_]+', candidate_src)
            for w in all_words:
                if len(w) >= 3 and w not in ADDRESS_STOP_WORDS and w not in settlement_words and ('_' in w or not any(c.isdigit() for c in w)):
                    if not city or w not in city.split():
                        street_words.append(w)
            if street_words:
                break

    return base_house, full_house, city, street_words


def get_address_blocking_keys(
    raw_addr: str = "",
    store_name: str = "",
    base_house: Optional[str] = None,
    city: Optional[str] = None,
    street_tokens: Optional[List[str]] = None,
    store_code: Optional[str] = None,
    km: Optional[str] = None,
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

    if km is None and raw_addr:
        km = extract_km(raw_addr) or extract_km(store_name)

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
    stemmed_tokens = [stem_street_token(st) for st in street_tokens]

    if not street_tokens and city_token and base_house != "б/н":
        keys.append((f"city_{city_token}", base_house))

    if city_token:
        for st in street_tokens[:3]:
            keys.append((f"{city_token}_{st}", base_house))
        for stem in stemmed_tokens[:3]:
            if stem:
                keys.append((f"{city_token}_{stem}", base_house))

    for st in street_tokens[:3]:
        keys.append((st, base_house))

    for stem in stemmed_tokens[:3]:
        if stem and stem not in street_tokens:
            keys.append((stem, base_house))

    # KM-based blocking keys
    if km:
        keys.append((f"km_{km}", base_house))
        for stem in stemmed_tokens[:2]:
            if stem:
                keys.append((f"{stem}_km{km}", "km"))

    return keys

