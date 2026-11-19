"""
DataFix - Transparent Data Quality Scoring Engine
Computes 0-100 multidimensional quality scores across Completeness, Uniqueness, Validity,
Consistency, and Integrity, explaining the exact mathematical derivation.
"""

from typing import Dict, Any, List
import pandas as pd
from config import QUALITY_SCORE_WEIGHTS, CATEGORY_MISSING, CATEGORY_EXACT_DUPLICATES, CATEGORY_INVALID_FORMAT, CATEGORY_INCONSISTENT_CAT, CATEGORY_WHITESPACE_CASING, CATEGORY_OUTLIER, CATEGORY_CROSS_COLUMN, CATEGORY_DATE_NUMERIC, CATEGORY_DATA_TYPE


def compute_quality_score(df: pd.DataFrame, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes transparent multi-dimensional 0-100 data quality score.
    Returns composite score, dimensional breakdown, and mathematical explanation.
    """
    if df is None or df.empty:
        return {
            "overall_score": 0.0,
            "dimensions": {},
            "formula_explanation": "Dataset is empty; score is undefined."
        }
        
    total_rows = max(len(df), 1)
    total_cols = max(len(df.columns), 1)
    total_cells = total_rows * total_cols
    
    # Aggregate defect counts per dimension from detected issues
    category_counts = {}
    for iss in issues:
        cat = iss.get("category", "")
        category_counts[cat] = category_counts.get(cat, 0) + iss.get("count", 0)

    # 1. Completeness: Penalty for missing/null cells
    missing_cells = category_counts.get(CATEGORY_MISSING, 0)
    completeness_score = max(0.0, min(100.0, (1.0 - (missing_cells / total_cells)) * 100.0))

    # 2. Uniqueness: Penalty for duplicate rows
    dup_rows = category_counts.get(CATEGORY_EXACT_DUPLICATES, 0)
    uniqueness_score = max(0.0, min(100.0, (1.0 - (dup_rows / total_rows)) * 100.0))

    # 3. Validity: Penalty for syntax/format/range errors (emails, phones, dates, numbers)
    validity_defects = (
        category_counts.get(CATEGORY_INVALID_FORMAT, 0) +
        category_counts.get(CATEGORY_DATE_NUMERIC, 0)
    )
    validity_score = max(0.0, min(100.0, (1.0 - (validity_defects / total_cells)) * 100.0))

    # 4. Consistency: Penalty for whitespace, casing, and category drift
    consistency_defects = (
        category_counts.get(CATEGORY_WHITESPACE_CASING, 0) +
        category_counts.get(CATEGORY_INCONSISTENT_CAT, 0)
    )
    consistency_score = max(0.0, min(100.0, (1.0 - (consistency_defects / total_cells)) * 100.0))

    # 5. Integrity: Penalty for cross-column logic violations, type glitches, and outliers
    integrity_defects = (
        category_counts.get(CATEGORY_CROSS_COLUMN, 0) +
        category_counts.get(CATEGORY_DATA_TYPE, 0) +
        category_counts.get(CATEGORY_OUTLIER, 0)
    )
    integrity_score = max(0.0, min(100.0, (1.0 - (integrity_defects / total_cells)) * 100.0))

    # Weighted Overall Score
    w = QUALITY_SCORE_WEIGHTS
    overall_score = (
        w["completeness"] * completeness_score +
        w["validity"] * validity_score +
        w["consistency"] * consistency_score +
        w["uniqueness"] * uniqueness_score +
        w["integrity"] * integrity_score
    )
    overall_score = round(max(0.0, min(100.0, overall_score)), 1)

    dimensions = {
        "Completeness": {
            "score": round(completeness_score, 1),
            "weight": f"{int(w['completeness']*100)}%",
            "defect_count": missing_cells,
            "description": "Measures absence of null, NaN, or whitespace-only blank cells."
        },
        "Validity": {
            "score": round(validity_score, 1),
            "weight": f"{int(w['validity']*100)}%",
            "defect_count": validity_defects,
            "description": "Conformity to expected domain formats (RFC emails, dates, positive ranges)."
        },
        "Consistency": {
            "score": round(consistency_score, 1),
            "weight": f"{int(w['consistency']*100)}%",
            "defect_count": consistency_defects,
            "description": "Standardization of casing, whitespace padding, and canonical categories."
        },
        "Uniqueness": {
            "score": round(uniqueness_score, 1),
            "weight": f"{int(w['uniqueness']*100)}%",
            "defect_count": dup_rows,
            "description": "Absence of redundant duplicate entity records."
        },
        "Integrity": {
            "score": round(integrity_score, 1),
            "weight": f"{int(w['integrity']*100)}%",
            "defect_count": integrity_defects,
            "description": "Mathematical cross-column agreement, type purity, and statistical reasonableness."
        }
    }

    formula_explanation = (
        f"Score = ({w['completeness']} × Completeness) + ({w['validity']} × Validity) + "
        f"({w['consistency']} × Consistency) + ({w['uniqueness']} × Uniqueness) + ({w['integrity']} × Integrity). "
        "Notice: A high statistical score reflects syntactic and structural cleanliness, but does not substitute for ground-truth domain verification."
    )

    return {
        "overall_score": overall_score,
        "dimensions": dimensions,
        "formula_explanation": formula_explanation,
        "total_cells": total_cells,
        "total_rows": total_rows
    }
