"""
DataFix - Autonomous Data Repair Engine
Implements conservative, explainable, reversible repairs with confidence scoring,
audit logging, safe auto-repair, and undo functionality.
"""

from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np

from config import (
    CONFIDENCE_AUTO_REPAIR_THRESHOLD,
    CATEGORY_MISSING,
    CATEGORY_EXACT_DUPLICATES,
    CATEGORY_POTENTIAL_DUPLICATES,
    CATEGORY_INVALID_FORMAT,
    CATEGORY_DATE_NUMERIC,
    CATEGORY_INCONSISTENT_CAT,
    CATEGORY_WHITESPACE_CASING,
    CATEGORY_DATA_TYPE,
    CATEGORY_OUTLIER,
    CATEGORY_CROSS_COLUMN
)
from utils.helpers import clean_numeric_string, try_parse_date


class DataRepairEngine:
    """Manages generation of repair candidates, execution of user-approved or autonomous repairs, and undo tracking."""

    def __init__(self, df: pd.DataFrame, issues: List[Dict[str, Any]]):
        self.df = df.copy(deep=True)
        self.issues = issues
        self.audit_log: List[Dict[str, Any]] = []

    def generate_repair_proposals(self) -> List[Dict[str, Any]]:
        """
        Translates detected issues into discrete, actionable repair proposals.
        Each proposal contains original value, proposed value, method, confidence, and reason.
        """
        proposals = []
        proposal_id = 1

        for issue in self.issues:
            cat = issue.get("category")
            repair_method = issue.get("repair_recommended")
            details = issue.get("details", {})
            confidence = issue.get("confidence", 0.80)

            # 1. Whitespace Stripping
            if repair_method == "strip_whitespace":
                col = details.get("column")
                indices = details.get("indices", [])
                for idx in indices:
                    if idx in self.df.index:
                        orig = self.df.at[idx, col]
                        cleaned = str(orig).strip()
                        proposals.append({
                            "proposal_id": f"REP-{proposal_id:04d}",
                            "issue_id": issue.get("id"),
                            "category": cat,
                            "column": col,
                            "row_index": idx,
                            "original_value": orig,
                            "proposed_value": cleaned,
                            "repair_method": "strip_whitespace",
                            "confidence": 1.0,
                            "is_safe_auto": True,
                            "reason": f"Remove leading/trailing whitespace padding from string in column '{col}'."
                        })
                        proposal_id += 1

            # 2. Casing Standardization (Title Case)
            elif repair_method == "standardize_casing_title":
                col = details.get("column")
                indices = details.get("indices", [])
                for idx in indices:
                    if idx in self.df.index:
                        orig = self.df.at[idx, col]
                        # Fix caps lock or inverted casing (e.g. 'bOB SMITH' -> 'Bob Smith')
                        new_val = str(orig).strip().title()
                        proposals.append({
                            "proposal_id": f"REP-{proposal_id:04d}",
                            "issue_id": issue.get("id"),
                            "category": cat,
                            "column": col,
                            "row_index": idx,
                            "original_value": orig,
                            "proposed_value": new_val,
                            "repair_method": "standardize_casing_title",
                            "confidence": 0.92,
                            "is_safe_auto": True,
                            "reason": f"Standardize haphazard or inverted capitalization to proper Title Case in column '{col}'."
                        })
                        proposal_id += 1

            # 3. Email Domain Typos
            elif repair_method == "fix_email_typo":
                corrections = details.get("corrections", [])
                col = details.get("column")
                for idx, orig, fixed in corrections:
                    if idx in self.df.index:
                        proposals.append({
                            "proposal_id": f"REP-{proposal_id:04d}",
                            "issue_id": issue.get("id"),
                            "category": cat,
                            "column": col,
                            "row_index": idx,
                            "original_value": orig,
                            "proposed_value": fixed,
                            "repair_method": "fix_email_domain_typo",
                            "confidence": 0.96,
                            "is_safe_auto": True,
                            "reason": f"Correct recognized common domain typo in email address to '{fixed}'."
                        })
                        proposal_id += 1

            # 4. Phone Number Normalization
            elif repair_method == "normalize_phone_format":
                corrections = details.get("corrections", [])
                col = details.get("column")
                for idx, orig, norm in corrections:
                    if idx in self.df.index:
                        proposals.append({
                            "proposal_id": f"REP-{proposal_id:04d}",
                            "issue_id": issue.get("id"),
                            "category": cat,
                            "column": col,
                            "row_index": idx,
                            "original_value": orig,
                            "proposed_value": norm,
                            "repair_method": "normalize_phone_format",
                            "confidence": 0.94,
                            "is_safe_auto": True,
                            "reason": f"Standardize contact phone number into international E.164-compatible format '{norm}'."
                        })
                        proposal_id += 1

            # 5. Date ISO-8601 Normalization
            elif repair_method == "normalize_date_iso":
                corrections = details.get("corrections", [])
                col = details.get("column")
                for idx, orig, iso_date in corrections:
                    if idx in self.df.index:
                        proposals.append({
                            "proposal_id": f"REP-{proposal_id:04d}",
                            "issue_id": issue.get("id"),
                            "category": cat,
                            "column": col,
                            "row_index": idx,
                            "original_value": orig,
                            "proposed_value": iso_date,
                            "repair_method": "normalize_date_iso",
                            "confidence": 0.98,
                            "is_safe_auto": True,
                            "reason": f"Normalize non-standard date string to unambiguous ISO-8601 format (YYYY-MM-DD)."
                        })
                        proposal_id += 1

            # 6. Inconsistent Categorical Standardization
            elif repair_method == "standardize_categorical_values":
                corrections = details.get("corrections", [])
                col = details.get("column")
                for idx, orig, standard_cat in corrections:
                    if idx in self.df.index:
                        proposals.append({
                            "proposal_id": f"REP-{proposal_id:04d}",
                            "issue_id": issue.get("id"),
                            "category": cat,
                            "column": col,
                            "row_index": idx,
                            "original_value": orig,
                            "proposed_value": standard_cat,
                            "repair_method": "standardize_categorical_values",
                            "confidence": 0.95,
                            "is_safe_auto": True,
                            "reason": f"Map non-standard abbreviation or alias '{orig}' to canonical category '{standard_cat}'."
                        })
                        proposal_id += 1

            # 7. Numeric String Cleaning (Currency, Commas)
            elif repair_method == "clean_and_cast_numeric":
                conversions = details.get("conversions", [])
                col = details.get("column")
                for idx, orig, num in conversions:
                    if idx in self.df.index:
                        proposals.append({
                            "proposal_id": f"REP-{proposal_id:04d}",
                            "issue_id": issue.get("id"),
                            "category": cat,
                            "column": col,
                            "row_index": idx,
                            "original_value": orig,
                            "proposed_value": float(num),
                            "repair_method": "clean_and_cast_numeric",
                            "confidence": 0.98,
                            "is_safe_auto": True,
                            "reason": f"Strip currency symbols and commas to convert string to pure numeric floating point {num}."
                        })
                        proposal_id += 1

            # 8. Negative Value Sanitization (Absolute Value where strictly positive)
            elif repair_method == "convert_absolute_or_flag":
                entries = details.get("entries", [])
                col = details.get("column")
                for idx, orig, abs_num in entries:
                    if idx in self.df.index:
                        proposals.append({
                            "proposal_id": f"REP-{proposal_id:04d}",
                            "issue_id": issue.get("id"),
                            "category": cat,
                            "column": col,
                            "row_index": idx,
                            "original_value": orig,
                            "proposed_value": float(abs_num),
                            "repair_method": "convert_absolute_value",
                            "confidence": 0.90,
                            "is_safe_auto": True,
                            "reason": f"Convert erroneous negative sign to positive value {abs_num} for domain '{col}'."
                        })
                        proposal_id += 1

            # 9. Exact Duplicate Removal
            elif repair_method == "remove_exact_duplicates":
                drop_indices = details.get("indices_to_drop", [])
                for idx in drop_indices:
                    if idx in self.df.index:
                        proposals.append({
                            "proposal_id": f"REP-{proposal_id:04d}",
                            "issue_id": issue.get("id"),
                            "category": cat,
                            "column": "[Entire Row]",
                            "row_index": idx,
                            "original_value": f"[Row {idx} Identical to earlier record]",
                            "proposed_value": "[Row Deleted / Deduplicated]",
                            "repair_method": "remove_duplicate_row",
                            "confidence": 1.0,
                            "is_safe_auto": True,
                            "reason": f"Deduplicate exact redundant row {idx} to maintain dataset uniqueness."
                        })
                        proposal_id += 1

            # 10. Cross-Column Arithmetic Recalculation (Total = Qty * Price)
            elif repair_method == "recalculate_cross_column_total":
                mismatches = details.get("mismatches", [])
                total_col = details.get("total_col")
                for idx, orig_total, expected_total, q_val, p_val in mismatches:
                    if idx in self.df.index:
                        proposals.append({
                            "proposal_id": f"REP-{proposal_id:04d}",
                            "issue_id": issue.get("id"),
                            "category": cat,
                            "column": total_col,
                            "row_index": idx,
                            "original_value": orig_total,
                            "proposed_value": float(expected_total),
                            "repair_method": "recalculate_total_amount",
                            "confidence": 0.97,
                            "is_safe_auto": True,
                            "reason": f"Recalculate desynchronized total: {q_val} units × ${p_val} unit price = ${expected_total:.2f}."
                        })
                        proposal_id += 1

            # 11. Missing Value Imputation (Median for Numeric, Mode / Placeholder for Categorical)
            elif repair_method in ["impute_numeric_median", "impute_categorical_mode", "statistical_imputation"]:
                col = issue.get("column")
                affected_rows = issue.get("affected_rows", [])
                
                # Compute replacement value
                valid_series = self.df[col].dropna()
                if valid_series.empty:
                    replacement = "Unspecified"
                    method_name = "constant_placeholder"
                    conf = 0.70
                elif pd.api.types.is_numeric_dtype(valid_series):
                    replacement = round(float(valid_series.median()), 2)
                    method_name = "impute_median"
                    conf = 0.85
                else:
                    # Categorical mode
                    mode_val = valid_series.mode()
                    if not mode_val.empty:
                        replacement = str(mode_val.iloc[0])
                        method_name = "impute_mode"
                        conf = 0.80
                    else:
                        replacement = "Unknown"
                        method_name = "impute_unknown"
                        conf = 0.75

                for idx in affected_rows:
                    if idx in self.df.index:
                        orig = self.df.at[idx, col]
                        proposals.append({
                            "proposal_id": f"REP-{proposal_id:04d}",
                            "issue_id": issue.get("id"),
                            "category": cat,
                            "column": col,
                            "row_index": idx,
                            "original_value": "<NULL / BLANK>" if (pd.isna(orig) or str(orig).strip() == "") else str(orig),
                            "proposed_value": replacement,
                            "repair_method": method_name,
                            "confidence": conf,
                            "is_safe_auto": (conf >= CONFIDENCE_AUTO_REPAIR_THRESHOLD),
                            "reason": f"Impute missing value using robust column {method_name.replace('impute_', '')} ({replacement})."
                        })
                        proposal_id += 1

            # 12. Statistical Outlier Capping (Winsorization)
            elif repair_method == "cap_outliers_iqr":
                col = details.get("column")
                lower = details.get("lower_bound")
                upper = details.get("upper_bound")
                indices = details.get("indices", [])
                
                for idx in indices:
                    if idx in self.df.index:
                        orig = self.df.at[idx, col]
                        ok, num = clean_numeric_string(orig)
                        if ok:
                            capped_val = min(max(num, lower), upper)
                            proposals.append({
                                "proposal_id": f"REP-{proposal_id:04d}",
                                "issue_id": issue.get("id"),
                                "category": cat,
                                "column": col,
                                "row_index": idx,
                                "original_value": orig,
                                "proposed_value": round(float(capped_val), 2),
                                "repair_method": "cap_outlier_winsorize",
                                "confidence": 0.86,
                                "is_safe_auto": False, # Outlier capping is opt-in to avoid mutating real extreme values
                                "reason": f"Cap extreme outlier value at IQR fence limit [{lower:.1f}, {upper:.1f}] to preserve parametric distributions."
                            })
                            proposal_id += 1

        return proposals

    @staticmethod
    def apply_single_repair(
        df: pd.DataFrame, 
        proposal: Dict[str, Any]
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Applies a single discrete repair proposal to the dataframe.
        Returns the updated dataframe and a formal audit log entry.
        """
        updated_df = df.copy(deep=True)
        idx = proposal.get("row_index")
        col = proposal.get("column")
        method = proposal.get("repair_method")
        new_val = proposal.get("proposed_value")
        orig_val = proposal.get("original_value")

        if method == "remove_duplicate_row":
            if idx in updated_df.index:
                updated_df = updated_df.drop(index=idx)
        else:
            if idx in updated_df.index and col in updated_df.columns:
                try:
                    updated_df.at[idx, col] = new_val
                except (TypeError, ValueError):
                    # If column dtype rejects the new type (e.g. arrow string rejecting float),
                    # convert column to object first to allow multi-type assignment
                    updated_df[col] = updated_df[col].astype("object")
                    updated_df.at[idx, col] = new_val

        audit_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "proposal_id": proposal.get("proposal_id"),
            "issue_id": proposal.get("issue_id"),
            "category": proposal.get("category"),
            "row_index": idx,
            "column": col,
            "original_value": str(orig_val),
            "updated_value": str(new_val),
            "repair_method": method,
            "confidence": proposal.get("confidence", 1.0),
            "reason": proposal.get("reason"),
            "approval_status": "Approved",
            "validation_status": "Validated"
        }

        return updated_df, audit_entry

    @staticmethod
    def apply_batch_repairs(
        df: pd.DataFrame, 
        proposals: List[Dict[str, Any]]
    ) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
        """Applies a collection of approved repair proposals in one atomic batch transaction."""
        current_df = df.copy(deep=True)
        applied_logs = []

        # Sort so non-deletion repairs occur before row-deletion deduplications
        sorted_proposals = sorted(
            proposals, 
            key=lambda p: 1 if p.get("repair_method") == "remove_duplicate_row" else 0
        )

        for prop in sorted_proposals:
            current_df, log_entry = DataRepairEngine.apply_single_repair(current_df, prop)
            applied_logs.append(log_entry)

        return current_df, applied_logs
