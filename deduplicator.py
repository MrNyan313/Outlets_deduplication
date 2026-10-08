"""Outlets Deduplication Engine."""

from collections import defaultdict
from typing import List, Dict, Any, Tuple, Optional
from rapidfuzz import fuzz

from config import (
    NATIONAL_NETWORKS,
    STRICT_SUBNETWORK_DISTRIBUTORS,
    CODE_BASED_NETWORKS,
    PAD_3DIGIT_CODE_NETWORKS,
    STATUS_IDENTICAL,
    STATUS_SIMILAR,
    STATUS_UNIQUE,
    NAME_EXACT_THRESHOLD,
    NAME_SIMILAR_THRESHOLD,
)
from normalizer import (
    extract_address_details,
    extract_house_components,
    get_address_blocking_keys,
    extract_store_code,
    clean_store_name,
    normalize_text,
)


class OutletRecord:
    """Lightweight representation of an outlet record with pre-extracted features."""
    __slots__ = (
        'index',
        'raw_row',
        'id',
        'name',
        'address',
        'is_vendor',
        'distributor',
        'subnetwork',
        'base_house',
        'full_house',
        'city',
        'street_tokens',
        'store_code',
        'clean_name',
        'blocking_keys',
        'is_national',
    )

    def __init__(self, index: int, raw_row: tuple, col_indices: Dict[str, int]):
        self.index = index
        self.raw_row = raw_row

        self.id = str(raw_row[col_indices['id']]).strip()
        self.name = str(raw_row[col_indices['Name']]).strip()
        self.address = str(raw_row[col_indices['AccountingSystemAddress']]).strip()
        
        vendor_val = str(raw_row[col_indices['IsVendor']]).strip()
        self.is_vendor = 1 if vendor_val == '1' else 0

        self.distributor = str(raw_row[col_indices['Дистрибьютор']]).strip()
        self.is_national = self.distributor in NATIONAL_NETWORKS

        if 'Подсеть' in col_indices:
            sub_val = raw_row[col_indices['Подсеть']]
            self.subnetwork = str(sub_val).strip() if (sub_val is not None and str(sub_val) != 'None') else ""
        else:
            self.subnetwork = ""

        # Pre-extracted features from primary address
        base_h, full_h, city, street_tokens = extract_address_details(self.address)
        self.base_house = base_h
        self.full_house = full_h
        self.city = city
        self.street_tokens = street_tokens

        # Fallback to Street column if available and primary address was incomplete
        if 'Street' in col_indices:
            street_col = str(raw_row[col_indices['Street']]).strip()
            if street_col and street_col != "None":
                if self.base_house == "б/н":
                    st_base, st_full = extract_house_components(street_col)
                    if st_base != "б/н":
                        self.base_house = st_base
                        self.full_house = st_full
                if not self.street_tokens or not self.city:
                    _, _, st_city, st_tokens = extract_address_details(street_col)
                    if not self.city and st_city:
                        self.city = st_city
                    if not self.street_tokens and st_tokens:
                        self.street_tokens = st_tokens

        self.store_code = extract_store_code(self.name, self.distributor)
        self.clean_name = clean_store_name(self.name)

        if self.distributor in CODE_BASED_NETWORKS:
            # Code-based networks only match by store code!
            if self.store_code:
                self.blocking_keys = [(f"code_{self.distributor}_{self.store_code}", "code")]
            else:
                self.blocking_keys = []
        elif self.distributor in STRICT_SUBNETWORK_DISTRIBUTORS:
            # Strict Name + Subnetwork distributors (Тандер, Перекресток)
            clean_n = normalize_text(self.name)
            clean_sub = normalize_text(self.subnetwork)
            if clean_n and clean_sub:
                self.blocking_keys = [(f"strict_sub_{self.distributor}_{clean_n}_{clean_sub}", "strict_sub")]
            else:
                self.blocking_keys = []
        elif self.is_vendor:
            # Master coverage points can match code-based networks, strict subnetwork networks, or regular distributors
            keys = []
            if self.store_code:
                for net in CODE_BASED_NETWORKS:
                    c = self.store_code
                    if net in PAD_3DIGIT_CODE_NETWORKS and c.isdigit() and len(c) in (1, 2):
                        c = c.zfill(3)
                    keys.append((f"code_{net}_{c}", "code"))
            clean_n = normalize_text(self.name)
            clean_sub = normalize_text(self.subnetwork)
            if clean_n and clean_sub:
                for dist in STRICT_SUBNETWORK_DISTRIBUTORS:
                    keys.append((f"strict_sub_{dist}_{clean_n}_{clean_sub}", "strict_sub"))
            keys.extend(get_address_blocking_keys(
                raw_addr=self.address,
                store_name=self.name,
                base_house=self.base_house,
                city=self.city,
                street_tokens=self.street_tokens,
                store_code=self.store_code,
            ))
            self.blocking_keys = keys
        else:
            # Regular distributor outlets
            self.blocking_keys = get_address_blocking_keys(
                raw_addr=self.address,
                store_name=self.name,
                base_house=self.base_house,
                city=self.city,
                street_tokens=self.street_tokens,
                store_code=self.store_code,
            )


def calculate_outlet_match_score(
    outlet1: OutletRecord,
    outlet2: OutletRecord
) -> Tuple[float, bool]:
    """
    Calculates similarity between two outlets.
    Returns: (score, is_exact_match)
    """
    # 0. STRICT NAME + SUBNETWORK RULE for STRICT_SUBNETWORK_DISTRIBUTORS (ТАНДЕР, ПЕРЕКРЕСТОК)
    # Outlets match IF AND ONLY IF both Name and Подсеть match identically!
    if (
        outlet1.distributor in STRICT_SUBNETWORK_DISTRIBUTORS
        or outlet2.distributor in STRICT_SUBNETWORK_DISTRIBUTORS
    ):
        if not outlet1.is_vendor and not outlet2.is_vendor and outlet1.distributor != outlet2.distributor:
            return 0.0, False
        n1 = normalize_text(outlet1.name)
        n2 = normalize_text(outlet2.name)
        s1 = normalize_text(outlet1.subnetwork)
        s2 = normalize_text(outlet2.subnetwork)
        if n1 and s1 and n1 == n2 and s1 == s2:
            return 100.0, True
        return 0.0, False

    # 1. CODE-BASED NETWORKS RULE (Атак, Ашан, Дикси, Лента, Метро, Пятёрочка, СОЮЗ СВ. ИОАННА ВОИНА)
    # Outlets match IF AND ONLY IF store codes match identically!
    if (
        outlet1.distributor in CODE_BASED_NETWORKS
        or outlet2.distributor in CODE_BASED_NETWORKS
    ):
        if not outlet1.is_vendor and not outlet2.is_vendor and outlet1.distributor != outlet2.distributor:
            return 0.0, False
        c1 = outlet1.store_code
        c2 = outlet2.store_code
        # Apply 3-digit padding if matching with/within PAD_3DIGIT_CODE_NETWORKS
        if (outlet1.distributor in PAD_3DIGIT_CODE_NETWORKS or outlet2.distributor in PAD_3DIGIT_CODE_NETWORKS):
            if c1.isdigit() and len(c1) in (1, 2):
                c1 = c1.zfill(3)
            if c2.isdigit() and len(c2) in (1, 2):
                c2 = c2.zfill(3)
        if c1 and c2 and c1 == c2:
            return 100.0, True
        return 0.0, False

    # 2. HARD RULE for other networks: If both outlets have store codes and they CONFLICT, they are different!
    if outlet1.store_code and outlet2.store_code and outlet1.store_code != outlet2.store_code:
        return 0.0, False

    # 2. Geographic checks: outlets must be at the same physical location
    # 2a. House check: If both outlets have explicit house numbers (neither is "б/н"),
    # different house numbers can NEVER merge!
    has_num1 = bool(outlet1.base_house and outlet1.base_house != "б/н")
    has_num2 = bool(outlet2.base_house and outlet2.base_house != "б/н")

    if has_num1 and has_num2 and outlet1.base_house != outlet2.base_house:
        return 0.0, False

    # 2b. Street check: must have at least one overlapping street token or high fuzzy match
    s_set1 = set(outlet1.street_tokens)
    s_set2 = set(outlet2.street_tokens)
    street_overlap = bool(s_set1 and s_set2 and (s_set1 & s_set2))

    street_str1 = ' '.join(outlet1.street_tokens)
    street_str2 = ' '.join(outlet2.street_tokens)
    street_fuzzy = fuzz.token_sort_ratio(street_str1, street_str2) if (street_str1 and street_str2) else 0

    if not street_overlap and street_fuzzy < 70:
        return 0.0, False

    # 2c. City check: if both cities are identified, they must not conflict
    if outlet1.city and outlet2.city:
        c_set1 = set(outlet1.city.split())
        c_set2 = set(outlet2.city.split())
        city_overlap = bool(c_set1 & c_set2)
        city_fuzzy = fuzz.token_sort_ratio(outlet1.city, outlet2.city)
        if not city_overlap and city_fuzzy < 65:
            return 0.0, False

    # 3. Store name and code checks
    name1 = outlet1.clean_name
    name2 = outlet2.clean_name

    code_match = (
        bool(outlet1.store_code) and
        bool(outlet2.store_code) and
        (outlet1.store_code == outlet2.store_code)
    )

    token_set = fuzz.token_set_ratio(name1, name2) if (name1 and name2) else 0.0
    token_sort = fuzz.token_sort_ratio(name1, name2) if (name1 and name2) else 0.0
    name_score = max(token_set, token_sort)

    if code_match:
        score = 100.0
    else:
        score = name_score

    # 4. Determine whether it is an exact (identical) or similar match:
    is_national = outlet1.is_national or outlet2.is_national
    house_match = (outlet1.full_house == outlet2.full_house)

    if is_national:
        # For national networks: code match or high name match (>=90) -> exact
        is_exact = (code_match or name_score >= 90)
    else:
        # For regular distributors:
        # Even if store code matches, if the legal entity / brand name differs
        # (e.g. "Люкс" vs "Перминов В.В ИП"), it must be marked as "Похожая".
        # Exact match requires name similarity >= 95 and same full house.
        is_exact = (name_score >= NAME_EXACT_THRESHOLD) and house_match

    return score, is_exact


class OutletsDeduplicator:
    """Executes the deduplication and grouping workflow."""

    def __init__(self, records: List[OutletRecord]):
        self.records = records
        self.master_records: List[OutletRecord] = []
        self.distrib_records: List[OutletRecord] = []

        for r in records:
            if r.is_vendor == 1:
                self.master_records.append(r)
            else:
                self.distrib_records.append(r)

    def run(self, include_similarity: bool = False) -> List[Tuple[Any, ...]]:
        """
        Runs the full deduplication pipeline.
        Returns a list of output tuples:
          - If include_similarity is False: (Итоговый ID, Статус, raw_row)
          - If include_similarity is True: (Итоговый ID, Статус, raw_row, Similarity_Score)
        """
        # Step 1: Index master records (IsVendor = 1)
        master_index = defaultdict(list)
        for m_idx, m_rec in enumerate(self.master_records):
            for key in m_rec.blocking_keys:
                master_index[key].append(m_idx)

        # Step 2: Match distributor records against master records
        # master_matches: maps master_record index -> list of (distrib_record, status, score)
        master_matches: Dict[int, List[Tuple[OutletRecord, str, float]]] = defaultdict(list)
        unmatched_distrib: List[OutletRecord] = []

        for d_rec in self.distrib_records:
            best_master_idx: Optional[int] = None
            best_score = 0.0
            best_status = ""

            # Retrieve candidate master records
            candidates = set()
            for key in d_rec.blocking_keys:
                if key in master_index:
                    candidates.update(master_index[key])

            for m_idx in candidates:
                m_rec = self.master_records[m_idx]
                score, is_exact = calculate_outlet_match_score(d_rec, m_rec)

                if score >= NAME_SIMILAR_THRESHOLD and score > best_score:
                    best_score = score
                    best_master_idx = m_idx
                    best_status = STATUS_IDENTICAL if is_exact else STATUS_SIMILAR

            if best_master_idx is not None:
                master_matches[best_master_idx].append((d_rec, best_status, best_score))
            else:
                unmatched_distrib.append(d_rec)

        # Step 3: Match remaining distributor records among themselves
        dist_index = defaultdict(list)
        for u_idx, d_rec in enumerate(unmatched_distrib):
            for key in d_rec.blocking_keys:
                dist_index[key].append(u_idx)

        dist_groups: List[List[Tuple[OutletRecord, str, float]]] = []
        visited_dist_indices = set()

        for u_idx, d_rec in enumerate(unmatched_distrib):
            if u_idx in visited_dist_indices:
                continue

            visited_dist_indices.add(u_idx)
            current_group: List[Tuple[OutletRecord, str, float]] = []

            # Find candidates
            candidates = set()
            for key in d_rec.blocking_keys:
                if key in dist_index:
                    for cand_idx in dist_index[key]:
                        if cand_idx not in visited_dist_indices:
                            candidates.add(cand_idx)

            matched_cands: List[Tuple[OutletRecord, str, float]] = []
            for cand_idx in candidates:
                cand_rec = unmatched_distrib[cand_idx]

                # Constraint: National networks only match within the SAME distributor
                if d_rec.is_national:
                    if cand_rec.distributor != d_rec.distributor:
                        continue
                else:
                    # Regular distributors can match with other regular distributors,
                    # but never with national networks
                    if cand_rec.is_national:
                        continue

                score, is_exact = calculate_outlet_match_score(d_rec, cand_rec)
                if score >= NAME_SIMILAR_THRESHOLD:
                    visited_dist_indices.add(cand_idx)
                    cand_status = STATUS_IDENTICAL if is_exact else STATUS_SIMILAR
                    matched_cands.append((cand_rec, cand_status, score))

            if matched_cands:
                has_ident = any(s == STATUS_IDENTICAL for _, s, _ in matched_cands)
                main_status = STATUS_IDENTICAL if has_ident else STATUS_SIMILAR
                current_group.append((d_rec, main_status, 100.0))
                current_group.extend(matched_cands)
                dist_groups.append(current_group)
            else:
                current_group.append((d_rec, STATUS_UNIQUE, 0.0))
                dist_groups.append(current_group)

        # Step 4: Build final ordered output list
        output_rows: List[Tuple[Any, ...]] = []
        current_final_id = 1

        # 4a: Master groups that have at least one distributor match
        # (Master records with no distributor matches are EXCLUDED per requirements)
        for m_idx, d_matches in master_matches.items():
            m_rec = self.master_records[m_idx]

            # Master outlet status: "Одинаковая" if at least one distributor point matches identically,
            # otherwise "Похожая"
            has_identical = any(status == STATUS_IDENTICAL for _, status, _ in d_matches)
            master_status = STATUS_IDENTICAL if has_identical else STATUS_SIMILAR

            # Master outlet first
            if include_similarity:
                output_rows.append((current_final_id, master_status, m_rec.raw_row, 100.0))
                for d_rec, dist_status, dist_score in d_matches:
                    output_rows.append((current_final_id, dist_status, d_rec.raw_row, dist_score))
            else:
                output_rows.append((current_final_id, master_status, m_rec.raw_row))
                for d_rec, dist_status, _ in d_matches:
                    output_rows.append((current_final_id, dist_status, d_rec.raw_row))

            current_final_id += 1

        # 4b: Distributor-only groups (both multi-record and unique)
        for d_group in dist_groups:
            for item in d_group:
                d_rec = item[0]
                dist_status = item[1]
                dist_score = item[2]
                if include_similarity:
                    output_rows.append((current_final_id, dist_status, d_rec.raw_row, dist_score))
                else:
                    output_rows.append((current_final_id, dist_status, d_rec.raw_row))
            current_final_id += 1

        return output_rows
