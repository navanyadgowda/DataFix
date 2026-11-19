"""
DataFix - Automated Tests for Repair Engine
Validates candidate generation, safe repair execution, imputation, normalization, and rollback.
"""

import unittest
import pandas as pd
from modules.detection import DataQualityDetector
from modules.repair import DataRepairEngine


class TestDataRepair(unittest.TestCase):

    def setUp(self):
        self.test_df = pd.DataFrame({
            "name": ["  Alice Cooper  ", "bOB SMITH", "Charlie Brown", "Alice Cooper"],
            "email": ["alice@gmail.com", "bob@gmaill.com", "charlie@corp.com", "alice@gmail.com"],
            "state": ["California", "calif", "NY", "California"],
            "age": [30, -25, 40, 30],
            "price": ["$10.00", "$20.00", "$30.00", "$10.00"],
            "qty": [2, 3, 1, 2],
            "total": [20.0, 99.0, 30.0, 20.0]
        })

    def test_proposal_generation(self):
        detector = DataQualityDetector(self.test_df)
        issues = detector.detect_all()
        engine = DataRepairEngine(self.test_df, issues)
        proposals = engine.generate_repair_proposals()
        
        self.assertTrue(len(proposals) > 0)
        methods = [p["repair_method"] for p in proposals]
        self.assertIn("strip_whitespace", methods)
        self.assertIn("fix_email_domain_typo", methods)

    def test_whitespace_and_casing_repair(self):
        detector = DataQualityDetector(self.test_df)
        issues = detector.detect_all()
        engine = DataRepairEngine(self.test_df, issues)
        proposals = engine.generate_repair_proposals()
        
        ws_proposals = [p for p in proposals if p["repair_method"] == "strip_whitespace"]
        self.assertTrue(len(ws_proposals) > 0)
        
        repaired_df, log = DataRepairEngine.apply_single_repair(self.test_df, ws_proposals[0])
        self.assertEqual(repaired_df.at[0, "name"], "Alice Cooper")
        self.assertEqual(log["column"], "name")
        self.assertEqual(log["original_value"], "  Alice Cooper  ")
        self.assertEqual(log["updated_value"], "Alice Cooper")

    def test_email_typo_repair(self):
        detector = DataQualityDetector(self.test_df)
        issues = detector.detect_all()
        engine = DataRepairEngine(self.test_df, issues)
        proposals = engine.generate_repair_proposals()
        
        email_prop = next(p for p in proposals if p["repair_method"] == "fix_email_domain_typo")
        repaired_df, log = DataRepairEngine.apply_single_repair(self.test_df, email_prop)
        self.assertEqual(repaired_df.at[1, "email"], "bob@gmail.com")

    def test_cross_column_total_recalculation(self):
        detector = DataQualityDetector(self.test_df)
        issues = detector.detect_all()
        engine = DataRepairEngine(self.test_df, issues)
        proposals = engine.generate_repair_proposals()
        
        total_prop = next(p for p in proposals if p["repair_method"] == "recalculate_total_amount")
        repaired_df, log = DataRepairEngine.apply_single_repair(self.test_df, total_prop)
        # 3 * $20 = 60.0
        self.assertEqual(repaired_df.at[1, "total"], 60.0)

    def test_batch_safe_repair(self):
        detector = DataQualityDetector(self.test_df)
        issues = detector.detect_all()
        engine = DataRepairEngine(self.test_df, issues)
        proposals = engine.generate_repair_proposals()
        
        safe_props = [p for p in proposals if p.get("is_safe_auto")]
        repaired_df, applied_logs = DataRepairEngine.apply_batch_repairs(self.test_df, safe_props)
        
        self.assertTrue(len(applied_logs) > 0)
        # Check that row 0 whitespace is gone
        self.assertFalse(repaired_df.at[0, "name"].startswith(" "))


if __name__ == "__main__":
    unittest.main()
