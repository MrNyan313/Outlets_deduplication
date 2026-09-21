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

# Status strings
STATUS_IDENTICAL = "Одинаковая"
STATUS_SIMILAR = "Похожая"
STATUS_UNIQUE = "Уникальная"

# RapidFuzz similarity thresholds (0-100)
NAME_EXACT_THRESHOLD = 95
NAME_SIMILAR_THRESHOLD = 68

# Output filename pattern
OUTPUT_FILENAME_PATTERN = "Deduplication_results-%Y%m%d%H%M.xlsx"
