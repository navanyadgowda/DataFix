"""
DataFix - Automated Tests for Issue Detection Engine
Validates detection of missing values, duplicates, format violations, anomalies, and cross-column logic errors.
"""

import unittest
import pandas as pd
from modules.detection import DataQualityDetector
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
    CATEGORY_CROSS_COLUMN
)


class TestDataQualityDetection(unittest.TestCase):

    def setUp(self):
        # Create a synthetic dataset with controlled intentional defects
        self.test_df = pd.DataFrame({
            "id": [1, 2, 3, 4, 1],  # Row 0 and Row 4 exact duplicate potential
            "name": ["Alice Cooper", "  Bob Smith  ", "bOB SMITH", "Jonathon Miller", "Alice Cooper"],
            "email": ["alice@gmail.com", "bob@gmaill.com", "invalid-email", "jon@miller.com", "alice@gmail.com"],
            "state": ["CA", "California", "calif", "NY", "CA"],
            "age": [25, -5, 180, 32, 25],
            "salary": ["$50,000", "$60,000", None, "$75,000", "$50,000"],
            "order_qty": [2, 3, 1, 4, 2],
            "unit_price": [10.0, 20.0, 15.0, 5.0, 10.0],
            "total_amount": [20.0, 99.0, 15.0, 20.0, 20.0]  # Row 1 mismatch: 3 * 20 = 60, not 99
        })

    def test_missing_values_detection(self):
        detector = DataQualityDetector(self.test_df)
        issues = detector.detect_all()
        missing_issues = [i for i in issues if i["category"] == CATEGORY_MISSING]
        self.assertTrue(len(missing_issues) > 0)
        self.assertTrue(any(i["column"] == "salary" for i in missing_issues))

    def test_exact_duplicates_detection(self):
        detector = DataQualityDetector(self.test_df)
        issues = detector.detect_all()
        dup_issues = [i for i in issues if i["category"] == CATEGORY_EXACT_DUPLICATES]
        self.assertTrue(len(dup_issues) > 0)
        self.assertIn(4, dup_issues[0]["affected_rows"])

    def test_whitespace_and_casing_detection(self):
        detector = DataQualityDetector(self.test_df)
        issues = detector.detect_all()
        ws_issues = [i for i in issues if i["category"] == CATEGORY_WHITESPACE_CASING]
        self.assertTrue(len(ws_issues) > 0)
        self.assertTrue(any("Bob Smith" in str(i["evidence"]) or "bOB" in str(i["evidence"]) for i in ws_issues))

    def test_invalid_formats_detection(self):
        detector = DataQualityDetector(self.test_df)
        issues = detector.detect_all()
        format_issues = [i for i in issues if i["category"] == CATEGORY_INVALID_FORMAT]
        self.assertTrue(len(format_issues) > 0)
        # Should catch bob@gmaill.com typo or invalid-email
        evidence_str = " ".join([i["evidence"] for i in format_issues])
        self.assertTrue("gmaill.com" in evidence_str or "invalid-email" in evidence_str)

    def test_date_and_numeric_errors(self):
        detector = DataQualityDetector(self.test_df)
        issues = detector.detect_all()
        num_issues = [i for i in issues if i["category"] == CATEGORY_DATE_NUMERIC]
        self.assertTrue(len(num_issues) > 0)
        self.assertTrue(any(i["column"] == "age" for i in num_issues))

    def test_inconsistent_categories_detection(self):
        detector = DataQualityDetector(self.test_df)
        issues = detector.detect_all()
        cat_issues = [i for i in issues if i["category"] == CATEGORY_INCONSISTENT_CAT]
        self.assertTrue(len(cat_issues) > 0)
        self.assertTrue(any(i["column"] == "state" for i in cat_issues))

    def test_unexpected_data_types_detection(self):
        detector = DataQualityDetector(self.test_df)
        issues = detector.detect_all()
        type_issues = [i for i in issues if i["category"] == CATEGORY_DATA_TYPE]
        self.assertTrue(len(type_issues) > 0)
        self.assertTrue(any(i["column"] == "salary" for i in type_issues))

    def test_cross_column_math_inconsistency(self):
        detector = DataQualityDetector(self.test_df)
        issues = detector.detect_all()
        cross_issues = [i for i in issues if i["category"] == CATEGORY_CROSS_COLUMN]
        self.assertTrue(len(cross_issues) > 0)
        # Row 1 has total_amount 99 != 3 * 20
        self.assertIn(1, cross_issues[0]["affected_rows"])


if __name__ == "__main__":
    unittest.main()
