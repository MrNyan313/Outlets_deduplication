"""Outlets Deduplication Engine."""

from collections import defaultdict
from typing import List, Dict, Any, Tuple, Optional
from rapidfuzz import fuzz

from config import (
    NATIONAL_NETWORKS,
    STATUS_IDENTICAL,
    STATUS_SIMILAR,
    STATUS_UNIQUE,
    NAME_EXACT_THRESHOLD,
    NAME_SIMILAR_THRESHOLD,
)
from normalizer import (
    extract_address_details,
    get_address_blocking_keys,
    extract_store_code,
    clean_store_name,
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

        # Pre-extracted features
        base_h, full_h, city, street_tokens = extract_address_details(self.address)
        self.base_house = base_h
        self.full_house = full_h
        self.city = city
        self.street_tokens = street_tokens

        self.store_code = extract_store_code(self.name)
        self.clean_name = clean_store_name(self.name)
        self.blocking_keys = get_address_blocking_keys(self.address)


def calculate_outlet_match_score(
    outlet1: OutletRecord,
    outlet2: OutletRecord
) -> Tuple[float, bool]:
    """
    Calculates similarity between two outlets at the same address.
    Returns: (score, is_exact_match)
    """
    # Hard rule: base house numbers MUST match
    if not outlet1.base_house or not outlet2.base_house or outlet1.base_house != outlet2.base_house:
        return 0.0, False

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

    # Determine whether it is an exact (identical) or similar match:
    is_national = outlet1.is_national or outlet2.is_national
    house_match = (outlet1.full_house == outlet2.full_house)

    if is_national:
        # For national networks: code match or high name match (>=90) at same address -> exact
        is_exact = (code_match or name_score >= 90) and house_match
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

    def run(self) -> List[Tuple[int, str, tuple]]:
        """
        Runs the full deduplication pipeline.
        Returns a list of output tuples: (Итоговый ID, Статус, raw_row)
        """
        # Step 1: Index master records (IsVendor = 1)
        master_index = defaultdict(list)
        for m_idx, m_rec in enumerate(self.master_records):
            for key in m_rec.blocking_keys:
                master_index[key].append(m_idx)

        # Step 2: Match distributor records against master records
        # master_matches: maps master_record index -> list of (distrib_record, status)
        master_matches: Dict[int, List[Tuple[OutletRecord, str]]] = defaultdict(list)
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
                master_matches[best_master_idx].append((d_rec, best_status))
            else:
                unmatched_distrib.append(d_rec)

        # Step 3: Match remaining distributor records among themselves
        dist_index = defaultdict(list)
        for u_idx, d_rec in enumerate(unmatched_distrib):
            for key in d_rec.blocking_keys:
                dist_index[key].append(u_idx)

        dist_groups: List[List[Tuple[OutletRecord, str]]] = []
        visited_dist_indices = set()

        for u_idx, d_rec in enumerate(unmatched_distrib):
            if u_idx in visited_dist_indices:
                continue

            visited_dist_indices.add(u_idx)
            current_group: List[Tuple[OutletRecord, str]] = []

            # Find candidates
            candidates = set()
            for key in d_rec.blocking_keys:
                if key in dist_index:
                    for cand_idx in dist_index[key]:
                        if cand_idx not in visited_dist_indices:
                            candidates.add(cand_idx)

            matched_cands: List[Tuple[OutletRecord, str]] = []
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
                    matched_cands.append((cand_rec, cand_status))

            if matched_cands:
                has_ident = any(s == STATUS_IDENTICAL for _, s in matched_cands)
                main_status = STATUS_IDENTICAL if has_ident else STATUS_SIMILAR
                current_group.append((d_rec, main_status))
                current_group.extend(matched_cands)
                dist_groups.append(current_group)
            else:
                current_group.append((d_rec, STATUS_UNIQUE))
                dist_groups.append(current_group)

        # Step 4: Build final ordered output list
        output_rows: List[Tuple[int, str, tuple]] = []
        current_final_id = 1

        # 4a: Master groups that have at least one distributor match
        # (Master records with no distributor matches are EXCLUDED per requirements)
        for m_idx, d_matches in master_matches.items():
            m_rec = self.master_records[m_idx]

            # Master outlet status: "Одинаковая" if at least one distributor point matches identically,
            # otherwise "Похожая"
            has_identical = any(status == STATUS_IDENTICAL for _, status in d_matches)
            master_status = STATUS_IDENTICAL if has_identical else STATUS_SIMILAR

            # Master outlet first
            output_rows.append((current_final_id, master_status, m_rec.raw_row))

            # Matched distributor outlets with their individual statuses
            for d_rec, dist_status in d_matches:
                output_rows.append((current_final_id, dist_status, d_rec.raw_row))

            current_final_id += 1

        # 4b: Distributor-only groups (both multi-record and unique)
        for d_group in dist_groups:
            for d_rec, dist_status in d_group:
                output_rows.append((current_final_id, dist_status, d_rec.raw_row))
            current_final_id += 1

        return output_rows
