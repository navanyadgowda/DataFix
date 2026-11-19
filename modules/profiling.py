"""
DataFix - Data Profiling Module
Comprehensive statistical profiling, missingness breakdown, cardinality, and distribution analysis.
"""

import streamlit as st
import pandas as pd
import numpy as np
try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
from typing import Dict, Any
from utils.helpers import clean_numeric_string, try_parse_date


def compute_column_profile(df: pd.DataFrame) -> pd.DataFrame:
    """Computes structural and statistical metrics for each column in the dataframe."""
    profile_rows = []
    total_rows = len(df)
    
    for col in df.columns:
        series = df[col]
        dtype = str(series.dtype)
        
        # Missing and blank detection
        null_count = int(series.isna().sum())
        blank_count = int(series.astype(str).str.strip().eq("").sum()) if dtype == "object" else 0
        effective_missing = null_count + blank_count
        missing_pct = round((effective_missing / total_rows) * 100, 2) if total_rows > 0 else 0
        
        # Distinct values
        n_unique = int(series.nunique(dropna=True))
        cardinality_pct = round((n_unique / total_rows) * 100, 2) if total_rows > 0 else 0
        
        # Inferred semantic type
        inferred_type = dtype
        if pd.api.types.is_numeric_dtype(series):
            inferred_type = "Numeric"
        elif pd.api.types.is_datetime64_any_dtype(series):
            inferred_type = "Datetime"
        else:
            # Check if strings are parseable dates or numeric
            sample_non_null = series.dropna().astype(str).str.strip()
            if len(sample_non_null) > 0:
                sample = sample_non_null.head(20)
                parsed_dates = [try_parse_date(v)[0] for v in sample]
                parsed_nums = [clean_numeric_string(v)[0] for v in sample]
                
                if sum(parsed_dates) / len(sample) >= 0.7:
                    inferred_type = "Date (String)"
                elif sum(parsed_nums) / len(sample) >= 0.7:
                    inferred_type = "Numeric (String/Symbol)"
                else:
                    inferred_type = "Categorical / Text"
            else:
                inferred_type = "Empty / Unspecified"
                
        profile_rows.append({
            "Column Name": col,
            "Storage Type": dtype,
            "Inferred Type": inferred_type,
            "Total Rows": total_rows,
            "Missing Count": effective_missing,
            "Missing %": missing_pct,
            "Unique Values": n_unique,
            "Cardinality %": cardinality_pct
        })
        
    return pd.DataFrame(profile_rows)


def render_profiling_page():
    """Renders the interactive Data Profiling dashboard."""
    if st.session_state.get("working_df") is None:
        st.info("Please upload or select a dataset first in the 'Upload Dataset' tab.")
        return
        
    df = st.session_state["working_df"]
    
    st.markdown("""
    <div class="datafix-card">
        <h2 style="color: #0B192C; margin-bottom: 0.25rem;">Data Profiling & Statistical Diagnostics</h2>
        <p style="color: #64748B; font-size: 0.95rem;">
            Deep architectural analysis of column distributions, missing value concentrations, data type inferences, and cardinality metrics.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # 1. Column Overview Table
    profile_df = compute_column_profile(df)
    
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        # Missing values bar chart
        missing_subset = profile_df[profile_df["Missing %"] > 0].sort_values("Missing %", ascending=False)
        if not missing_subset.empty:
            if PLOTLY_AVAILABLE:
                fig_missing = px.bar(
                    missing_subset,
                    x="Column Name",
                    y="Missing %",
                    title="Missing Value Distribution by Column (%)",
                    color="Missing %",
                    color_continuous_scale="Reds",
                    text="Missing %"
                )
                fig_missing.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
                st.plotly_chart(fig_missing, use_container_width=True)
            else:
                st.markdown("**Missing Value Distribution by Column (%)**")
                st.bar_chart(missing_subset.set_index("Column Name")["Missing %"])
        else:
            st.success("No missing or blank values detected across any column!")
            
    with col_chart2:
        # Inferred data types donut chart
        type_counts = profile_df["Inferred Type"].value_counts().reset_index()
        type_counts.columns = ["Inferred Type", "Count"]
        if PLOTLY_AVAILABLE:
            fig_types = px.pie(
                type_counts,
                names="Inferred Type",
                values="Count",
                title="Column Semantic Data Types",
                hole=0.45,
                color_discrete_sequence=["#00ADB5", "#1E3E62", "#0B192C", "#F59E0B", "#10B981"]
            )
            fig_types.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_types, use_container_width=True)
        else:
            st.markdown("**Column Semantic Data Types**")
            st.bar_chart(type_counts.set_index("Inferred Type")["Count"])
        
    st.subheader("Column Structural Profile Summary")
    st.dataframe(profile_df, use_container_width=True)
    
    st.markdown("<hr style='margin: 2rem 0; border-color: #E2E8F0;' />", unsafe_allow_html=True)
    st.subheader("Deep Column Inspector")
    
    selected_col = st.selectbox("Select column to inspect:", options=df.columns)
    if selected_col:
        series = df[selected_col]
        ic1, ic2 = st.columns([1, 1])
        
        with ic1:
            st.markdown(f"**Quick Stats for `{selected_col}`**")
            nulls = int(series.isna().sum())
            uniques = int(series.nunique(dropna=True))
            
            stat_dict = {
                "Metric": ["Storage dtype", "Null Count", "Distinct Values", "Top Value", "Top Frequency"],
                "Value": [
                    str(series.dtype),
                    f"{nulls} ({round(nulls/len(df)*100, 1)}%)",
                    str(uniques),
                    str(series.mode().iloc[0]) if not series.mode().empty else "N/A",
                    str(int((series == series.mode().iloc[0]).sum())) if not series.mode().empty else "N/A"
                ]
            }
            
            # Numeric descriptive statistics if applicable
            numeric_vals = pd.to_numeric(series, errors="coerce").dropna()
            if len(numeric_vals) > 0 and len(numeric_vals) / max(len(series.dropna()), 1) > 0.5:
                stat_dict["Metric"].extend(["Mean", "Std Dev", "Min", "Median", "Max"])
                stat_dict["Value"].extend([
                    f"{numeric_vals.mean():,.2f}",
                    f"{numeric_vals.std():,.2f}",
                    f"{numeric_vals.min():,.2f}",
                    f"{numeric_vals.median():,.2f}",
                    f"{numeric_vals.max():,.2f}"
                ])
                
            st.table(pd.DataFrame(stat_dict))
            
        with ic2:
            st.markdown(f"**Value Distribution for `{selected_col}`**")
            val_counts = series.value_counts(dropna=False).head(10).reset_index()
            val_counts.columns = ["Value", "Frequency"]
            val_counts["Value"] = val_counts["Value"].astype(str)
            
            if PLOTLY_AVAILABLE:
                fig_bar = px.bar(
                    val_counts,
                    x="Frequency",
                    y="Value",
                    orientation="h",
                    title=f"Top 10 Values in '{selected_col}'",
                    color="Frequency",
                    color_continuous_scale="Blues"
                )
                fig_bar.update_layout(yaxis=dict(autorange="reversed"), height=300, margin=dict(l=20, r=20, t=40, b=20))
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.bar_chart(val_counts.set_index("Value")["Frequency"])
