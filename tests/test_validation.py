"""
DataFix - Automated Tests for Validation Engine
Validates re-scanning, score delta calculation, schema preservation, and cell invariance checks.
"""

import unittest
import pandas as pd
from modules.detection import DataQualityDetector
from modules.repair import DataRepairEngine
from modules.validation import ValidationEngine


class TestValidationEngine(unittest.TestCase):

    def setUp(self):
        self.original_df = pd.DataFrame({
            "name": ["  Alice Cooper  ", "Bob Smith", "Charlie Brown"],
            "email": ["alice@gmail.com", "bob@gmaill.com", "charlie@corp.com"],
            "state": ["CA", "New York", "Texas"],
            "qty": [2, 1, 4],
            "price": [10.0, 50.0, 25.0],
            "total": [20.0, 50.0, 100.0]
        })

    def test_validation_workflow(self):
        # 1. Detect
        detector = DataQualityDetector(self.original_df)
        initial_issues = detector.detect_all()
        self.assertTrue(len(initial_issues) > 0)

        # 2. Repair
        engine = DataRepairEngine(self.original_df, initial_issues)
        proposals = engine.generate_repair_proposals()
        safe_props = [p for p in proposals if p.get("is_safe_auto")]
        repaired_df, logs = DataRepairEngine.apply_batch_repairs(self.original_df, safe_props)

        # 3. Validate
        val_engine = ValidationEngine(self.original_df, repaired_df, initial_issues, logs)
        report = val_engine.validate()

        self.assertEqual(report["status"], "PASS")
        self.assertTrue(report["post_score"] >= report["pre_score"])
        self.assertTrue(report["schema_check"]["preserved"])
        self.assertTrue(report["invariance_check"]["verified"])
        self.assertEqual(report["invariance_check"]["unlogged_changes_count"], 0)

    def test_unlogged_change_detection(self):
        # Deliberately inject an unauthorized silent modification into repaired_df
        tampered_df = self.original_df.copy(deep=True)
        tampered_df.at[0, "name"] = "Malicious Modification"
        
        val_engine = ValidationEngine(self.original_df, tampered_df, [], audit_log=[])
        report = val_engine.validate()
        
        self.assertFalse(report["invariance_check"]["verified"])
        self.assertEqual(report["invariance_check"]["unlogged_changes_count"], 1)


if __name__ == "__main__":
    unittest.main()
