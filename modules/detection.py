"""
DataFix - Automated Data Quality Detection Engine
Identifies missing values, exact and fuzzy duplicates, invalid formats, numeric/date anomalies,
whitespace/casing glitches, statistical outliers, and cross-column logic violations.
"""

import re
from datetime import datetime
from typing import List, Dict, Any, Tuple
import pandas as pd
import numpy as np

from config import (
    CATEGORY_MISSING,
    CATEGORY_EXACT_DUPLICATES,
    CATEGORY_POTENTIAL_DUPLICATES,
    CATEGORY_INVALID_FORMAT,
    CATEGORY_DATE_NUMERIC,
    CATEGORY_INCONSISTENT_CAT,
    CATEGORY_WHITESPACE_CASING,
    CATEGORY_DATA_TYPE,
    CATEGORY_OUTLIER,
    CATEGORY_CROSS_COLUMN,
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_MEDIUM,
    SEVERITY_LOW,
    MAX_ROWS_PAIRWISE_FUZZY
)
from utils.helpers import (
    calculate_similarity,
    is_valid_email,
    fix_email_domain_typo,
    is_valid_phone,
    normalize_phone_number,
    try_parse_date,
    clean_numeric_string,
    COMMON_EMAIL_TYPOS
)


class DataQualityDetector:
    """Comprehensive engine for detecting data quality defects across tabular datasets."""
    
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.total_rows = len(df)
        self.columns = list(df.columns)
        self.issues: List[Dict[str, Any]] = []
        self._issue_counter = 1

    def _is_text_column(self, col: str) -> bool:
        """Helper to determine if a column stores text/string/object data across pandas versions."""
        series = self.df[col]
        return not pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_datetime64_any_dtype(series)

    def _next_id(self) -> str:
        issue_id = f"ISSUE-{self._issue_counter:04d}"
        self._issue_counter += 1
        return issue_id

    def detect_all(self) -> List[Dict[str, Any]]:
        """Runs all detection sub-modules in sequence and aggregates discovered issues."""
        self.issues = []
        self._issue_counter = 1
        
        if self.df is None or self.df.empty:
            return self.issues
            
        self._detect_missing_values()
        self._detect_exact_duplicates()
        self._detect_potential_duplicates()
        self._detect_whitespace_and_casing()
        self._detect_invalid_formats()
        self._detect_date_and_numeric_errors()
        self._detect_inconsistent_categories()
        self._detect_unexpected_data_types()
        self._detect_statistical_outliers()
        self._detect_cross_column_inconsistencies()
        
        return self.issues

    def _detect_missing_values(self):
        """Detects null values, NaN, None, and whitespace-only blank cells."""
        for col in self.columns:
            series = self.df[col]
            null_mask = series.isna()
            
            blank_mask = pd.Series(False, index=self.df.index)
            if self._is_text_column(col):
                blank_mask = series.astype(str).str.strip().eq("") & (~null_mask)
                
            combined_mask = null_mask | blank_mask
            affected_indices = self.df.index[combined_mask].tolist()
            count = len(affected_indices)
            
            if count > 0:
                pct = round((count / self.total_rows) * 100, 1)
                severity = SEVERITY_CRITICAL if pct > 30 else (SEVERITY_HIGH if pct > 10 else SEVERITY_MEDIUM)
                
                # Determine recommended repair strategy based on column data
                sample_valid = series.dropna()
                repair_method = "statistical_imputation"
                if pd.api.types.is_numeric_dtype(series):
                    repair_method = "impute_numeric_median"
                else:
                    repair_method = "impute_categorical_mode"
                    
                self.issues.append({
                    "id": self._next_id(),
                    "category": CATEGORY_MISSING,
                    "column": col,
                    "count": count,
                    "affected_rows": affected_indices,
                    "severity": severity,
                    "confidence": 1.0,
                    "evidence": f"Column '{col}' has {count} missing or blank cells ({pct}% of dataset). Rows: {affected_indices[:5]}{'...' if len(affected_indices) > 5 else ''}",
                    "repair_recommended": repair_method,
                    "details": {"col": col, "missing_type": "null_or_blank"}
                })

    def _detect_exact_duplicates(self):
        """Identifies completely identical duplicate rows."""
        dup_mask = self.df.duplicated(keep="first")
        affected_indices = self.df.index[dup_mask].tolist()
        count = len(affected_indices)
        
        if count > 0:
            self.issues.append({
                "id": self._next_id(),
                "category": CATEGORY_EXACT_DUPLICATES,
                "column": "All Columns",
                "count": count,
                "affected_rows": affected_indices,
                "severity": SEVERITY_HIGH,
                "confidence": 1.0,
                "evidence": f"Found {count} exact duplicate rows matching earlier records. Duplicate row indices: {affected_indices}",
                "repair_recommended": "remove_exact_duplicates",
                "details": {"indices_to_drop": affected_indices}
            })

    def _detect_potential_duplicates(self):
        """Identifies fuzzy duplicate records on likely identifier columns (name, email, phone, customer_id)."""
        candidate_cols = [c for c in self.columns if any(k in c.lower() for k in ["name", "email", "phone", "cust", "emp"])]
        if not candidate_cols or self.total_rows > MAX_ROWS_PAIRWISE_FUZZY:
            return
            
        primary_col = candidate_cols[0]
        values = self.df[primary_col].dropna().astype(str).tolist()
        indices = self.df[primary_col].dropna().index.tolist()
        
        found_pairs = []
        seen = set()
        
        for i in range(len(values)):
            for j in range(i + 1, len(values)):
                val_i = values[i].strip()
                val_j = values[j].strip()
                
                # Skip identical values (handled by exact duplicates)
                if val_i.lower() == val_j.lower() or not val_i or not val_j:
                    continue
                    
                score = calculate_similarity(val_i, val_j)
                if score >= 0.85: # High similarity threshold
                    pair_key = tuple(sorted([indices[i], indices[j]]))
                    if pair_key not in seen:
                        seen.add(pair_key)
                        found_pairs.append({
                            "row1": indices[i],
                            "row2": indices[j],
                            "val1": val_i,
                            "val2": val_j,
                            "similarity": round(score, 3)
                        })
                        
        if found_pairs:
            affected_rows = sorted(list(set([p["row1"] for p in found_pairs] + [p["row2"] for p in found_pairs])))
            evidence_samples = [f"Row {p['row1']} ('{p['val1']}') vs Row {p['row2']} ('{p['val2']}') [Similarity: {int(p['similarity']*100)}%]" for p in found_pairs[:3]]
            
            self.issues.append({
                "id": self._next_id(),
                "category": CATEGORY_POTENTIAL_DUPLICATES,
                "column": primary_col,
                "count": len(found_pairs),
                "affected_rows": affected_rows,
                "severity": SEVERITY_MEDIUM,
                "confidence": 0.85,
                "evidence": f"Found {len(found_pairs)} potential fuzzy duplicate pair(s) in '{primary_col}'. Evidence: {'; '.join(evidence_samples)}",
                "repair_recommended": "flag_potential_duplicates",
                "details": {"pairs": found_pairs, "column": primary_col}
            })

    def _detect_whitespace_and_casing(self):
        """Finds leading/trailing whitespace and inconsistent casing in string columns."""
        for col in self.columns:
            if self._is_text_column(col):
                series = self.df[col].dropna().astype(str)
                
                # Check leading/trailing spaces
                padded_mask = series.str.startswith(" ") | series.str.endswith(" ")
                padded_indices = series.index[padded_mask].tolist()
                
                if padded_indices:
                    self.issues.append({
                        "id": self._next_id(),
                        "category": CATEGORY_WHITESPACE_CASING,
                        "column": col,
                        "count": len(padded_indices),
                        "affected_rows": padded_indices,
                        "severity": SEVERITY_LOW,
                        "confidence": 1.0,
                        "evidence": f"Column '{col}' has {len(padded_indices)} records with leading/trailing whitespace. Sample rows: {padded_indices[:4]}",
                        "repair_recommended": "strip_whitespace",
                        "details": {"column": col, "indices": padded_indices}
                    })
                    
                # Check casing glitches (e.g. 'bOB SMITH', mixed capitalization)
                casing_glitches = []
                for idx, val in series.items():
                    s = str(val).strip()
                    if len(s) > 2 and s[0].islower() and any(c.isupper() for c in s[1:]):
                        casing_glitches.append(idx)
                        
                if casing_glitches:
                    self.issues.append({
                        "id": self._next_id(),
                        "category": CATEGORY_WHITESPACE_CASING,
                        "column": col,
                        "count": len(casing_glitches),
                        "affected_rows": casing_glitches,
                        "severity": SEVERITY_LOW,
                        "confidence": 0.90,
                        "evidence": f"Column '{col}' contains {len(casing_glitches)} inverted or haphazard casing records (e.g., '{series.loc[casing_glitches[0]]}').",
                        "repair_recommended": "standardize_casing_title",
                        "details": {"column": col, "indices": casing_glitches}
                    })

    def _detect_invalid_formats(self):
        """Validates format compliance for emails, phone numbers, and URLs."""
        for col in self.columns:
            col_lower = col.lower()
            series = self.df[col].dropna().astype(str).str.strip()
            
            # Email detection
            if "email" in col_lower or any("@" in str(v) for v in series.head(5)):
                invalid_emails = []
                typo_domain_emails = []
                
                for idx, val in series.items():
                    val_str = str(val).strip()
                    fixed = fix_email_domain_typo(val_str)
                    if fixed:
                        typo_domain_emails.append((idx, val, fixed))
                    elif not is_valid_email(val_str):
                        invalid_emails.append((idx, val))
                            
                if typo_domain_emails:
                    affected_rows = [t[0] for t in typo_domain_emails]
                    self.issues.append({
                        "id": self._next_id(),
                        "category": CATEGORY_INVALID_FORMAT,
                        "column": col,
                        "count": len(typo_domain_emails),
                        "affected_rows": affected_rows,
                        "severity": SEVERITY_HIGH,
                        "confidence": 0.95,
                        "evidence": f"{len(typo_domain_emails)} email(s) have recognizable domain typos (e.g., '{typo_domain_emails[0][1]}' -> '{typo_domain_emails[0][2]}').",
                        "repair_recommended": "fix_email_typo",
                        "details": {"column": col, "corrections": typo_domain_emails}
                    })
                    
                if invalid_emails:
                    affected_rows = [t[0] for t in invalid_emails]
                    self.issues.append({
                        "id": self._next_id(),
                        "category": CATEGORY_INVALID_FORMAT,
                        "column": col,
                        "count": len(invalid_emails),
                        "affected_rows": affected_rows,
                        "severity": SEVERITY_HIGH,
                        "confidence": 0.90,
                        "evidence": f"{len(invalid_emails)} email address(es) violate RFC 5322 email syntax (e.g., '{invalid_emails[0][1]}').",
                        "repair_recommended": "flag_invalid_format",
                        "details": {"column": col, "invalid_entries": invalid_emails}
                    })

            # Phone number detection
            if "phone" in col_lower or "contact" in col_lower:
                invalid_phones = []
                unformatted_phones = []
                
                for idx, val in series.items():
                    if not is_valid_phone(val):
                        invalid_phones.append((idx, val))
                    else:
                        norm = normalize_phone_number(val)
                        if norm and norm != val:
                            unformatted_phones.append((idx, val, norm))
                            
                if invalid_phones:
                    affected_rows = [p[0] for p in invalid_phones]
                    self.issues.append({
                        "id": self._next_id(),
                        "category": CATEGORY_INVALID_FORMAT,
                        "column": col,
                        "count": len(invalid_phones),
                        "affected_rows": affected_rows,
                        "severity": SEVERITY_MEDIUM,
                        "confidence": 0.95,
                        "evidence": f"{len(invalid_phones)} phone number(s) contain invalid characters or insufficient digits (e.g., '{invalid_phones[0][1]}').",
                        "repair_recommended": "flag_invalid_phone",
                        "details": {"column": col, "entries": invalid_phones}
                    })
                    
                if unformatted_phones:
                    affected_rows = [p[0] for p in unformatted_phones]
                    self.issues.append({
                        "id": self._next_id(),
                        "category": CATEGORY_INVALID_FORMAT,
                        "column": col,
                        "count": len(unformatted_phones),
                        "affected_rows": affected_rows,
                        "severity": SEVERITY_LOW,
                        "confidence": 0.92,
                        "evidence": f"{len(unformatted_phones)} phone number(s) lack standard formatting (e.g. '{unformatted_phones[0][1]}' -> '{unformatted_phones[0][2]}').",
                        "repair_recommended": "normalize_phone_format",
                        "details": {"column": col, "corrections": unformatted_phones}
                    })

    def _detect_date_and_numeric_errors(self):
        """Identifies unparseable dates, out-of-range dates, and illegal negative numbers."""
        for col in self.columns:
            col_lower = col.lower()
            series = self.df[col].dropna()
            
            # Date analysis
            if any(k in col_lower for k in ["date", "time", "birth", "hire", "signup", "order"]):
                unparseable_dates = []
                mixed_format_dates = []
                
                for idx, val in series.items():
                    ok, dt = try_parse_date(val)
                    if not ok:
                        unparseable_dates.append((idx, val))
                    elif isinstance(val, str) and ("/" in val or "-" in val):
                        # Detect if non-ISO (ISO is YYYY-MM-DD)
                        if not re.match(r"^\d{4}-\d{2}-\d{2}$", val.strip()):
                            mixed_format_dates.append((idx, val, dt.strftime("%Y-%m-%d")))
                            
                if unparseable_dates:
                    affected_rows = [d[0] for d in unparseable_dates]
                    self.issues.append({
                        "id": self._next_id(),
                        "category": CATEGORY_DATE_NUMERIC,
                        "column": col,
                        "count": len(unparseable_dates),
                        "affected_rows": affected_rows,
                        "severity": SEVERITY_HIGH,
                        "confidence": 0.95,
                        "evidence": f"Found {len(unparseable_dates)} unparseable date strings in '{col}' (e.g., '{unparseable_dates[0][1]}').",
                        "repair_recommended": "flag_or_impute_date",
                        "details": {"column": col, "entries": unparseable_dates}
                    })
                    
                if mixed_format_dates:
                    affected_rows = [d[0] for d in mixed_format_dates]
                    self.issues.append({
                        "id": self._next_id(),
                        "category": CATEGORY_DATE_NUMERIC,
                        "column": col,
                        "count": len(mixed_format_dates),
                        "affected_rows": affected_rows,
                        "severity": SEVERITY_MEDIUM,
                        "confidence": 0.98,
                        "evidence": f"{len(mixed_format_dates)} dates in '{col}' use non-standard or mixed formatting (e.g., '{mixed_format_dates[0][1]}' -> '{mixed_format_dates[0][2]}').",
                        "repair_recommended": "normalize_date_iso",
                        "details": {"column": col, "corrections": mixed_format_dates}
                    })

            # Negative numerical constraints (age, quantity, salary, price should not be negative)
            if any(k in col_lower for k in ["age", "quantity", "price", "salary", "income", "amount", "total"]):
                negative_entries = []
                for idx, val in series.items():
                    ok, num = clean_numeric_string(val)
                    if ok and num < 0:
                        negative_entries.append((idx, val, abs(num)))
                        
                if negative_entries:
                    affected_rows = [n[0] for n in negative_entries]
                    self.issues.append({
                        "id": self._next_id(),
                        "category": CATEGORY_DATE_NUMERIC,
                        "column": col,
                        "count": len(negative_entries),
                        "affected_rows": affected_rows,
                        "severity": SEVERITY_HIGH,
                        "confidence": 0.92,
                        "evidence": f"Found {len(negative_entries)} illegal negative numerical values in strictly positive field '{col}' (e.g., '{negative_entries[0][1]}').",
                        "repair_recommended": "convert_absolute_or_flag",
                        "details": {"column": col, "entries": negative_entries}
                    })

    def _detect_inconsistent_categories(self):
        """Identifies inconsistent categorical variations, aliases, abbreviations, and casing variations."""
        # Standard known dictionary mappings for state, gender, departments
        KNOWN_CANONICAL = {
            "state": {
                "california": "California", "ca": "California", "calif": "California",
                "new york": "New York", "ny": "New York",
                "texas": "Texas", "tx": "Texas",
                "florida": "Florida", "fl": "Florida"
            },
            "gender": {
                "male": "Male", "m": "Male",
                "female": "Female", "f": "Female",
                "other": "Other", "non-binary": "Non-Binary"
            },
            "department": {
                "engineering": "Engineering", "eng": "Engineering", "eng.": "Engineering",
                "human resources": "Human Resources", "hr": "Human Resources",
                "operations": "Operations", "ops": "Operations",
                "security": "Security", "sec": "Security"
            },
            "category": {
                "electronics": "Electronics", "electrnx": "Electronics",
                "accessories": "Accessories", "acc": "Accessories",
                "furniture": "Furniture", "furn": "Furniture"
            },
            "status": {
                "completed": "Completed", "complete": "Completed",
                "shipped": "Shipped", "pending": "Pending", "delivered": "Delivered", "cancelled": "Cancelled"
            }
        }
        
        for col in self.columns:
            if not self._is_text_column(col):
                continue
            col_lower = col.lower()
            matching_key = next((k for k in KNOWN_CANONICAL if k in col_lower), None)
            
            if matching_key:
                mapping = KNOWN_CANONICAL[matching_key]
                series = self.df[col].dropna().astype(str).str.strip()
                inconsistent_rows = []
                
                for idx, val in series.items():
                    val_clean = val.lower().replace(".", "")
                    if val_clean in mapping and val != mapping[val_clean]:
                        inconsistent_rows.append((idx, val, mapping[val_clean]))
                        
                if inconsistent_rows:
                    affected_rows = [r[0] for r in inconsistent_rows]
                    samples = [f"'{r[1]}' -> '{r[2]}'" for r in inconsistent_rows[:3]]
                    self.issues.append({
                        "id": self._next_id(),
                        "category": CATEGORY_INCONSISTENT_CAT,
                        "column": col,
                        "count": len(inconsistent_rows),
                        "affected_rows": affected_rows,
                        "severity": SEVERITY_MEDIUM,
                        "confidence": 0.95,
                        "evidence": f"Found {len(inconsistent_rows)} inconsistent category values in '{col}'. Examples: {', '.join(samples)}",
                        "repair_recommended": "standardize_categorical_values",
                        "details": {"column": col, "corrections": inconsistent_rows}
                    })

    def _detect_unexpected_data_types(self):
        """Identifies numeric columns stored as objects due to currency signs, commas, or text."""
        for col in self.columns:
            if not self._is_text_column(col):
                continue
            series = self.df[col].dropna().astype(str).str.strip()
            if len(series) == 0:
                continue
                
            # Count values that look like numbers with currency or commas
            convertible_count = 0
            dirty_samples = []
            
            for idx, val in series.items():
                ok, num = clean_numeric_string(val)
                if ok:
                    convertible_count += 1
                    if any(char in val for char in ["$", "€", "£", ",", "%"]):
                        dirty_samples.append((idx, val, num))
                        
            # If >= 70% of non-null values are numeric, the column is semantically numeric
            if (convertible_count / len(series)) >= 0.70 and dirty_samples:
                affected_rows = [d[0] for d in dirty_samples]
                self.issues.append({
                    "id": self._next_id(),
                    "category": CATEGORY_DATA_TYPE,
                    "column": col,
                    "count": len(dirty_samples),
                    "affected_rows": affected_rows,
                    "severity": SEVERITY_MEDIUM,
                    "confidence": 0.96,
                    "evidence": f"Column '{col}' is stored as string/object but contains {len(dirty_samples)} formatted numbers with currency symbols or commas (e.g. '{dirty_samples[0][1]}').",
                    "repair_recommended": "clean_and_cast_numeric",
                    "details": {"column": col, "conversions": dirty_samples}
                })

    def _detect_statistical_outliers(self):
        """Applies robust Interquartile Range (IQR) and Z-score outlier detection on numeric fields."""
        for col in self.columns:
            # Try to get clean numeric values
            raw_series = self.df[col].dropna()
            cleaned_vals = []
            valid_indices = []
            
            for idx, val in raw_series.items():
                ok, num = clean_numeric_string(val)
                if ok:
                    cleaned_vals.append(num)
                    valid_indices.append(idx)
                    
            if len(cleaned_vals) >= 8:
                num_series = pd.Series(cleaned_vals, index=valid_indices)
                q1 = num_series.quantile(0.25)
                q3 = num_series.quantile(0.75)
                iqr = q3 - q1
                
                if iqr > 0:
                    lower_bound = q1 - (1.5 * iqr)
                    upper_bound = q3 + (1.5 * iqr)
                    
                    # Also check domain realistic sanity limits
                    col_lower = col.lower()
                    if "age" in col_lower:
                        upper_bound = min(upper_bound, 120.0)
                        lower_bound = max(lower_bound, 0.0)
                        
                    outlier_mask = (num_series < lower_bound) | (num_series > upper_bound)
                    outlier_indices = num_series.index[outlier_mask].tolist()
                    
                    if outlier_indices:
                        samples = [f"Row {i}: {num_series.loc[i]}" for i in outlier_indices[:3]]
                        self.issues.append({
                            "id": self._next_id(),
                            "category": CATEGORY_OUTLIER,
                            "column": col,
                            "count": len(outlier_indices),
                            "affected_rows": outlier_indices,
                            "severity": SEVERITY_MEDIUM,
                            "confidence": 0.88,
                            "evidence": f"Identified {len(outlier_indices)} statistical outlier(s) in '{col}' outside IQR bounds [{lower_bound:.1f}, {upper_bound:.1f}]. Samples: {', '.join(samples)}",
                            "repair_recommended": "cap_outliers_iqr",
                            "details": {
                                "column": col,
                                "lower_bound": lower_bound,
                                "upper_bound": upper_bound,
                                "median": float(num_series.median()),
                                "indices": outlier_indices
                            }
                        })

    def _detect_cross_column_inconsistencies(self):
        """Validates cross-column arithmetic and logical constraints."""
        col_map = {c.lower().replace("_", "").replace(" ", ""): c for c in self.columns}
        
        # 1. Sales arithmetic: Total Amount == Quantity * Unit Price
        qty_col = next((c for c in self.columns if any(k in c.lower() for k in ["quantity", "qty"])), None)
        price_col = next((c for c in self.columns if any(k in c.lower() for k in ["unitprice", "unit_price", "price"])), None)
        total_col = next((c for c in self.columns if any(k in c.lower() for k in ["totalamount", "total_amount", "total"])), None)
        
        if qty_col and price_col and total_col and len({qty_col, price_col, total_col}) == 3:
            mismatches = []
            for idx in self.df.index:
                q_ok, q_val = clean_numeric_string(self.df.at[idx, qty_col])
                p_ok, p_val = clean_numeric_string(self.df.at[idx, price_col])
                t_ok, t_val = clean_numeric_string(self.df.at[idx, total_col])
                
                if q_ok and p_ok and t_ok and q_val > 0 and p_val > 0:
                    expected_total = round(q_val * p_val, 2)
                    # Allow 1 cent rounding difference
                    if abs(t_val - expected_total) > 0.05:
                        mismatches.append((idx, t_val, expected_total, q_val, p_val))
                        
            if mismatches:
                affected_rows = [m[0] for m in mismatches]
                sample_msg = f"Row {mismatches[0][0]}: Total recorded is {mismatches[0][1]}, but {mismatches[0][3]} qty * {mismatches[0][4]} unit price = {mismatches[0][2]}"
                self.issues.append({
                    "id": self._next_id(),
                    "category": CATEGORY_CROSS_COLUMN,
                    "column": f"{total_col} vs ({qty_col} * {price_col})",
                    "count": len(mismatches),
                    "affected_rows": affected_rows,
                    "severity": SEVERITY_HIGH,
                    "confidence": 0.96,
                    "evidence": f"Found {len(mismatches)} mathematical mismatch(es) where recorded Total does not match Quantity * Price. Evidence: {sample_msg}",
                    "repair_recommended": "recalculate_cross_column_total",
                    "details": {
                        "total_col": total_col,
                        "qty_col": qty_col,
                        "price_col": price_col,
                        "mismatches": mismatches
                    }
                })

        # 2. Date logical sequence: Hire Date must be after Birth Date (+ 16 years)
        birth_col = next((c for c in self.columns if any(k in c.lower() for k in ["birthdate", "birth_date", "dob"])), None)
        hire_col = next((c for c in self.columns if any(k in c.lower() for k in ["hiredate", "hire_date", "startdate", "start_date"])), None)
        
        if birth_col and hire_col and birth_col != hire_col:
            temporal_errors = []
            for idx in self.df.index:
                b_ok, b_dt = try_parse_date(self.df.at[idx, birth_col])
                h_ok, h_dt = try_parse_date(self.df.at[idx, hire_col])
                
                if b_ok and h_ok:
                    # Check if hire date is before birth date, or hired when under 16
                    age_at_hire = (h_dt - b_dt).days / 365.25
                    if age_at_hire < 16:
                        temporal_errors.append((idx, b_dt.strftime("%Y-%m-%d"), h_dt.strftime("%Y-%m-%d"), round(age_at_hire, 1)))
                        
            if temporal_errors:
                affected_rows = [t[0] for t in temporal_errors]
                sample = temporal_errors[0]
                self.issues.append({
                    "id": self._next_id(),
                    "category": CATEGORY_CROSS_COLUMN,
                    "column": f"{hire_col} vs {birth_col}",
                    "count": len(temporal_errors),
                    "affected_rows": affected_rows,
                    "severity": SEVERITY_CRITICAL,
                    "confidence": 0.98,
                    "evidence": f"Found {len(temporal_errors)} temporal impossibility record(s). Row {sample[0]}: Birth Date is {sample[1]} but Hire Date is {sample[2]} (calculated age at hire: {sample[3]} yrs).",
                    "repair_recommended": "flag_temporal_violation",
                    "details": {"birth_col": birth_col, "hire_col": hire_col, "errors": temporal_errors}
                })
