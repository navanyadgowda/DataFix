"""
DataFix - File Handler Utilities
Handles ingestion, format detection, encoding fallbacks, and export serialization.
"""

import io
import os
import json
import pandas as pd
from typing import Dict, Any, Tuple, Optional
from config import MAX_UPLOAD_SIZE_MB, SUPPORTED_EXTENSIONS


def get_file_info(file_obj, filename: str) -> Dict[str, Any]:
    """Extracts size, extension, and metadata from an uploaded file."""
    file_size_bytes = 0
    if hasattr(file_obj, "size"):
        file_size_bytes = file_obj.size
    elif hasattr(file_obj, "getbuffer"):
        file_size_bytes = len(file_obj.getbuffer())
    elif isinstance(file_obj, (bytes, bytearray)):
        file_size_bytes = len(file_obj)
    elif os.path.exists(filename):
        file_size_bytes = os.path.getsize(filename)

    ext = os.path.splitext(filename)[1].lower()
    return {
        "filename": filename,
        "extension": ext,
        "size_bytes": file_size_bytes,
        "size_mb": round(file_size_bytes / (1024 * 1024), 2),
        "is_supported": ext in SUPPORTED_EXTENSIONS
    }


def load_dataset(file_source, filename: str) -> Tuple[bool, Optional[pd.DataFrame], str]:
    """
    Safely loads CSV, XLSX, or JSON into a pandas DataFrame with robust encoding recovery.
    Supports file paths, BytesIO, or uploaded file buffers.
    Returns (success, dataframe, message).
    """
    ext = os.path.splitext(filename)[1].lower()
    
    if ext not in SUPPORTED_EXTENSIONS:
        return False, None, f"Unsupported format '{ext}'. Supported formats: {', '.join(SUPPORTED_EXTENSIONS)}"
    
    # Check file size limit
    if hasattr(file_source, "size") and file_source.size > MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        return False, None, f"File size exceeds maximum limit of {MAX_UPLOAD_SIZE_MB}MB."
    
    try:
        # Reset pointer if it's a stream
        if hasattr(file_source, "seek"):
            file_source.seek(0)
            
        df = None
        if ext == ".csv":
            # Attempt multi-encoding fallback
            encodings = ["utf-8", "utf-8-sig", "latin1", "cp1252", "iso-8859-1"]
            last_err = None
            for enc in encodings:
                try:
                    if hasattr(file_source, "seek"):
                        file_source.seek(0)
                    df = pd.read_csv(file_source, encoding=enc, low_memory=False)
                    break
                except Exception as e:
                    last_err = e
            if df is None:
                return False, None, f"Failed to parse CSV with standard encodings. Details: {str(last_err)}"

        elif ext in [".xlsx", ".xls"]:
            if hasattr(file_source, "seek"):
                file_source.seek(0)
            try:
                df = pd.read_excel(file_source, engine="openpyxl")
            except Exception:
                if hasattr(file_source, "seek"):
                    file_source.seek(0)
                df = pd.read_excel(file_source)

        elif ext == ".json":
            if hasattr(file_source, "seek"):
                file_source.seek(0)
            try:
                # Try records orient first
                df = pd.read_json(file_source)
            except Exception:
                if hasattr(file_source, "seek"):
                    file_source.seek(0)
                # Try lines orient or plain json
                content = file_source.read() if hasattr(file_source, "read") else open(file_source, "r").read()
                if isinstance(content, bytes):
                    content = content.decode("utf-8", errors="ignore")
                parsed = json.loads(content)
                if isinstance(parsed, list):
                    df = pd.DataFrame(parsed)
                elif isinstance(parsed, dict):
                    # Find first list value or normalize
                    first_list = next((v for v in parsed.values() if isinstance(v, list)), None)
                    if first_list:
                        df = pd.DataFrame(first_list)
                    else:
                        df = pd.DataFrame([parsed])

        if df is None or df.empty:
            return False, None, "The uploaded file contains no data or could not be decoded."
            
        # Clean column names of leading/trailing whitespace
        df.columns = [str(c).strip() for c in df.columns]
        
        return True, df, f"Successfully loaded {len(df):,} rows and {len(df.columns)} columns."
        
    except Exception as e:
        return False, None, f"Error reading file '{filename}': {str(e)}"


def export_dataframe_bytes(df: pd.DataFrame, file_format: str) -> bytes:
    """Serializes a DataFrame to bytes for download."""
    if df is None:
        return b""
        
    fmt = file_format.lower().replace(".", "")
    if fmt == "csv":
        return df.to_csv(index=False).encode("utf-8")
    elif fmt in ["xlsx", "excel"]:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="DataFix_Cleaned")
        return buf.getvalue()
    elif fmt == "json":
        return df.to_json(orient="records", indent=2, date_format="iso").encode("utf-8")
    else:
        raise ValueError(f"Unsupported export format: {file_format}")
