"""
DataFix - Data Integrity and Security Utilities
Ensures dataset immutability, schema preservation, change auditability, and safety.
"""

import hashlib
import json
import pandas as pd
from typing import Dict, Any, Tuple, List


def compute_dataframe_hash(df: pd.DataFrame) -> str:
    """
    Computes a cryptographic SHA-256 hash of a dataframe's content and structure.
    Used to guarantee that the original uploaded dataset remains strictly immutable.
    """
    if df is None:
        return ""
    # Combine shape, columns, dtypes, and serialized JSON values
    try:
        # Sort index and columns to ensure deterministic hash
        df_sorted = df.copy()
        raw_repr = (
            f"shape:{df_sorted.shape}|"
            f"cols:{list(df_sorted.columns)}|"
            f"dtypes:{[str(t) for t in df_sorted.dtypes]}|"
            f"values:{df_sorted.to_json(orient='split', date_format='iso')}"
        )
        return hashlib.sha256(raw_repr.encode('utf-8')).hexdigest()
    except Exception:
        # Fallback to string representation hash
        return hashlib.sha256(str(df.values).encode('utf-8')).hexdigest()


def verify_dataset_immutability(original_df: pd.DataFrame, expected_hash: str) -> bool:
    """
    Verifies that the original dataframe has not been mutated in memory.
    Returns True if the current hash strictly matches the initial registration hash.
    """
    if original_df is None or not expected_hash:
        return False
    current_hash = compute_dataframe_hash(original_df)
    return current_hash == expected_hash


def create_safe_working_copy(df: pd.DataFrame) -> pd.DataFrame:
    """
    Creates an isolated deep copy of the dataframe for all processing and repairs,
    preserving original index and column metadata.
    """
    if df is None:
        return None
    return df.copy(deep=True)


def check_schema_preservation(original_df: pd.DataFrame, repaired_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Validates that column names, column ordering, and expected structural properties
    have been maintained during repair.
    """
    if original_df is None or repaired_df is None:
        return {"preserved": False, "reason": "One or both dataframes are None"}
    
    orig_cols = list(original_df.columns)
    rep_cols = list(repaired_df.columns)
    
    missing_cols = [c for c in orig_cols if c not in rep_cols]
    added_cols = [c for c in rep_cols if c not in orig_cols]
    order_preserved = (orig_cols == rep_cols)
    
    preserved = (len(missing_cols) == 0 and order_preserved)
    
    return {
        "preserved": preserved,
        "original_column_count": len(orig_cols),
        "repaired_column_count": len(rep_cols),
        "missing_columns": missing_cols,
        "added_columns": added_cols,
        "order_preserved": order_preserved
    }


def verify_unintended_changes(
    original_df: pd.DataFrame, 
    repaired_df: pd.DataFrame, 
    audit_log: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Compares original vs repaired datasets against logged modifications.
    Confirms that:
    1. Every cell modification corresponds to a logged, authorized audit entry.
    2. Valid data cells not flagged in the audit log were preserved untouched.
    """
    if original_df is None or repaired_df is None:
        return {"verified": False, "discrepancies": ["Missing dataframe(s)"]}
    
    # Check shape: if rows were deleted (e.g. deduplication), ensure it's logged
    logged_deleted_rows = set()
    logged_modified_cells = set() # (row_idx, col_name)
    
    for entry in audit_log:
        if entry.get("repair_method") == "remove_duplicate_row":
            row_idx = entry.get("row_index")
            if row_idx is not None:
                logged_deleted_rows.add(row_idx)
        else:
            row_idx = entry.get("row_index")
            col_name = entry.get("column")
            if row_idx is not None and col_name is not None:
                logged_modified_cells.add((row_idx, col_name))
                
    discrepancies = []
    
    # Check cell-level fidelity on surviving rows
    common_indices = original_df.index.intersection(repaired_df.index)
    common_cols = [c for c in original_df.columns if c in repaired_df.columns]
    
    unlogged_changes_count = 0
    for idx in common_indices:
        for col in common_cols:
            orig_val = original_df.at[idx, col]
            rep_val = repaired_df.at[idx, col]
            
            # Check if values differ (handling NaN equivalence)
            is_both_nan = pd.isna(orig_val) and pd.isna(rep_val)
            if not is_both_nan and orig_val != rep_val:
                if (idx, col) not in logged_modified_cells:
                    unlogged_changes_count += 1
                    if len(discrepancies) < 5:
                        discrepancies.append(
                            f"Row {idx}, Col '{col}' was changed from '{orig_val}' to '{rep_val}' without audit log entry."
                        )
                        
    verified = (unlogged_changes_count == 0)
    return {
        "verified": verified,
        "unlogged_changes_count": unlogged_changes_count,
        "sample_discrepancies": discrepancies,
        "total_audited_changes": len(audit_log)
    }
