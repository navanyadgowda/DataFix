"""
DataFix – Autonomous Data Quality and Repair Engine
Main Application Entry Point (Streamlit Dashboard)
"""

import os
import json
import streamlit as st
import pandas as pd
try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# Set page configuration must be the first Streamlit command
st.set_page_config(
    page_title="DataFix – Autonomous Data Quality & Repair Engine",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import internal modules
from config import (
    APP_NAME, APP_SUBTITLE, APP_VERSION, APP_DESCRIPTION,
    THEME_COLORS, CONFIDENCE_AUTO_REPAIR_THRESHOLD,
    SEVERITY_CRITICAL, SEVERITY_HIGH, SEVERITY_MEDIUM, SEVERITY_LOW
)
from utils.helpers import get_severity_badge_html, get_confidence_badge_html
from utils.data_integrity import verify_dataset_immutability
from utils.file_handler import export_dataframe_bytes
from modules.upload import render_upload_page, initialize_session_state, set_dataset, SAMPLE_DATASETS
from modules.profiling import render_profiling_page
from modules.detection import DataQualityDetector
from modules.diagnosis import RootCauseDiagnosticEngine
from modules.repair import DataRepairEngine
from modules.validation import ValidationEngine
from modules.explainability import ExplainabilityEngine
from modules.audit import AuditTracker
from modules.quality_score import compute_quality_score
from modules.export import generate_executive_html_report


def load_custom_css():
    """Loads external CSS stylesheet."""
    css_path = os.path.join(os.path.dirname(__file__), "assets", "styles.css")
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def ensure_analysis_pipeline():
    """Runs automated detection, diagnosis, and quality scoring if not already cached."""
    df = st.session_state.get("working_df")
    if df is not None:
        if not st.session_state.get("detected_issues"):
            detector = DataQualityDetector(df)
            issues = detector.detect_all()
            st.session_state["detected_issues"] = issues
            
            # Diagnosis
            diag_engine = RootCauseDiagnosticEngine(issues, df)
            st.session_state["diagnoses"] = diag_engine.diagnose_all()
            
            # Pre-repair quality score
            score_data = compute_quality_score(st.session_state["original_df"], issues)
            st.session_state["quality_score_pre"] = score_data
            
            # Run validation baseline
            val_engine = ValidationEngine(
                st.session_state["original_df"],
                st.session_state["working_df"],
                st.session_state["detected_issues"],
                st.session_state["audit_log"]
            )
            st.session_state["validation_report"] = val_engine.validate()


def main():
    initialize_session_state()
    load_custom_css()

    # --- SIDEBAR NAVIGATION ---
    with st.sidebar:
        st.markdown(f"""
        <div style="padding: 0.5rem 0 1rem 0;">
            <div style="font-size: 1.6rem; font-weight: 800; color: #FFFFFF; letter-spacing: -0.5px;">
                🛡️ {APP_NAME}
            </div>
            <div style="font-size: 0.8rem; color: #00ADB5; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">
                {APP_SUBTITLE}
            </div>
            <div style="font-size: 0.75rem; color: #94A3B8; margin-top: 2px;">
                v{APP_VERSION} · Trust & Integrity Engine
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Dataset Status Indicator
        if st.session_state.get("working_df") is not None:
            df = st.session_state["working_df"]
            is_valid_hash = verify_dataset_immutability(
                st.session_state["original_df"], 
                st.session_state["original_hash"]
            )
            st.markdown(f"""
            <div style="background: rgba(255,255,255,0.06); padding: 0.75rem; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); margin-bottom: 1.25rem;">
                <div style="font-size: 0.75rem; color: #94A3B8; text-transform: uppercase; font-weight: 700;">Active Dataset</div>
                <div style="font-size: 0.9rem; font-weight: 700; color: #FFFFFF; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                    📄 {st.session_state.get('current_filename', 'dataset.csv')}
                </div>
                <div style="font-size: 0.75rem; color: #CBD5E1; margin-top: 4px;">
                    {len(df):,} rows · {len(df.columns)} cols
                </div>
                <div style="font-size: 0.72rem; color: {'#10B981' if is_valid_hash else '#EF4444'}; margin-top: 4px; font-weight: 600;">
                    {'🔒 Original Hash Locked' if is_valid_hash else '⚠️ Hash Integrity Warning'}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background: rgba(255,255,255,0.04); padding: 0.75rem; border-radius: 8px; border: 1px dashed rgba(255,255,255,0.2); margin-bottom: 1.25rem; text-align: center;">
                <div style="font-size: 0.8rem; color: #94A3B8;">No dataset ingested yet</div>
            </div>
            """, unsafe_allow_html=True)

        pages = [
            "Overview Dashboard",
            "Upload Dataset",
            "Data Profiling",
            "Issue Detection",
            "AI Diagnosis",
            "Smart Repair Center",
            "Validation Center",
            "Explainability & Audit",
            "Export Center"
        ]
        
        selected_page = st.radio(
            "Navigation",
            pages,
            index=pages.index(st.session_state.get("active_page", "Overview Dashboard")),
            label_visibility="collapsed"
        )
        st.session_state["active_page"] = selected_page

        st.markdown("<hr style='border-color: rgba(255,255,255,0.1); margin: 1.5rem 0;' />", unsafe_allow_html=True)
        st.caption("Engine Principle:")
        st.info("Build for trust: Prove what changed, why it changed, and how it was validated.")

    # Run analysis pipeline if data is loaded
    if st.session_state.get("working_df") is not None:
        ensure_analysis_pipeline()

    # --- ROUTING TO PAGES ---

    # 1. OVERVIEW DASHBOARD
    if selected_page == "Overview Dashboard":
        render_overview_page()

    # 2. UPLOAD DATASET
    elif selected_page == "Upload Dataset":
        render_upload_page()

    # 3. DATA PROFILING
    elif selected_page == "Data Profiling":
        render_profiling_page()

    # 4. ISSUE DETECTION
    elif selected_page == "Issue Detection":
        render_detection_page()

    # 5. AI DIAGNOSIS
    elif selected_page == "AI Diagnosis":
        render_diagnosis_page()

    # 6. SMART REPAIR CENTER
    elif selected_page == "Smart Repair Center":
        render_repair_page()

    # 7. VALIDATION CENTER
    elif selected_page == "Validation Center":
        render_validation_page()

    # 8. EXPLAINABILITY & AUDIT
    elif selected_page == "Explainability & Audit":
        render_audit_page()

    # 9. EXPORT CENTER
    elif selected_page == "Export Center":
        render_export_page()


# ==============================================================================
# PAGE 1: OVERVIEW DASHBOARD
# ==============================================================================
def render_overview_page():
    st.markdown("""
    <div class="hero-banner">
        <span class="hero-badge">Autonomous Trust & Quality Engine</span>
        <h1>DataFix Operations Command</h1>
        <p>
            Autonomous end-to-end data quality detection, root cause diagnosis, conservative safe repair,
            transparent explainability, and multi-dimensional validation.
        </p>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.get("working_df") is None:
        st.markdown("""
        <div class="datafix-card" style="text-align: center; padding: 3rem 1.5rem;">
            <h3 style="color: #0B192C;">Welcome to DataFix</h3>
            <p style="color: #64748B; max-width: 600px; margin: 0 auto 1.5rem auto;">
                To begin autonomous defect scanning, root-cause diagnosis, and safe repairs, please upload a dataset or choose one of our pre-configured sample datasets.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("📊 Load Customer Sample", use_container_width=True):
                load_sample_dataset_helper("sample_data/sample_customers.csv", "sample_customers.csv")
        with c2:
            if st.button("🛒 Load Sales Orders Sample", use_container_width=True):
                load_sample_dataset_helper("sample_data/sample_sales.csv", "sample_sales.csv")
        with c3:
            if st.button("👥 Load Employee HR Sample", use_container_width=True):
                load_sample_dataset_helper("sample_data/sample_employees.csv", "sample_employees.csv")
        return

    df = st.session_state["working_df"]
    issues = st.session_state.get("detected_issues", [])
    diagnoses = st.session_state.get("diagnoses", [])
    audit_log = st.session_state.get("audit_log", [])
    val_report = st.session_state.get("validation_report", {})
    score_data = st.session_state.get("quality_score_pre") or compute_quality_score(df, issues)
    
    # Critical issues count
    crit_count = sum(1 for iss in issues if iss.get("severity") == SEVERITY_CRITICAL)
    
    # 6 Top Metric Cards
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    with m1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-val">{len(df):,}</div>
            <div class="stat-label">Total Records</div>
            <div class="stat-sub">{len(df.columns)} Columns</div>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-val" style="color: {'#EF4444' if len(issues) > 0 else '#10B981'};">{len(issues):,}</div>
            <div class="stat-label">Issues Found</div>
            <div class="stat-sub">{sum(i.get('count',0) for i in issues):,} Affected Cells</div>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-val" style="color: {'#EF4444' if crit_count > 0 else '#10B981'};">{crit_count}</div>
            <div class="stat-label">Critical Alerts</div>
            <div class="stat-sub">Logic & Temporal</div>
        </div>
        """, unsafe_allow_html=True)
    with m4:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-val" style="color: #00ADB5;">{len(diagnoses)}</div>
            <div class="stat-label">Root Causes</div>
            <div class="stat-sub">Explainable Patterns</div>
        </div>
        """, unsafe_allow_html=True)
    with m5:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-val" style="color: #10B981;">{len(audit_log):,}</div>
            <div class="stat-label">Repairs Applied</div>
            <div class="stat-sub">100% Audited</div>
        </div>
        """, unsafe_allow_html=True)
    with m6:
        overall_score = val_report.get("post_score", score_data.get("overall_score", 0.0))
        score_color = "#10B981" if overall_score >= 85 else ("#F59E0B" if overall_score >= 65 else "#EF4444")
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-val" style="color: {score_color};">{overall_score:.1f}</div>
            <div class="stat-label">Quality Index</div>
            <div class="stat-sub">Scale 0 - 100</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br/>", unsafe_allow_html=True)

    # Visual Analytics Grid
    col_chart1, col_chart2 = st.columns([1, 1])

    with col_chart1:
        st.subheader("Data Quality Dimensional Radar")
        dims = score_data.get("dimensions", {})
        if dims:
            if PLOTLY_AVAILABLE:
                categories = list(dims.keys())
                scores = [dims[k]["score"] for k in categories]
                
                fig_radar = go.Figure()
                fig_radar.add_trace(go.Scatterpolar(
                    r=scores,
                    theta=categories,
                    fill='toself',
                    fillcolor='rgba(0, 173, 181, 0.25)',
                    line=dict(color='#00ADB5', width=2),
                    name='Pre-Repair'
                ))
                
                # If post repair exists, show comparison trace
                if val_report and val_report.get("post_dimensions"):
                    post_dims = val_report["post_dimensions"]
                    post_scores = [post_dims[k]["score"] for k in categories]
                    fig_radar.add_trace(go.Scatterpolar(
                        r=post_scores,
                        theta=categories,
                        fill='toself',
                        fillcolor='rgba(16, 185, 129, 0.2)',
                        line=dict(color='#10B981', width=2),
                        name='Post-Repair'
                    ))

                fig_radar.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                    showlegend=True,
                    height=340,
                    margin=dict(l=40, r=40, t=20, b=20)
                )
                st.plotly_chart(fig_radar, use_container_width=True)
            else:
                for dim_name, dinfo in dims.items():
                    sc = dinfo["score"]
                    st.write(f"**{dim_name}**: `{sc:.1f}/100` ({dinfo.get('weight', '')})")
                    st.progress(min(1.0, max(0.0, sc / 100.0)))

    with col_chart2:
        st.subheader("Detected Issues by Category")
        if issues:
            cat_df = pd.DataFrame([{"Category": iss["category"], "Count": iss["count"]} for iss in issues])
            cat_grouped = cat_df.groupby("Category").sum().reset_index().sort_values("Count", ascending=True)
            
            if PLOTLY_AVAILABLE:
                fig_cat = px.bar(
                    cat_grouped,
                    x="Count",
                    y="Category",
                    orientation="h",
                    color="Count",
                    color_continuous_scale="Tealgrn",
                    text="Count"
                )
                fig_cat.update_layout(height=340, margin=dict(l=20, r=20, t=20, b=20))
                st.plotly_chart(fig_cat, use_container_width=True)
            else:
                st.bar_chart(cat_grouped.set_index("Category")["Count"])
        else:
            st.success("No issues detected! Dataset is completely clean.")

    # High-Priority Call to Action
    st.markdown("<hr style='margin: 1.5rem 0; border-color: #E2E8F0;' />", unsafe_allow_html=True)
    quick_col1, quick_col2, quick_col3 = st.columns(3)
    with quick_col1:
        if st.button("🔍 Inspect All Issues", use_container_width=True, type="secondary"):
            st.session_state["active_page"] = "Issue Detection"
            st.rerun()
    with quick_col2:
        if st.button("🧠 View AI Root Cause Diagnosis", use_container_width=True, type="secondary"):
            st.session_state["active_page"] = "AI Diagnosis"
            st.rerun()
    with quick_col3:
        if st.button("⚡ Open Smart Repair Center", use_container_width=True, type="primary"):
            st.session_state["active_page"] = "Smart Repair Center"
            st.rerun()


def load_sample_dataset_helper(path: str, filename: str):
    """Loads a sample dataset directly into session state."""
    from utils.file_handler import load_dataset, get_file_info
    with open(path, "rb") as f:
        meta = get_file_info(f, filename)
        success, df, msg = load_dataset(path, filename)
        if success:
            set_dataset(df, filename, meta)
            st.rerun()


# ==============================================================================
# PAGE 4: ISSUE DETECTION
# ==============================================================================
def render_detection_page():
    if st.session_state.get("working_df") is None:
        st.info("Please upload or select a dataset first.")
        return

    issues = st.session_state.get("detected_issues", [])
    
    st.markdown("""
    <div class="datafix-card">
        <h2 style="color: #0B192C; margin-bottom: 0.25rem;">Automated Defect & Quality Issue Detection</h2>
        <p style="color: #64748B; font-size: 0.95rem;">
            Exhaustive scanning across 10 defect vectors including regex validation, schema checks,
            duplicate fingerprints, statistical IQR fences, and cross-column arithmetic logic.
        </p>
    </div>
    """, unsafe_allow_html=True)

    if not issues:
        st.success("🎉 No data quality issues were detected in this dataset!")
        return

    # Filter controls
    f_col1, f_col2, f_col3 = st.columns([1, 1, 2])
    with f_col1:
        categories = ["All Categories"] + sorted(list(set(iss["category"] for iss in issues)))
        selected_cat = st.selectbox("Filter Category:", categories)
    with f_col2:
        severities = ["All Severities", SEVERITY_CRITICAL, SEVERITY_HIGH, SEVERITY_MEDIUM, SEVERITY_LOW]
        selected_sev = st.selectbox("Filter Severity:", severities)
    with f_col3:
        search_query = st.text_input("Search issues (column, evidence, ID):", "")

    # Apply filters
    filtered_issues = issues
    if selected_cat != "All Categories":
        filtered_issues = [i for i in filtered_issues if i["category"] == selected_cat]
    if selected_sev != "All Severities":
        filtered_issues = [i for i in filtered_issues if i["severity"] == selected_sev]
    if search_query.strip():
        q = search_query.lower()
        filtered_issues = [
            i for i in filtered_issues 
            if q in i["id"].lower() or q in i["column"].lower() or q in i["evidence"].lower()
        ]

    st.markdown(f"**Showing {len(filtered_issues)} of {len(issues)} detected issue groups:**")

    for iss in filtered_issues:
        sev_badge = get_severity_badge_html(iss["severity"])
        conf_badge = get_confidence_badge_html(iss["confidence"])
        
        with st.expander(f"[{iss['id']}] {iss['category']} — Column: '{iss['column']}' ({iss['count']} occurrences)"):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"**Evidence:** {iss['evidence']}")
                st.markdown(f"**Recommended Repair:** `{iss['repair_recommended']}`")
                st.markdown(f"**Affected Rows:** {iss['affected_rows'][:15]}{'...' if len(iss['affected_rows']) > 15 else ''}")
            with c2:
                st.markdown(f"**Severity:** {sev_badge}", unsafe_allow_html=True)
                st.markdown(f"**Confidence:** {conf_badge}", unsafe_allow_html=True)
                st.markdown(f"**Defect Count:** `{iss['count']}`")


# ==============================================================================
# PAGE 5: AI ROOT CAUSE DIAGNOSIS
# ==============================================================================
def render_diagnosis_page():
    if st.session_state.get("working_df") is None:
        st.info("Please upload or select a dataset first.")
        return

    diagnoses = st.session_state.get("diagnoses", [])
    
    st.markdown("""
    <div class="datafix-card">
        <h2 style="color: #0B192C; margin-bottom: 0.25rem;">Intelligent Root Cause Diagnostic Engine</h2>
        <p style="color: #64748B; font-size: 0.95rem;">
            Heuristic clustering and statistical pattern synthesis inferring upstream origins of defects.
            Clearly identifies inferred causes versus ground-truth facts.
        </p>
    </div>
    """, unsafe_allow_html=True)

    if not diagnoses:
        st.success("No systemic defect patterns detected.")
        return

    for diag in diagnoses:
        conf_pct = int(diag["confidence"] * 100)
        st.markdown(f"""
        <div class="datafix-card" style="border-left: 4px solid #00ADB5;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                <h3 style="margin: 0; color: #0B192C; font-size: 1.15rem;">
                    🔍 [{diag['id']}] {diag['title']}
                </h3>
                <span style="background: #E0F2FE; color: #0284C7; padding: 4px 10px; border-radius: 12px; font-weight: 700; font-size: 0.75rem;">
                    {diag['inference_type']} · {conf_pct}% Confidence
                </span>
            </div>
            <div style="font-size: 0.825rem; color: #64748B; margin-bottom: 0.75rem;">
                <strong>Domain:</strong> {diag['category']} | <strong>Affected Records:</strong> {diag['affected_records']}
            </div>
            <p style="font-size: 0.925rem; color: #1E293B; line-height: 1.5; margin-bottom: 0.6rem;">
                <strong>Inferred Root Cause:</strong> {diag['probable_root_cause']}
            </p>
            <p style="font-size: 0.875rem; color: #DC2626; margin-bottom: 0.6rem;">
                <strong>Systemic Impact:</strong> {diag['impact']}
            </p>
            <p style="font-size: 0.875rem; color: #059669; margin-bottom: 0;">
                <strong>Strategic Recommendation:</strong> {diag['recommended_action']}
            </p>
        </div>
        """, unsafe_allow_html=True)


# ==============================================================================
# PAGE 6: SMART REPAIR CENTER
# ==============================================================================
def render_repair_page():
    if st.session_state.get("working_df") is None:
        st.info("Please upload or select a dataset first.")
        return

    df = st.session_state["working_df"]
    issues = st.session_state.get("detected_issues", [])
    
    st.markdown("""
    <div class="datafix-card">
        <h2 style="color: #0B192C; margin-bottom: 0.25rem;">Autonomous & Controlled Smart Repair Center</h2>
        <p style="color: #64748B; font-size: 0.95rem;">
            Inspect candidate corrections, execute safe autonomous repairs (≥85% confidence),
            approve individual patches, or perform non-destructive state rollbacks.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Generate candidate proposals
    repair_engine = DataRepairEngine(df, issues)
    proposals = repair_engine.generate_repair_proposals()
    
    safe_proposals = [p for p in proposals if p.get("is_safe_auto")]
    manual_proposals = [p for p in proposals if not p.get("is_safe_auto")]

    # Action Toolbar
    act_col1, act_col2, act_col3 = st.columns([2, 1, 1])
    
    with act_col1:
        if safe_proposals:
            if st.button(
                f"⚡ Execute Safe Auto-Repair ({len(safe_proposals)} High-Confidence Repairs)",
                type="primary",
                use_container_width=True
            ):
                with st.spinner("Applying safe non-destructive repairs..."):
                    # Save undo snapshot first
                    AuditTracker.push_undo_snapshot(
                        st.session_state["undo_stack"],
                        st.session_state["working_df"],
                        len(st.session_state["audit_log"])
                    )
                    
                    new_df, logs = DataRepairEngine.apply_batch_repairs(df, safe_proposals)
                    st.session_state["working_df"] = new_df
                    st.session_state["audit_log"].extend(logs)
                    
                    # Refresh issues and validation
                    new_detector = DataQualityDetector(new_df)
                    st.session_state["detected_issues"] = new_detector.detect_all()
                    val_eng = ValidationEngine(
                        st.session_state["original_df"],
                        new_df,
                        st.session_state["detected_issues"],
                        st.session_state["audit_log"]
                    )
                    st.session_state["validation_report"] = val_eng.validate()
                    st.success(f"Successfully applied {len(logs)} certified repairs!")
                    st.rerun()
        else:
            st.info("No pending safe auto-repairs. All high-confidence defects are already resolved.")

    with act_col2:
        undo_available = len(st.session_state.get("undo_stack", [])) > 0
        if st.button("↩️ Undo Last Repair", disabled=not undo_available, use_container_width=True):
            restored_df, restored_log = AuditTracker.pop_undo_snapshot(
                st.session_state["undo_stack"],
                st.session_state["audit_log"]
            )
            if restored_df is not None:
                st.session_state["working_df"] = restored_df
                st.session_state["audit_log"] = restored_log
                # Refresh
                detector = DataQualityDetector(restored_df)
                st.session_state["detected_issues"] = detector.detect_all()
                st.success("Successfully rolled back to previous state.")
                st.rerun()

    with act_col3:
        if st.button("🔄 Revert to Immutable Original", use_container_width=True):
            st.session_state["working_df"] = st.session_state["original_df"].copy(deep=True)
            st.session_state["audit_log"] = []
            st.session_state["undo_stack"] = []
            detector = DataQualityDetector(st.session_state["working_df"])
            st.session_state["detected_issues"] = detector.detect_all()
            st.warning("Reverted dataset to 100% original baseline.")
            st.rerun()

    st.markdown("<hr style='margin: 1.5rem 0; border-color: #E2E8F0;' />", unsafe_allow_html=True)
    
    tab_auto, tab_manual = st.tabs([
        f"Safe Candidates ({len(safe_proposals)})", 
        f"User-Review Required ({len(manual_proposals)})"
    ])

    with tab_auto:
        if not safe_proposals:
            st.success("All safe repairs have been applied!")
        else:
            st.caption("These repairs have confidence ≥ 85%, use explainable transformations, and are completely reversible.")
            render_proposal_table(safe_proposals, df)

    with tab_manual:
        if not manual_proposals:
            st.info("No repairs require manual review.")
        else:
            st.caption("These actions involve statistical capping or subjective domain corrections requiring explicit human authorization.")
            for p in manual_proposals:
                with st.container():
                    c1, c2, c3 = st.columns([3, 1, 1])
                    with c1:
                        st.markdown(f"**Row {p['row_index']} · Col '{p['column']}'**: `{p['original_value']}` → `{p['proposed_value']}`")
                        st.caption(p["reason"])
                    with c2:
                        st.markdown(get_confidence_badge_html(p["confidence"]), unsafe_allow_html=True)
                    with c3:
                        if st.button(f"Approve", key=f"btn_app_{p['proposal_id']}"):
                            AuditTracker.push_undo_snapshot(
                                st.session_state["undo_stack"],
                                st.session_state["working_df"],
                                len(st.session_state["audit_log"])
                            )
                            new_df, log_entry = DataRepairEngine.apply_single_repair(df, p)
                            st.session_state["working_df"] = new_df
                            st.session_state["audit_log"].append(log_entry)
                            # Re-detect
                            detector = DataQualityDetector(new_df)
                            st.session_state["detected_issues"] = detector.detect_all()
                            st.success(f"Applied repair {p['proposal_id']}")
                            st.rerun()


def render_proposal_table(proposals: list, df: pd.DataFrame):
    """Renders candidate repair proposals in a clean structured table."""
    table_data = []
    for p in proposals[:50]:
        table_data.append({
            "ID": p["proposal_id"],
            "Row": p["row_index"],
            "Column": p["column"],
            "Original Value": str(p["original_value"]),
            "Proposed Value": str(p["proposed_value"]),
            "Method": p["repair_method"],
            "Confidence": f"{int(p['confidence']*100)}%",
            "Reason": p["reason"]
        })
    st.dataframe(pd.DataFrame(table_data), use_container_width=True)


# ==============================================================================
# PAGE 7: VALIDATION CENTER
# ==============================================================================
def render_validation_page():
    if st.session_state.get("working_df") is None:
        st.info("Please upload or select a dataset first.")
        return

    val_report = st.session_state.get("validation_report")
    if not val_report:
        val_eng = ValidationEngine(
            st.session_state["original_df"],
            st.session_state["working_df"],
            st.session_state["detected_issues"],
            st.session_state["audit_log"]
        )
        val_report = val_eng.validate()
        st.session_state["validation_report"] = val_report

    st.markdown("""
    <div class="datafix-card">
        <h2 style="color: #0B192C; margin-bottom: 0.25rem;">Post-Repair Validation & Integrity Verification</h2>
        <p style="color: #64748B; font-size: 0.95rem;">
            Exhaustive verification of pre- vs post-repair quality metrics, schema preservation,
            unintended change invariance, and residual defects.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Certification Banner
    status = val_report.get("status", "PASS")
    status_color = "#10B981" if status == "PASS" else ("#F59E0B" if status == "WARNING" else "#EF4444")
    
    st.markdown(f"""
    <div style="background: #FFFFFF; border-left: 6px solid {status_color}; border-radius: 8px; padding: 1.25rem; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 1.5rem;">
        <div style="font-size: 0.8rem; font-weight: 700; color: {status_color}; text-transform: uppercase;">
            Validation Status: {status} ({val_report.get('certification_code')})
        </div>
        <div style="font-size: 1.15rem; font-weight: 700; color: #0B192C; margin: 0.25rem 0;">
            {val_report.get('summary_message')}
        </div>
        <div style="font-size: 0.85rem; color: #64748B;">
            Pre-repair Quality: <strong>{val_report.get('pre_score'):.1f}</strong> → Post-repair Quality: <strong>{val_report.get('post_score'):.1f}</strong> (Improvement: <strong>+{val_report.get('score_delta'):.1f} pts</strong>)
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 4 Validation Verification Checks
    vc1, vc2, vc3, vc4 = st.columns(4)
    with vc1:
        preserved = val_report.get("schema_check", {}).get("preserved", False)
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-val" style="color: {'#10B981' if preserved else '#EF4444'};">{'PASS' if preserved else 'FAIL'}</div>
            <div class="stat-label">Schema Preservation</div>
            <div class="stat-sub">{val_report.get('col_count_after')} / {val_report.get('col_count_before')} Columns Intact</div>
        </div>
        """, unsafe_allow_html=True)
    with vc2:
        verified = val_report.get("invariance_check", {}).get("verified", False)
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-val" style="color: {'#10B981' if verified else '#EF4444'};">{'PASS' if verified else 'FAIL'}</div>
            <div class="stat-label">Cell Invariance</div>
            <div class="stat-sub">Zero Unlogged Changes</div>
        </div>
        """, unsafe_allow_html=True)
    with vc3:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-val" style="color: #00ADB5;">{val_report.get('repairs_applied_count', 0)}</div>
            <div class="stat-label">Repairs Applied</div>
            <div class="stat-sub">100% Audited</div>
        </div>
        """, unsafe_allow_html=True)
    with vc4:
        rem = val_report.get("remaining_issues_count", 0)
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-val" style="color: {'#10B981' if rem == 0 else '#F59E0B'};">{rem}</div>
            <div class="stat-label">Residual Defects</div>
            <div class="stat-sub">Unresolved Issues</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<hr style='margin: 1.5rem 0; border-color: #E2E8F0;' />", unsafe_allow_html=True)
    
    # Pre vs Post Score Dimension Comparison Table
    st.subheader("Dimensional Quality Score Comparison")
    pre_d = val_report.get("pre_dimensions", {})
    post_d = val_report.get("post_dimensions", {})
    
    comparison_rows = []
    for dim_name in pre_d:
        s_pre = pre_d[dim_name]["score"]
        s_post = post_d.get(dim_name, {}).get("score", s_pre)
        delta = round(s_post - s_pre, 1)
        comparison_rows.append({
            "Dimension": dim_name,
            "Weight": pre_d[dim_name]["weight"],
            "Pre-Repair Score": f"{s_pre:.1f}",
            "Post-Repair Score": f"{s_post:.1f}",
            "Change (Delta)": f"{'+' if delta >= 0 else ''}{delta:.1f} pts",
            "Initial Defects": pre_d[dim_name]["defect_count"],
            "Remaining Defects": post_d.get(dim_name, {}).get("defect_count", 0)
        })
    st.dataframe(pd.DataFrame(comparison_rows), use_container_width=True)


# ==============================================================================
# PAGE 8: EXPLAINABILITY & AUDIT
# ==============================================================================
def render_audit_page():
    audit_log = st.session_state.get("audit_log", [])
    
    st.markdown("""
    <div class="datafix-card">
        <h2 style="color: #0B192C; margin-bottom: 0.25rem;">Explainability & Modification Audit Ledger</h2>
        <p style="color: #64748B; font-size: 0.95rem;">
            Full provenance tracking. Every modification records the exact cell coordinates, original value,
            new value, repair algorithm, confidence, and human-readable explanation.
        </p>
    </div>
    """, unsafe_allow_html=True)

    if not audit_log:
        st.info("No modifications have been applied yet. Run repairs in the Smart Repair Center to generate audit records.")
        return

    # Column Summary Breakdown
    st.subheader("Modifications Summary by Column")
    summary_df = ExplainabilityEngine.summarize_modifications_by_column(audit_log)
    st.dataframe(summary_df, use_container_width=True)

    st.markdown("<br/>", unsafe_allow_html=True)
    st.subheader(f"Complete Transaction Audit History ({len(audit_log)} Operations)")
    
    audit_df = AuditTracker.get_audit_dataframe(audit_log)
    st.dataframe(audit_df, use_container_width=True)

    st.markdown("<hr style='margin: 1.5rem 0; border-color: #E2E8F0;' />", unsafe_allow_html=True)
    st.subheader("Deep Explainability Card Inspector")
    
    # Inspector for a chosen audit record
    selected_idx = st.selectbox(
        "Select transaction to inspect:",
        options=range(len(audit_log)),
        format_func=lambda i: f"#{i+1}: Row {audit_log[i].get('row_index')} | Col '{audit_log[i].get('column')}' ({audit_log[i].get('repair_method')})"
    )
    if selected_idx is not None and selected_idx < len(audit_log):
        entry = audit_log[selected_idx]
        exp = ExplainabilityEngine.generate_detailed_explanation(entry)
        
        st.markdown(f"""
        <div class="datafix-card">
            <h4 style="color: #0B192C; margin-top: 0;">{exp['title']}</h4>
            <p style="font-size: 1rem; color: #1E293B; line-height: 1.6;">
                {exp['narrative']}
            </p>
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 1rem; margin-top: 1rem;">
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; font-size: 0.85rem;">
                    <div><strong>Original:</strong> <span class="code-diff-old">{exp['original_value']}</span></div>
                    <div><strong>Repaired:</strong> <span class="code-diff-new">{exp['new_value']}</span></div>
                    <div><strong>Confidence:</strong> {exp['confidence_pct']}</div>
                    <div><strong>Status:</strong> Validated</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ==============================================================================
# PAGE 9: EXPORT CENTER
# ==============================================================================
def render_export_page():
    if st.session_state.get("working_df") is None:
        st.info("Please upload or select a dataset first.")
        return

    df_cleaned = st.session_state["working_df"]
    df_orig = st.session_state["original_df"]
    audit_log = st.session_state.get("audit_log", [])
    val_report = st.session_state.get("validation_report", {})
    score_pre = st.session_state.get("quality_score_pre", {}).get("overall_score", 0.0)
    score_post = val_report.get("post_score", score_pre)
    fname_base = os.path.splitext(st.session_state.get("current_filename", "datafix_dataset"))[0]

    st.markdown("""
    <div class="datafix-card">
        <h2 style="color: #0B192C; margin-bottom: 0.25rem;">Export Center & Artifact Packaging</h2>
        <p style="color: #64748B; font-size: 0.95rem;">
            Export the certified clean dataset in CSV, Excel, or JSON, download complete modification audit logs,
            or export a standalone executive HTML data quality certificate.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.subheader("1. Download Cleaned Dataset")
        st.caption("Cleaned, validated, and normalized data ready for production analytics and machine learning pipelines.")

        # CSV Download
        csv_bytes = export_dataframe_bytes(df_cleaned, "csv")
        st.download_button(
            label="📥 Download Cleaned CSV",
            data=csv_bytes,
            file_name=f"{fname_base}_cleaned.csv",
            mime="text/csv",
            use_container_width=True
        )

        # Excel Download
        try:
            excel_bytes = export_dataframe_bytes(df_cleaned, "xlsx")
            st.download_button(
                label="📥 Download Cleaned Excel (.xlsx)",
                data=excel_bytes,
                file_name=f"{fname_base}_cleaned.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        except Exception:
            pass

        # JSON Download
        json_bytes = export_dataframe_bytes(df_cleaned, "json")
        st.download_button(
            label="📥 Download Cleaned JSON",
            data=json_bytes,
            file_name=f"{fname_base}_cleaned.json",
            mime="application/json",
            use_container_width=True
        )

    with col2:
        st.subheader("2. Quality Certificate & Audit Logs")
        st.caption("Complete provenance artifacts, mathematical justification, and cryptographic verification logs.")

        # Executive HTML Certificate
        html_report = generate_executive_html_report(
            st.session_state.get("current_filename", "dataset"),
            df_orig,
            df_cleaned,
            val_report,
            audit_log,
            score_pre,
            score_post
        )
        st.download_button(
            label="📑 Download Executive Quality Report (HTML)",
            data=html_report.encode("utf-8"),
            file_name=f"{fname_base}_quality_certificate.html",
            mime="text/html",
            type="primary",
            use_container_width=True
        )

        # Audit Log in CSV
        audit_df = AuditTracker.get_audit_dataframe(audit_log)
        st.download_button(
            label="📜 Download Audit Ledger (CSV)",
            data=audit_df.to_csv(index=False).encode("utf-8"),
            file_name=f"{fname_base}_audit_log.csv",
            mime="text/csv",
            use_container_width=True
        )

        # Audit Log in JSON
        st.download_button(
            label="📜 Download Audit Ledger (JSON)",
            data=json.dumps(audit_log, indent=2).encode("utf-8"),
            file_name=f"{fname_base}_audit_log.json",
            mime="application/json",
            use_container_width=True
        )


if __name__ == "__main__":
    main()
