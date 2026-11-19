"""
DataFix - Automated Tests for Data Integrity & Security
Validates cryptographic immutability hashing, isolation of working copies, and schema invariance.
"""

import unittest
import pandas as pd
from utils.data_integrity import (
    compute_dataframe_hash,
    verify_dataset_immutability,
    create_safe_working_copy,
    check_schema_preservation,
    verify_unintended_changes
)


class TestDataIntegrity(unittest.TestCase):

    def setUp(self):
        self.df = pd.DataFrame({
            "user_id": [101, 102, 103],
            "username": ["john_doe", "jane_smith", "alex_m"],
            "score": [88.5, 92.0, 79.5]
        })

    def test_hash_immutability(self):
        orig_hash = compute_dataframe_hash(self.df)
        self.assertTrue(len(orig_hash) == 64) # SHA-256 length
        self.assertTrue(verify_dataset_immutability(self.df, orig_hash))

        # Modifying a cell must break hash verification
        mutated_df = self.df.copy()
        mutated_df.at[0, "score"] = 99.9
        self.assertFalse(verify_dataset_immutability(mutated_df, orig_hash))

    def test_safe_working_copy_isolation(self):
        working_copy = create_safe_working_copy(self.df)
        working_copy.at[0, "username"] = "changed_name"

        # Verify original remained completely untouched
        self.assertEqual(self.df.at[0, "username"], "john_doe")

    def test_schema_preservation_check(self):
        # Case 1: Identical schema
        rep_df = self.df.copy()
        check1 = check_schema_preservation(self.df, rep_df)
        self.assertTrue(check1["preserved"])

        # Case 2: Dropped column
        rep_df_dropped = self.df.drop(columns=["score"])
        check2 = check_schema_preservation(self.df, rep_df_dropped)
        self.assertFalse(check2["preserved"])
        self.assertIn("score", check2["missing_columns"])

        # Case 3: Reordered columns
        rep_df_reordered = self.df[["score", "username", "user_id"]]
        check3 = check_schema_preservation(self.df, rep_df_reordered)
        self.assertFalse(check3["preserved"])
        self.assertFalse(check3["order_preserved"])

    def test_audit_invariance_verification(self):
        repaired_df = self.df.copy()
        repaired_df.at[1, "username"] = "Jane Smith"

        # When logged: verified is True
        audit_log = [{
            "row_index": 1,
            "column": "username",
            "repair_method": "title_case"
        }]
        res_ok = verify_unintended_changes(self.df, repaired_df, audit_log)
        self.assertTrue(res_ok["verified"])

        # When unlogged: verified is False
        res_fail = verify_unintended_changes(self.df, repaired_df, [])
        self.assertFalse(res_fail["verified"])
        self.assertEqual(res_fail["unlogged_changes_count"], 1)


if __name__ == "__main__":
    unittest.main()
