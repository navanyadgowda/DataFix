"""
DataFix - Validation Engine
Conducts post-repair re-scanning, compares pre- vs post-repair metrics, verifies preservation
of valid untouched records, checks schema integrity, and issues final validation certifications.
"""

from typing import Dict, Any, List
import pandas as pd

from modules.detection import DataQualityDetector
from modules.quality_score import compute_quality_score
from utils.data_integrity import check_schema_preservation, verify_unintended_changes


class ValidationEngine:
    """Validates data repairs by re-scanning, diffing metrics, and verifying schema integrity."""

    def __init__(
        self, 
        original_df: pd.DataFrame, 
        repaired_df: pd.DataFrame, 
        initial_issues: List[Dict[str, Any]], 
        audit_log: List[Dict[str, Any]]
    ):
        self.original_df = original_df
        self.repaired_df = repaired_df
        self.initial_issues = initial_issues
        self.audit_log = audit_log

    def validate(self) -> Dict[str, Any]:
        """Performs full post-repair validation suite and returns structured report."""
        if self.repaired_df is None:
            return {"status": "FAIL", "reason": "Repaired dataset is None"}

        # 1. Re-scan repaired dataset for remaining defects
        detector = DataQualityDetector(self.repaired_df)
        remaining_issues = detector.detect_all()

        # 2. Compute post-repair quality score
        post_score_data = compute_quality_score(self.repaired_df, remaining_issues)
        pre_score_data = compute_quality_score(self.original_df, self.initial_issues)

        # 3. Schema & Structure Preservation Check
        schema_check = check_schema_preservation(self.original_df, self.repaired_df)

        # 4. Unintended Changes & Invariance Check
        invariance_check = verify_unintended_changes(self.original_df, self.repaired_df, self.audit_log)

        # 5. Issue Resolution Accounting
        total_initial_issues = len(self.initial_issues)
        total_remaining_issues = len(remaining_issues)
        total_repairs_applied = len(self.audit_log)
        
        # Calculate issues resolved
        resolved_count = max(0, total_initial_issues - total_remaining_issues)

        # Determine Certification Status
        score_diff = post_score_data["overall_score"] - pre_score_data["overall_score"]
        
        if invariance_check["verified"] and schema_check["preserved"] and total_remaining_issues == 0:
            cert_status = "CERTIFIED_PERFECT"
            badge = "PASS"
            summary_msg = "All detectable data quality issues were successfully resolved with 100% schema and cell invariance."
        elif invariance_check["verified"] and schema_check["preserved"] and score_diff >= 0:
            cert_status = "CERTIFIED_VALID"
            badge = "PASS"
            summary_msg = f"Repairs validated successfully. Quality score improved by +{score_diff:.1f} points with zero unauthorized changes."
        elif not schema_check["preserved"]:
            cert_status = "SCHEMA_WARNING"
            badge = "WARNING"
            summary_msg = "Schema discrepancies detected between original and repaired datasets."
        elif not invariance_check["verified"]:
            cert_status = "INTEGRITY_WARNING"
            badge = "WARNING"
            summary_msg = f"Detected {invariance_check['unlogged_changes_count']} cell change(s) without matching audit entries."
        else:
            cert_status = "QUALITY_REGRESSION"
            badge = "FAIL"
            summary_msg = "Post-repair validation detected regressions or unresolved critical defects."

        return {
            "status": badge,
            "certification_code": cert_status,
            "summary_message": summary_msg,
            "pre_score": pre_score_data["overall_score"],
            "post_score": post_score_data["overall_score"],
            "score_delta": round(score_diff, 1),
            "pre_dimensions": pre_score_data["dimensions"],
            "post_dimensions": post_score_data["dimensions"],
            "initial_issues_count": total_initial_issues,
            "remaining_issues_count": total_remaining_issues,
            "remaining_issues": remaining_issues,
            "repairs_applied_count": total_repairs_applied,
            "resolved_issues_count": resolved_count,
            "schema_check": schema_check,
            "invariance_check": invariance_check,
            "row_count_before": len(self.original_df),
            "row_count_after": len(self.repaired_df),
            "col_count_before": len(self.original_df.columns),
            "col_count_after": len(self.repaired_df.columns)
        }
