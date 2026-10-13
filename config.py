"""Configuration settings for Outlets Deduplication."""

from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
RESULTS_DIR = PROJECT_ROOT / "Results"

# National retail network distributors that must be matched in isolation
NATIONAL_NETWORKS = {
    "Атак take off c 01.01.2019",
    "АШАН ООО (take-off) с 01.04.2018",
    "ГИПЕРГЛОБУС ООО (take-off)",
    "ДЕТСКИЙ МИР ПАО",
    "Дикси Юг АО (take-off) с 01.04.2018",
    "Лента ООО (take-off) с 01.04.2018",
    "МЕТРО КЭШ ЭНД КЕРРИ ООО (take-off) с 01.04.2018",
    "ОКЕЙ ООО (take off)",
    "ПЕРЕКРЕСТОК ТД АО",
    "ПЯТЁРОЧКА",
    "СОЮЗ СВ. ИОАННА ВОИНА ООО (take-off) с 01.04.2018",
    "ТАНДЕР АО (take-off) с 01.04.2018",
}

# Distributors that require strictly identical subnetwork ("Подсеть") and Name
STRICT_SUBNETWORK_DISTRIBUTORS = {
    "ТАНДЕР АО (take-off) с 01.04.2018",
}

# Distributors that require strictly identical store code in Name AND subnetwork ("Подсеть")
CODE_AND_SUBNETWORK_DISTRIBUTORS = {
    "ПЕРЕКРЕСТОК ТД АО",
}

# National retail networks where matching is strictly by store code in Name
CODE_BASED_NETWORKS = {
    "Атак take off c 01.01.2019",
    "АШАН ООО (take-off) с 01.04.2018",
    "Дикси Юг АО (take-off) с 01.04.2018",
    "Лента ООО (take-off) с 01.04.2018",
    "МЕТРО КЭШ ЭНД КЕРРИ ООО (take-off) с 01.04.2018",
    "ПЯТЁРОЧКА",
    "СОЮЗ СВ. ИОАННА ВОИНА ООО (take-off) с 01.04.2018",
}

# Distributors that require padding 1- or 2-digit store codes to 3 digits (e.g. '1' -> '001', '36' -> '036')
PAD_3DIGIT_CODE_NETWORKS = {
    "АШАН ООО (take-off) с 01.04.2018",
    "Лента ООО (take-off) с 01.04.2018",
}

# Detskiy Mir distributor and store format prefixes
DETSKIY_MIR_DISTRIBUTOR = "ДЕТСКИЙ МИР ПАО"
DETSKIY_MIR_FORMATS = ("ДМ МИНИ", "ДМ", "ЗОО", "РЦ")

# Globus hypermarket distributor and known location abbreviations
GLOBUS_DISTRIBUTOR = "ГИПЕРГЛОБУС ООО (take-off)"

GLOBUS_CITY_ABBREVIATIONS = {
    "БЛШ": "балашиха",
    "ВЛД": "владимир",
    "КЛГ": "калуга",
    "КЛМ": "климовск",
    "КМН": "коммунарка",
    "КРЛ": "королев",
    "КРС": "красногорск",
    "КСН": "косино",
    "КТЛ": "котельники",
    "МДВ": "медведково",
    "МТН": "митино",
    "ОДН": "одинцово",
    "ПШК": "пушкино",
    "РЯЗ": "рязань",
    "СЛР": "саларьево",
    "ТВР": "тверь",
    "ТУЛ": "тула",
    "ТУЛ2": "тула2",
    "ТШН": "тушино",
    "ЩЛК": "щелково",
    "ЭЛС": "электросталь",
    "ЯРС": "ярославль",
}

# Status strings
STATUS_IDENTICAL = "Одинаковая"
STATUS_SIMILAR = "Похожая"
STATUS_UNIQUE = "Уникальная"

# RapidFuzz similarity thresholds (0-100)
NAME_EXACT_THRESHOLD = 95
NAME_SIMILAR_THRESHOLD = 68

# Output options
INCLUDE_SIMILARITY_PERCENT: bool = True

# Border agglomeration city groups for major highways / ring roads
BORDER_AGGLOMERATIONS = [
    # Moscow & near Moscow Oblast satellite cities
    {
        "москва", "красногорск", "химки", "мытищи", "люберцы", "котельники",
        "реутов", "видное", "одинцово", "ленинский", "балашиха", "дзержинский",
        "подольск", "долгопрудный", "отрадное", "мо", "московская"
    },
    # Saint Petersburg & Leningrad Oblast border districts / settlements
    {
        "санкт-петербург", "петербург", "спб", "ленинградская", "ло", "ломоносовский", "всеволожский",
        "всеволожск", "кудрово", "мурино", "виллози", "гатчинский", "гатчина",
        "старо-паново", "паново"
    }
]

# Output filename pattern
OUTPUT_FILENAME_PATTERN = "Deduplication_results-%Y%m%d%H%M.xlsx"

