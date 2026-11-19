"""
DataFix - Upload and Ingestion Module
Handles dataset ingestion, sample loading, structural preview, and immutable state initialization.
"""

import os
import streamlit as st
import pandas as pd
from typing import Optional, Tuple
from utils.file_handler import load_dataset, get_file_info
from utils.data_integrity import compute_dataframe_hash, create_safe_working_copy
from config import MAX_PREVIEW_ROWS

SAMPLE_DATASETS = {
    "Customer Demographics & Contacts": "sample_data/sample_customers.csv",
    "E-Commerce Sales Transactions": "sample_data/sample_sales.csv",
    "HR & Staff Records": "sample_data/sample_employees.csv"
}


def initialize_session_state():
    """Initializes standard session state keys if not already present."""
    default_states = {
        "original_df": None,
        "original_hash": "",
        "working_df": None,
        "current_filename": "",
        "file_metadata": {},
        "detected_issues": [],
        "diagnoses": [],
        "audit_log": [],
        "undo_stack": [],
        "quality_score_pre": None,
        "quality_score_post": None,
        "validation_report": None,
        "active_page": "Overview Dashboard"
    }
    for key, val in default_states.items():
        if key not in st.session_state:
            st.session_state[key] = val


def set_dataset(df: pd.DataFrame, filename: str, metadata: dict):
    """Safely registers a loaded dataset, creates the immutable baseline hash, and resets working state."""
    # Ensure standard string column headers
    df.columns = [str(c).strip() for c in df.columns]
    
    st.session_state["original_df"] = df.copy(deep=True)
    st.session_state["original_hash"] = compute_dataframe_hash(df)
    st.session_state["working_df"] = create_safe_working_copy(df)
    st.session_state["current_filename"] = filename
    st.session_state["file_metadata"] = metadata
    
    # Reset processing states
    st.session_state["detected_issues"] = []
    st.session_state["diagnoses"] = []
    st.session_state["audit_log"] = []
    st.session_state["undo_stack"] = []
    st.session_state["quality_score_pre"] = None
    st.session_state["quality_score_post"] = None
    st.session_state["validation_report"] = None


def render_upload_page():
    """Renders the Upload and Ingestion page."""
    initialize_session_state()
    
    st.markdown("""
    <div class="datafix-card">
        <h2 style="color: #0B192C; margin-bottom: 0.25rem;">Data Ingestion & Dataset Selection</h2>
        <p style="color: #64748B; font-size: 0.95rem;">
            Upload your own real-world dataset or select a pre-configured sample dataset loaded with intentional errors for instant demonstration.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1], gap="large")
    
    with col1:
        st.subheader("1. Upload Custom Dataset")
        uploaded_file = st.file_uploader(
            "Upload CSV, XLSX, or JSON",
            type=["csv", "xlsx", "xls", "json"],
            help="Files up to 200MB are supported. Datasets are processed locally with strict immutability guarantees."
        )
        if uploaded_file is not None:
            if st.button("Ingest Uploaded File", key="btn_ingest_custom", type="primary"):
                with st.spinner("Decoding and profiling dataset structure..."):
                    meta = get_file_info(uploaded_file, uploaded_file.name)
                    success, df, msg = load_dataset(uploaded_file, uploaded_file.name)
                    if success:
                        set_dataset(df, uploaded_file.name, meta)
                        st.success(f"Loaded: {msg}")
                        st.rerun()
                    else:
                        st.error(f"Ingestion failed: {msg}")
                        
    with col2:
        st.subheader("2. Quick Load Sample Dataset")
        sample_choice = st.selectbox(
            "Choose a curated dataset with intentional defects:",
            options=list(SAMPLE_DATASETS.keys()),
            index=0
        )
        st.caption("Each sample demonstrates diverse real-world issues: missing values, mixed dates, casing drift, typos, and cross-column logic errors.")
        
        if st.button("Load Selected Sample", key="btn_load_sample", type="secondary"):
            sample_rel_path = SAMPLE_DATASETS[sample_choice]
            if os.path.exists(sample_rel_path):
                with open(sample_rel_path, "rb") as f:
                    fname = os.path.basename(sample_rel_path)
                    meta = get_file_info(f, fname)
                    success, df, msg = load_dataset(sample_rel_path, fname)
                    if success:
                        set_dataset(df, fname, meta)
                        st.success(f"Loaded Sample '{sample_choice}': {msg}")
                        st.rerun()
                    else:
                        st.error(f"Sample load error: {msg}")
            else:
                st.error(f"File '{sample_rel_path}' not found on server.")

    # Dataset Inspection and Preview
    if st.session_state["working_df"] is not None:
        df = st.session_state["working_df"]
        st.markdown("<hr style='margin: 2rem 0; border-color: #E2E8F0;' />", unsafe_allow_html=True)
        st.markdown(f"### Ingested Dataset: `{st.session_state['current_filename']}`")
        
        # Metadata metric cards
        m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
        with m_col1:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-val">{len(df):,}</div>
                <div class="stat-label">Total Rows</div>
            </div>
            """, unsafe_allow_html=True)
        with m_col2:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-val">{len(df.columns)}</div>
                <div class="stat-label">Total Columns</div>
            </div>
            """, unsafe_allow_html=True)
        with m_col3:
            mem_mb = round(df.memory_usage(deep=True).sum() / (1024 * 1024), 2)
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-val">{mem_mb} MB</div>
                <div class="stat-label">Memory Usage</div>
            </div>
            """, unsafe_allow_html=True)
        with m_col4:
            null_count = int(df.isna().sum().sum())
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-val" style="color: {'#EF4444' if null_count > 0 else '#10B981'};">{null_count:,}</div>
                <div class="stat-label">Raw Null Cells</div>
            </div>
            """, unsafe_allow_html=True)
        with m_col5:
            dup_count = int(df.duplicated().sum())
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-val" style="color: {'#EF4444' if dup_count > 0 else '#10B981'};">{dup_count:,}</div>
                <div class="stat-label">Exact Duplicates</div>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown("<br/>", unsafe_allow_html=True)
        st.subheader("Data Preview (First 50 Rows)")
        st.dataframe(df.head(MAX_PREVIEW_ROWS), use_container_width=True)
        
        st.markdown(f"""
        <div class="datafix-callout">
            <strong>Immutable Baseline Secured:</strong> SHA-256 fingerprint 
            <code style="background: #E2E8F0; padding: 2px 6px; border-radius: 4px;">{st.session_state['original_hash'][:16]}...</code>
            recorded. All downstream detection and repair actions operate on an isolated working copy.
        </div>
        """, unsafe_allow_html=True)
