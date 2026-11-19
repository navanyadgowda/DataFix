"""
DataFix - Autonomous Data Quality and Repair Engine
Configuration and Global Constants
"""

import os

# Application Metadata
APP_NAME = "DataFix"
APP_SUBTITLE = "Autonomous Data Quality & Repair Engine"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "Intelligent automated data quality detection, root cause diagnosis, autonomous safe repair, explainability, and validation platform."

# Color Theme Palette (Navy Blue, Subtle Cyan, Clean White)
THEME_COLORS = {
    "primary": "#0B192C",       # Deep Navy
    "secondary": "#1E3E62",     # Royal Navy
    "accent": "#00ADB5",        # Subtle Cyan
    "accent_dark": "#088395",   # Ocean Blue
    "background": "#F8FAFC",    # Slate Light White
    "surface": "#FFFFFF",       # Card White
    "text_dark": "#1E293B",     # Deep Slate
    "text_muted": "#64748B",    # Muted Slate
    "border": "#E2E8F0",        # Light Slate Border
    "success": "#10B981",       # Emerald Green
    "warning": "#F59E0B",       # Amber Warning
    "danger": "#EF4444",        # Crimson Red
    "info": "#3B82F6",          # Sky Blue
    "purple": "#8B5CF6"         # Violet
}

# Issue Severity Levels
SEVERITY_CRITICAL = "Critical"
SEVERITY_HIGH = "High"
SEVERITY_MEDIUM = "Medium"
SEVERITY_LOW = "Low"

# Issue Categories
CATEGORY_MISSING = "Missing & Null Values"
CATEGORY_EXACT_DUPLICATES = "Exact Duplicate Records"
CATEGORY_POTENTIAL_DUPLICATES = "Potential / Fuzzy Duplicates"
CATEGORY_INVALID_FORMAT = "Invalid Formats"
CATEGORY_DATE_NUMERIC = "Date & Numeric Errors"
CATEGORY_INCONSISTENT_CAT = "Inconsistent Categoricals"
CATEGORY_WHITESPACE_CASING = "Whitespace & Casing Glitches"
CATEGORY_DATA_TYPE = "Unexpected Data Types"
CATEGORY_OUTLIER = "Statistical Anomalies & Outliers"
CATEGORY_CROSS_COLUMN = "Cross-Column Inconsistencies"

# Confidence Thresholds
CONFIDENCE_AUTO_REPAIR_THRESHOLD = 0.85  # Repairs with >= 85% confidence qualify for safe auto-repair
CONFIDENCE_HIGH = 0.80
CONFIDENCE_MEDIUM = 0.60
CONFIDENCE_LOW = 0.40

# Quality Score Weights (Total = 100%)
QUALITY_SCORE_WEIGHTS = {
    "completeness": 0.25,      # 25% penalty for missing / null data
    "validity": 0.25,          # 25% penalty for format, range, regex errors
    "consistency": 0.20,       # 20% penalty for casing, category, and cross-column errors
    "uniqueness": 0.15,        # 15% penalty for exact and potential duplicates
    "integrity": 0.15          # 15% penalty for outliers and type mismatches
}

# Max rows for expensive pairwise fuzzy matching (for responsiveness)
MAX_ROWS_PAIRWISE_FUZZY = 1500
MAX_PREVIEW_ROWS = 100

# File Upload Limits
MAX_UPLOAD_SIZE_MB = 200
SUPPORTED_EXTENSIONS = [".csv", ".xlsx", ".xls", ".json"]
