import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io
import json
import re
import html
import os
from datetime import datetime

from utils.data_analyzer import DataAnalyzer
from utils.ai_agent import AIAgent
from utils.report_generator import ReportGenerator
from utils.visualizer import Visualizer
from utils.data_quality import evaluate_dataset_quality, detect_anomalies

#  1. CORE TRACKING & LOGOUT INTEGRATION 
from utils.auth import (
    init_db, 
    log_activity, 
    save_dataset_record, 
    save_report_record
)
from pages.login_page import show_login_page
from pages.admin_panel import show_admin_panel

# Database initialisation
init_db()


#  2. UNIVERSAL DYNAMIC DATA LOADER ENGINE (Handles All Messy Sheets) 
def super_smart_data_loader(uploaded_file):
    """
    Universal Data Parser: Automatically detects data orientation (Horizontal vs Vertical),
    cleans garbage wrappers, strips currency symbols, and standardizes dates dynamically.
    """
    try:
        # Step 1: Read raw matrix based on extension
        if uploaded_file.name.endswith('.xlsx') or uploaded_file.name.endswith('.xls'):
            xls = pd.ExcelFile(uploaded_file)
            sheet_name = xls.sheet_names[0]
            raw_df = pd.read_excel(uploaded_file, sheet_name=sheet_name, header=None)
        else:
            raw_df = pd.read_csv(uploaded_file, header=None)
            
        if raw_df.empty:
            return None

        # Step 2: Remove completely blank edge paddings
        raw_df = raw_df.dropna(how='all').dropna(how='all', axis=1)
        raw_df = raw_df.reset_index(drop=True)

        # Step 3: Find the True Structural Header Row
        best_row_idx = 0
        best_score = -1
        for i in range(min(15, len(raw_df))):
            row = raw_df.iloc[i]
            non_null_count = row.notna().sum()
            unique_count = row.nunique()
            score = non_null_count + unique_count
            if score > best_score:
                best_score = score
                best_row_idx = i

        # Slice data from the detected header boundary
        header_vals = raw_df.iloc[best_row_idx].fillna('').astype(str).tolist()
        df = raw_df.iloc[best_row_idx + 1:].copy()
        df.columns = [h.strip() if h.strip() else f"Col_{idx}" for idx, h in enumerate(header_vals)]
        df = df.reset_index(drop=True)

        # Step 4: Auto-Orientation Scanner (Detects Horizontal Matrices)
        cols_combined = " ".join([str(c) for c in df.columns]).lower()
        has_years_in_cols = any(re.search(r"(fy|20\d{2}|19\d{2})", str(c).lower()) for c in df.columns)
        has_years_in_rows = any(re.search(r"(fy|20\d{2}|19\d{2})", str(v).lower()) for v in df.iloc[:3].values.flatten())

        if has_years_in_cols and not has_years_in_rows:
            st.info("Horizontal matrix layout detected. Auto-adapting data shape...")
            label_col = df.columns[0]
            for col in df.columns:
                if any(k in str(col).lower() for k in ['million', 'usd', 'currency', 'metric', 'item']):
                    label_col = col
                    break
            df[label_col] = df[label_col].fillna("Metric").astype(str).str.strip()
            df = df.set_index(label_col).T
            df = df.reset_index().rename(columns={'index': 'Parsed_Date'})

        # Step 5: Advanced Force-Type Casting Engine
        df = df.dropna(how='all')
        date_column_found = False

        for col in df.columns:
            df = df.rename(columns={col: str(col).strip()})
            col_clean = str(col).strip()
            
            if df[col_clean].dtype == 'object':
                df[col_clean] = df[col_clean].apply(lambda x: x.strip() if isinstance(x, str) else x)

            col_str = col_clean.lower()
            
            if not date_column_found and any(k in col_str for k in ['date', 'year', 'timeline', 'period', 'month', 'quarter']):
                df[col_clean] = df[col_clean].astype(str).apply(lambda x: re.sub(r"FY\s*'", "20", x, flags=re.IGNORECASE))
                df[col_clean] = pd.to_datetime(df[col_clean], errors='coerce')
                df = df.rename(columns={col_clean: 'Parsed_Date'})
                date_column_found = True
                continue

            try:
                sanitized_series = df[col_clean].astype(str).str.replace(r'[$,%\s()]', '', regex=True)
                sanitized_series = sanitized_series.apply(lambda x: f"-{x}" if str(x).startswith('-') else x)
                numeric_converted = pd.to_numeric(sanitized_series, errors='coerce')
                
                if numeric_converted.notna().sum() > (0.6 * len(df)):
                    df[col_clean] = numeric_converted
            except:
                if not date_column_found and df[col_clean].astype(str).str.contains(r'(\d{2,4}|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)', case=False, regex=True).any():
                    cleaned_date_strs = df[col_clean].astype(str).apply(lambda x: re.sub(r"FY\s*'", "20", x, flags=re.IGNORECASE))
                    parsed_dates = pd.to_datetime(cleaned_date_strs, errors='coerce')
                    if parsed_dates.notna().sum() > (0.5 * len(df)):
                        df[col_clean] = parsed_dates
                        df = df.rename(columns={col_clean: 'Parsed_Date'})
                        date_column_found = True

        if 'Parsed_Date' not in df.columns:
            df['Parsed_Date'] = pd.date_range(start="2023-01-01", periods=len(df), freq="D")

        df.columns = make_unique_columns(df.columns)
        return df

    except Exception as e:
        st.error(f"Critical failure while parsing messy data layout: {str(e)}")
        return None


def persist_uploaded_file(uploaded_file, username):
    os.makedirs("uploads", exist_ok=True)
    safe_user = re.sub(r"[^a-zA-Z0-9_-]", "_", username or "user")
    safe_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", uploaded_file.name)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join("uploads", f"{timestamp}_{safe_user}_{safe_name}")
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path


def make_unique_columns(columns):
    seen = {}
    unique = []
    for col in columns:
        base = str(col).strip() or "Column"
        count = seen.get(base, 0)
        unique.append(base if count == 0 else f"{base}_{count + 1}")
        seen[base] = count + 1
    return unique


#  Page config 
st.set_page_config(
    page_title="AI Business Analyst",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

#  Custom CSS (Theme + Fixed Layout + Logout Button Styling) 
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght=300;400;500;600;700&family=JetBrains+Mono:wght=400;500&display=swap');

    .block-container {
        padding-top: 1rem !important;
    }
    html, body, [class*="css"] {
        font-family: 'Space Grotesk', sans-serif;
    }

    .main { background: #0a0a0f; }
    .stApp { background: #0a0a0f; }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: #0d0d1a !important;
        border-right: 1px solid #1e1e3a;
    }

    /* Cards */
    .metric-card {
        background: linear-gradient(135deg, #12122a 0%, #1a1a35 100%);
        border: 1px solid #2a2a5a;
        border-radius: 14px;
        padding: 22px 18px;
        text-align: center;
        margin-bottom: 16px;
        min-height: 230px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 14px;
        box-sizing: border-box;
    }
    .metric-card .feature-icon {
        font-size: 2.6rem;
        line-height: 1;
        height: 52px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .metric-card h4 {
        color: #a090f7;
        margin: 0;
        font-size: 1.35rem;
        line-height: 1.2;
    }
    .metric-card p  {
        color: #9090b0;
        font-size: 0.95rem;
        line-height: 1.5;
        margin: 0;
        max-width: 280px;
    }

    /* Chat bubbles */
    .chat-user {
        background: linear-gradient(135deg, #2d1f7a, #1f2d7a);
        border-radius: 18px 18px 4px 18px;
        padding: 12px 16px;
        margin: 8px 0;
        color: #e0e0ff;
        max-width: 80%;
        margin-left: auto;
    }
    .chat-ai {
        background: linear-gradient(135deg, #1a2a1a, #1a1a2a);
        border: 1px solid #2a4a2a;
        border-radius: 18px 18px 18px 4px;
        padding: 12px 16px;
        margin: 8px 0;
        color: #d0ffd0;
        max-width: 85%;
    }

    /* Section headers */
    .section-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #7c6af7;
        border-bottom: 1px solid #2a2a5a;
        padding-bottom: 8px;
        margin-bottom: 16px;
    }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #4a3fa0, #6a3fa0) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 500 !important;
        padding: 0.5rem 1.2rem !important;
        transition: all 0.2s !important;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #5a4fbf, #7a4fbf) !important;
        transform: translateY(-1px) !important;
    }

    /* Red Logout Button Custom Design */
    div[data-testid="stSidebar"] .stButton > button[key="logout_btn"] {
        background: linear-gradient(135deg, #8b1e1e, #b91c1c) !important;
        border: 1px solid #ef4444 !important;
        margin-top: 20px !important;
    }
    div[data-testid="stSidebar"] .stButton > button[key="logout_btn"]:hover {
        background: linear-gradient(135deg, #991b1b, #dc2626) !important;
        box-shadow: 0 0 12px rgba(220, 38, 38, 0.4) !important;
    }

    /* Tabs Layout Fix */
    .stTabs [data-baseweb="tab-list"] {
        background: #12122a;
        border-radius: 8px;
        gap: 4px;
        padding: 4px;
        display: flex !important;
        flex-wrap: nowrap !important;
        overflow-x: auto !important;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        color: #7070a0;
        border-radius: 6px;
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 500;
        white-space: nowrap !important;
    }
    .stTabs [aria-selected="true"] {
        background: #2a2a5a !important;
        color: #a090f7 !important;
    }

    /* Inputs */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        background: #12122a !important;
        border: 1px solid #2a2a5a !important;
        color: #e0e0ff !important;
        border-radius: 8px !important;
        font-family: 'JetBrains Mono', monospace !important;
    }

    [data-testid="stDataFrame"] {
        border: 1px solid #2a2a5a;
        border-radius: 8px;
    }
    hr { border-color: #2a2a5a; }
    #MainMenu { visibility: hidden; }
    footer    { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


#  Session state initialisation 
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False


def init_session():
    defaults = {
        "file_processed": False,
        "df": None,
        "filename": None,
        "chat_history": [],
        "analysis_done": False,
        "analyzer": None,
        "ai_agent": None,
        "api_key_set": False,
        "uploader_key": 0,  
        "user": None,
        "role": None,
        "username": None,
        "dataset_id": None,
        "dataset_status": None,
        "quality_report": None,
    }

    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()

#  100% SECURE ROUTING GATEWAY 
if not st.session_state.get("logged_in", False):
    show_login_page()
    st.stop()


#  Sidebar Content & Actions 
with st.sidebar:
    st.markdown(f"### 👋 Welcome, {st.session_state.username}")
    if st.session_state.role == "admin":
        st.success("Admin Access")
    else:
        st.info("👤 User Access")

    st.markdown("## 🔑 LLM API Key / Ollama")
    api_key = st.text_input(
        "Enter OpenAI/Gemini/Groq key or Ollama URL", 
        type="password", 
        placeholder="sk-..., AIzaSy..., gsk_..., or ollama=http://localhost:11434",
        key="sidebar_api_key_input"
    )
    
    if api_key and not st.session_state.api_key_set:
        try:
            st.session_state.ai_agent = AIAgent(api_key)
            st.session_state.api_key_set = True
            st.rerun()
        except ValueError as e:
            st.error(str(e))

    st.markdown("## ⚙️ Settings")
    if st.session_state.api_key_set:
        st.success("🤖 AI Connected")
    else:
        st.warning("⚠️ AI Not Connected")

    if st.session_state.df is not None:
        st.markdown("## 📂 Current Dataset")
        st.info(f"""
        📄 File: {st.session_state.filename}
        📊 Rows: {st.session_state.df.shape[0]:,}
        📐 Columns: {st.session_state.df.shape[1]}
        """)

        if st.button("🗑️ Remove Dataset", use_container_width=True):
            log_activity(st.session_state.username, "Remove Dataset", f"Removed current session active file: {st.session_state.filename}")
            st.session_state.df = None
            st.session_state.filename = None
            st.session_state.analyzer = None
            st.session_state.chat_history = []
            st.session_state.analysis_done = False
            st.session_state.file_processed = False
            st.session_state.dataset_id = None
            st.session_state.dataset_status = None
            st.session_state.quality_report = None
            st.session_state.uploader_key += 1  
            st.rerun()

    st.markdown("## 🎨 Theme")
    theme = st.selectbox("", ["Dark", "Midnight", "Purple Night"])

    if st.button("🎲 Load Sample Dataset", key="sample_btn_sidebar", use_container_width=True):
        np.random.seed(42)
        dates = pd.date_range("2023-01-01", periods=100, freq="W")
        regions = ["North", "South", "East", "West"]
        products = ["Electronics", "Clothing", "Food", "Books", "Sports"]

        df_sample = pd.DataFrame({
            "Parsed_Date": np.random.choice(dates, 200),
            "Region": np.random.choice(regions, 200),
            "Product": np.random.choice(products, 200),
            "Sales": np.random.randint(1000, 50000, 200),
            "Units": np.random.randint(10, 500, 200),
            "Marketing_Spend": np.random.randint(500, 10000, 200),
            "Returns": np.random.randint(0, 50, 200),
            "Profit": np.random.randint(200, 20000, 200),
        })

        st.session_state.df = df_sample
        st.session_state.filename = "sample_data.csv"
        st.session_state.analysis_done = False
        st.session_state.analyzer = DataAnalyzer(df_sample)
        st.session_state.file_processed = True
        quality_report = evaluate_dataset_quality(df_sample)
        st.session_state.quality_report = quality_report
        st.session_state.dataset_status = "pending"
        
        st.session_state.dataset_id = save_dataset_record(
            "sample_data.csv",
            st.session_state.username,
            df_sample.shape[0],
            df_sample.shape[1],
            quality_score=quality_report["score"],
            quality_grade=quality_report["grade"],
        )
        log_activity(st.session_state.username, "Load Sample Data", "Loaded synthetic pre-configured business model data")
        st.rerun()

    st.markdown("---")
    if st.button("🚪 Log Out", key="logout_btn", use_container_width=True):
        log_activity(st.session_state.username, "Logout", "User closed active session securely.")
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

#  Navigation 
menu = ["Dashboard"]
if st.session_state.role == "admin":
    menu.append("Admin Panel")

selected_page = st.sidebar.radio("📌 Navigation", menu)

if selected_page == "Admin Panel":
    show_admin_panel()
    st.stop()

#  Dashboard View Panel 
st.markdown("# 📊 AI Business Analyst")
st.markdown("<p style='color:#7070a0;margin-top:-10px;'>Upload data, get AI-powered insights, charts, and reports.</p>", unsafe_allow_html=True)

st.info("📊 Upload any CSV or Excel business dataset to generate AI-powered insights instantly.")
st.markdown("### 📤 Upload Your Business Data")

uploaded_file = st.file_uploader(
    "Drag & drop CSV or Excel file here",
    type=["csv", "xlsx", "xls"],
    key=f"main_upload_{st.session_state.uploader_key}"
)

#  DYNAMIC FIX: Jab user cross (X) daba kar file hataye, toh session state automatic reset ho jaye
if uploaded_file is None and st.session_state.df is not None and st.session_state.filename != "sample_data.csv":
    st.session_state.df = None
    st.session_state.filename = None
    st.session_state.analyzer = None
    st.session_state.chat_history = []
    st.session_state.analysis_done = False
    st.session_state.file_processed = False
    st.session_state.dataset_id = None
    st.session_state.dataset_status = None
    st.session_state.quality_report = None
    st.rerun()

if uploaded_file is not None and st.session_state.filename is not None and uploaded_file.name != st.session_state.filename:
    st.session_state.file_processed = False 

# File Processing Logic Gate Connected with Universal Shapes Engine
if uploaded_file is not None and not st.session_state.file_processed:
    if st.button("⚡ Analyze Dataset", use_container_width=True):
        try:
            with st.spinner("Executing Universal Shape Engine..."):
                df = super_smart_data_loader(uploaded_file)
                if df is not None:
                    file_path = persist_uploaded_file(uploaded_file, st.session_state.username)
                    quality_report = evaluate_dataset_quality(df)
                    st.session_state.df = df
                    st.session_state.filename = uploaded_file.name
                    st.session_state.analyzer = DataAnalyzer(df)
                    st.session_state.file_processed = True
                    st.session_state.quality_report = quality_report
                    st.session_state.dataset_status = "pending"
                    st.session_state.dataset_id = save_dataset_record(
                        uploaded_file.name,
                        st.session_state.username,
                        df.shape[0],
                        df.shape[1],
                        file_path=file_path,
                        quality_score=quality_report["score"],
                        quality_grade=quality_report["grade"],
                    )
                    log_activity(st.session_state.username, "Upload Dataset", f"Uploaded and parsed file: {uploaded_file.name}")
                    st.rerun()
        except Exception as e:
            st.error(f"Error reading file: {e}")


if st.session_state.df is None:
    col1, col2, col3 = st.columns(3)
    features = [
        ("📤", "Upload Data", "CSV or Excel files, instantly parsed and previewed"),
        ("🧠", "AI Analysis", "Ask questions about your data"),
        ("📈", "Auto Charts", "Interactive visualizations generated automatically"),
        ("🔍", "Smart Insights", "Trends, anomalies, and KPIs detected automatically"),
        ("📉", "Forecasting", "Predict future trends with built-in models"),
        ("📄", "PDF Reports", "One-click professional business report download"),
    ]
    for i, (icon, title, desc) in enumerate(features):
        with [col1, col2, col3][i % 3]:
            st.markdown(f"""
            <div class="metric-card">
                <div class="feature-icon">{icon}</div>
                <h4>{title}</h4>
                <p>{desc}</p>
            </div>
            """, unsafe_allow_html=True)

else:
    df = st.session_state.df
    analyzer = st.session_state.analyzer

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📋 Overview",
        "📈 Visualizations",
        "🧠 AI Chat",
        "🔮 Forecast",
        "🚨 Anomalies",
        "📄 Report"
    ])

    #  TAB 1: OVERVIEW 
    #  TAB 1: OVERVIEW 
    with tab1:
        st.markdown(f"<div class='section-title'>Dataset: {st.session_state.filename}</div>", unsafe_allow_html=True)

        stats = analyzer.get_summary_stats()
        num_cols = analyzer.get_numeric_columns()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📦 Total Rows",    f"{df.shape[0]:,}")
        col2.metric("📐 Columns",       str(df.shape[1]))
        col3.metric("🔢 Numeric Cols",  str(len(num_cols)))
        col4.metric("❌ Missing Values", str(int(df.isnull().sum().sum())))

        quality_report = st.session_state.get("quality_report") or evaluate_dataset_quality(df)
        q1, q2, q3 = st.columns(3)
        q1.metric("✅ Data Quality", f"{quality_report['score']}/100", quality_report["grade"])
        q2.metric("🔁 Duplicate Rows", str(quality_report["duplicate_rows"]), f"{quality_report['duplicate_pct']}%")
        q3.metric("🛂 Review Status", (st.session_state.get("dataset_status") or "session only").title())
        if quality_report.get("issues"):
            st.caption(" | ".join(quality_report["issues"][:4]))

        st.divider()
        col_left, col_right = st.columns([3, 2])

        with col_left:
            st.markdown("<div class='section-title'>Data Preview</div>", unsafe_allow_html=True)
            st.dataframe(df.head(50), use_container_width=True, height=300)

        with col_right:
            st.markdown("<div class='section-title'>Column Types</div>", unsafe_allow_html=True)
            col_info = analyzer.get_column_info()
            type_df = pd.DataFrame(col_info).T.reset_index()
            type_df.columns = ["Column", "Type", "Non-Null", "Unique"]
            st.dataframe(type_df, use_container_width=True, height=300)

        st.divider()
        st.markdown("<div class='section-title'>Statistical Summary</div>", unsafe_allow_html=True)
        
        #  CRITICAL BUG FIX: `.round(2)` crash check condition deployment
        if stats is not None and len(stats) > 0:
            st.dataframe(stats.round(2), use_container_width=True)
        else:
            st.warning("No numeric data found for summary statistics.")

        missing = df.isnull().sum()
        missing = missing[missing > 0]
        if not missing.empty:
            st.divider()
            st.markdown("<div class='section-title'>⚠️ Missing Values</div>", unsafe_allow_html=True)
            miss_df = pd.DataFrame({"Column": missing.index, "Missing": missing.values,
                                    "Percent": (missing.values / len(df) * 100).round(2)})
            fig = px.bar(miss_df, x="Column", y="Percent",
                        title="Missing Values (%)",
                        color="Percent",
                        color_continuous_scale="Reds",
                        template="plotly_dark")
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

        if len(num_cols) >= 2:
            st.divider()
            st.markdown("<div class='section-title'>🔗 Correlation Matrix</div>", unsafe_allow_html=True)
            corr = analyzer.get_correlation().round(2)
            fig = px.imshow(corr, text_auto=True, color_continuous_scale="RdBu_r",
                            title="Feature Correlation Heatmap", template="plotly_dark")
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

    #  TAB 2: VISUALIZATIONS 
    with tab2:
        st.markdown("<div class='section-title'>📈 Auto-Generated Charts</div>", unsafe_allow_html=True)

        viz = Visualizer(df)
        cat_cols = analyzer.get_categorical_columns()
        num_cols = analyzer.get_numeric_columns()
        date_cols = analyzer.get_date_columns()
        smart_x = None
        if cat_cols:
            preferred_cat_cols = [c for c in cat_cols if not str(c).lower().startswith("col_")]
            smart_x_candidates = preferred_cat_cols or cat_cols
            smart_x = max(smart_x_candidates, key=lambda c: df[c].dropna().nunique())
        fiscal_cols = [
            c for c in num_cols
            if re.search(r"(?:fy\s*'?\s*)?(\d{2,4})", str(c), re.IGNORECASE)
        ]
        smart_y = fiscal_cols[-1] if fiscal_cols else (num_cols[0] if num_cols else None)

        ccol1, ccol2, ccol3 = st.columns(3)
        with ccol1:
            x_options = df.columns.tolist()
            x_index = x_options.index(smart_x) if smart_x in x_options else 0
            x_axis = st.selectbox("X Axis", options=x_options, index=x_index, key="x_sel")
        with ccol2:
            y_options = num_cols if num_cols else df.columns.tolist()
            y_index = y_options.index(smart_y) if smart_y in y_options else 0
            y_axis = st.selectbox("Y Axis", options=y_options, index=y_index, key="y_sel")
        with ccol3:
            chart_type = st.selectbox("Chart Type", ["Bar", "Line", "Scatter", "Histogram", "Box", "Pie"])

        color_by = st.selectbox("Color By (optional)", ["None"] + cat_cols, key="color_sel")
        color_col = None if color_by == "None" else color_by

        fig = viz.plot(chart_type, x_axis, y_axis, color_col)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("This chart type does not fit the selected columns. Try a Bar chart with a text X axis and numeric Y axis.")

        st.divider()
        st.markdown("<div class='section-title'>📊 Smart Auto-Charts</div>", unsafe_allow_html=True)

        auto_figs = viz.generate_auto_charts(num_cols, cat_cols, date_cols)
        if not auto_figs:
            st.info("No meaningful auto-charts could be generated from the detected columns. Try selecting different X and Y fields above.")
        for i in range(0, len(auto_figs), 2):
            c1, c2 = st.columns(2)
            with c1:
                st.plotly_chart(auto_figs[i], use_container_width=True)
            if i + 1 < len(auto_figs):
                with c2:
                    st.plotly_chart(auto_figs[i+1], use_container_width=True)

    #  TAB 3: AI CHAT 
    with tab3:
        st.markdown("<div class='section-title'>🧠 Ask Your Data Anything</div>", unsafe_allow_html=True)

        if not st.session_state.api_key_set:
            st.warning("Please enter your OpenAI API key in the sidebar to use AI Chat.")
        else:
            st.markdown("**Suggested Questions:**")
            suggestions = [
                "What are the top 3 trends in this data?",
                "Which category has the highest performance?",
                "Are there any anomalies or outliers?",
                "Give me a business summary of this dataset",
                "What recommendations do you have to improve revenue?",
            ]
            cols = st.columns(3)
            for idx, sug in enumerate(suggestions):
                with cols[idx % 3]:
                    if st.button(sug, key=f"sug_{idx}", use_container_width=True):
                        st.session_state._pending_question = sug

            st.divider()

            chat_container = st.container()
            with chat_container:
                for msg in st.session_state.chat_history:
                    safe_content = html.escape(str(msg["content"]))
                    if msg["role"] == "user":
                        st.markdown(f"<div class='chat-user'>User: {safe_content}</div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div class='chat-ai'>AI: {safe_content}</div>", unsafe_allow_html=True)
            user_q = st.text_input("Ask a question about your data...", key="chat_input",
                                  placeholder="e.g. Which region generates the most revenue?")

            if hasattr(st.session_state, "_pending_question") and st.session_state._pending_question:
                user_q = st.session_state._pending_question
                st.session_state._pending_question = None

            c_send, c_clear = st.columns([6, 1])
            with c_send:
                send_btn = st.button("Send 🚀", use_container_width=True)
            with c_clear:
                clear_btn = st.button("🗑️ Clear", use_container_width=True)

            if send_btn and user_q.strip():
                st.session_state.chat_history.append({"role": "user", "content": user_q})
                with st.spinner("AI is thinking..."):
                    response = st.session_state.ai_agent.answer_question(df, user_q, st.session_state.chat_history)
                st.session_state.chat_history.append({"role": "assistant", "content": response})
                
                log_activity(st.session_state.username, "AI Query", f"Question: {user_q[:60]}...")
                st.rerun()

            if clear_btn:
                st.session_state.chat_history = []
                log_activity(st.session_state.username, "Clear Chat", f"Cleared AI Chat history metrics stream for file: {st.session_state.filename}")
                st.rerun()

   #  TAB 4: FORECAST 
    with tab4:
        st.markdown("<div class='section-title'>🔮 Sales Forecasting</div>", unsafe_allow_html=True)

        date_cols = analyzer.get_date_columns()
        num_cols  = analyzer.get_numeric_columns()

        available_cols = df.columns.tolist()

        if not available_cols:
            st.warning("Forecasting requires data arrays.")
        else:
            fc1, fc2, fc3 = st.columns(3)
            
            #  SMART DEFAULT 1: Agar loader ne 'Parsed_Date' banaya hai, toh use automatic chun lo
            if 'Parsed_Date' in available_cols:
                default_date_idx = available_cols.index('Parsed_Date')
            else:
                default_date_idx = 0

            with fc1:
                date_col = st.selectbox("Date Column", options=available_cols, index=default_date_idx)
            
            #  SMART DEFAULT 2: End-user ko gande text columns chunne se bachao
            # Value to Forecast ke dropdown mein sirf vahi columns dikhao jo asali numeric data hain!
            value_targets = [c for c in num_cols if c != 'Parsed_Date']
            
            # Agar koi valid numeric column mila toh use dropdown ki pehli choice banao, varna fallback to all
            display_options = value_targets if value_targets else available_cols
            
            with fc2:
                value_col = st.selectbox("Value to Forecast", options=display_options, index=0)
                
            with fc3:
                periods = st.slider("Forecast Periods", 4, 52, 12)

            if st.button("🚀 Run Forecast", use_container_width=True):
                with st.spinner("Running forecast..."):
                    import utils.forecaster
                    import importlib
                    importlib.reload(utils.forecaster)
                    from utils.forecaster import Forecaster
                    
                    try:
                        fc = Forecaster(df, date_col, value_col)
                        fig, metrics = fc.forecast(periods)
                        
                        if fig is not None:
                            st.plotly_chart(fig, use_container_width=True)
                            m1, m2, m3 = st.columns(3)
                            m1.metric("MAE", f"{metrics.get('mae', 0.0):.2f}" if isinstance(metrics.get('mae'), (int, float)) else "N/A")
                            m2.metric("RMSE", f"{metrics.get('rmse', 0.0):.2f}" if isinstance(metrics.get('rmse'), (int, float)) else "N/A")
                            m3.metric("Trend", metrics.get("trend", ""))
                            
                            log_activity(st.session_state.username, "Forecast Model", f"Target KPI: {value_col} over {periods} periods")
                        else:
                            st.error(f"Could not generate forecast. Details: {metrics.get('error', 'Unknown Error')}")
                    except Exception as e:
                        st.error(f"Runtime execution block failed: {str(e)}")

    #  TAB 5: ANOMALIES
    with tab5:
        st.markdown("<div class='section-title'>🚨 Anomaly Detection</div>", unsafe_allow_html=True)
        anomalies, anomaly_error = detect_anomalies(df)
        if anomaly_error:
            st.info(anomaly_error)
        elif anomalies.empty:
            st.success("No major numeric outliers detected in this dataset.")
        else:
            st.warning(f"{len(anomalies)} unusual rows detected. Review these before making business decisions.")
            st.dataframe(anomalies, use_container_width=True, height=360)

            numeric_cols = analyzer.get_numeric_columns()
            if numeric_cols and "Anomaly_Score" in anomalies.columns:
                fig = px.scatter(
                    anomalies,
                    x=anomalies.index,
                    y="Anomaly_Score",
                    title="Anomaly Severity by Row",
                    template="plotly_dark",
                    color="Anomaly_Score",
                    color_continuous_scale="Reds",
                )
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)

    #  TAB 6: REPORT 
    with tab6:
        st.markdown("<div class='section-title'>📄 Generate Business Report</div>", unsafe_allow_html=True)

        if not st.session_state.api_key_set:
            st.warning("Please enter your OpenAI API key in the sidebar to generate AI-powered reports.")
        elif st.session_state.get("dataset_status") not in [None, "approved"] and st.session_state.role != "admin":
            st.warning("This dataset is pending admin review. Reports unlock after approval.")
        else:
            rcol1, rcol2 = st.columns(2)
            with rcol1:
                company_name = st.text_input("Company Name", value="Acme Corp")
                analyst_name = st.text_input("Analyst Name", value="AI Business Analyst")
            with rcol2:
                report_title = st.text_input("Report Title", value="Business Intelligence Report")
                report_date  = st.date_input("Report Date", value=datetime.today())

            if st.button("📊 Generate Report", use_container_width=True):
                with st.spinner("AI is writing your report..."):
                    gen = ReportGenerator(
                        df=df,
                        ai_agent=st.session_state.ai_agent,
                        analyzer=analyzer,
                        company_name=company_name,
                        analyst_name=analyst_name,
                        report_title=report_title,
                        report_date=str(report_date),
                        filename=st.session_state.filename or "data.csv",
                    )
                    pdf_bytes = gen.generate()

                if pdf_bytes:
                    st.success("✅ Report generated successfully!")
                    save_report_record(report_title, st.session_state.username)
                    log_activity(st.session_state.username, "Generate Report", f"Generated document title: {report_title}")
                    
                    st.download_button(
                        label="⬇️ Download PDF Report",
                        data=pdf_bytes,
                        file_name=f"business_report_{report_date}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                else:
                    st.error("Report generation failed. Check your API key.")
                    

