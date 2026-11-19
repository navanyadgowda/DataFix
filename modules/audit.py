"""
DataFix - Audit and Tracking System
Maintains an immutable modification history ledger, diff comparisons, and state rollback / undo manager.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd


class AuditTracker:
    """Manages transactional modification logging, before/after diffs, and undo operations."""

    @staticmethod
    def get_audit_dataframe(audit_log: List[Dict[str, Any]]) -> pd.DataFrame:
        """Converts raw audit log entries into a clean presentation DataFrame."""
        if not audit_log:
            return pd.DataFrame(columns=[
                "Timestamp", "Row", "Column", "Original Value", 
                "Updated Value", "Method", "Confidence", "Reason", "Status"
            ])
            
        rows = []
        for entry in audit_log:
            conf = entry.get("confidence", 1.0)
            rows.append({
                "Timestamp": entry.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                "Row": entry.get("row_index", "N/A"),
                "Column": entry.get("column", "N/A"),
                "Original Value": str(entry.get("original_value", "")),
                "Updated Value": str(entry.get("updated_value", "")),
                "Method": entry.get("repair_method", "N/A"),
                "Confidence": f"{int(conf * 100)}%",
                "Reason": entry.get("reason", "N/A"),
                "Status": entry.get("approval_status", "Approved")
            })
            
        return pd.DataFrame(rows)

    @staticmethod
    def generate_diff_table(
        original_df: pd.DataFrame, 
        repaired_df: pd.DataFrame, 
        audit_log: List[Dict[str, Any]],
        limit: int = 50
    ) -> pd.DataFrame:
        """
        Creates a side-by-side diff table showing affected rows, highlighting original vs updated values.
        """
        if original_df is None or repaired_df is None or not audit_log:
            return pd.DataFrame(columns=["Row", "Column", "Original Value", "Repaired Value", "Method", "Confidence"])

        diff_rows = []
        for entry in audit_log[:limit]:
            row_idx = entry.get("row_index")
            col = entry.get("column")
            orig_val = entry.get("original_value")
            new_val = entry.get("updated_value")
            method = entry.get("repair_method")
            conf = entry.get("confidence", 1.0)

            diff_rows.append({
                "Row Index": row_idx,
                "Column Affected": col,
                "Original Value": orig_val,
                "Repaired Value": new_val,
                "Repair Technique": method,
                "Confidence": f"{int(conf * 100)}%"
            })

        return pd.DataFrame(diff_rows)

    @staticmethod
    def push_undo_snapshot(undo_stack: list, current_df: pd.DataFrame, current_audit_len: int):
        """Pushes current working copy and audit log count to undo stack."""
        undo_stack.append({
            "df_snapshot": current_df.copy(deep=True),
            "audit_len": current_audit_len
        })

    @staticmethod
    def pop_undo_snapshot(
        undo_stack: list, 
        audit_log: list
    ) -> Tuple[Optional[pd.DataFrame], List[Dict[str, Any]]]:
        """Pops the most recent snapshot from undo stack, rolling back state."""
        if not undo_stack:
            return None, audit_log
        
        last_state = undo_stack.pop()
        target_len = last_state.get("audit_len", 0)
        # Trim audit log to prior length
        restored_audit_log = audit_log[:target_len]
        return last_state.get("df_snapshot"), restored_audit_log
