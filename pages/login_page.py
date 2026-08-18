import streamlit as st
import secrets
import re
import os
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta
from utils.auth import (
    get_conn, log_activity, authenticate, create_user, hash_password,
    get_login_lock, record_login_failure, clear_login_failures
)
from utils.branding import BRAND_NAME, BRAND_TAGLINE, brand_logo_data_uri


def password_strength(password: str) -> tuple[int, str]:
    strength = 0
    if len(password) >= 8:
        strength += 1
    if re.search(r"[a-z]", password) and re.search(r"[A-Z]", password):
        strength += 1
    if re.search(r"\d", password):
        strength += 1
    if re.search(r"[_@$%&*!#.-]", password):
        strength += 1
    labels = ["Weak", "Moderate", "Strong", "Excellent"]
    return strength, labels[max(strength, 1) - 1] if password else "Weak"


def user_exists(username: str = "", email: str = "") -> tuple[bool, str]:
    conn = get_conn()
    row = conn.execute(
        "SELECT username,email FROM users WHERE lower(username)=lower(?) OR lower(email)=lower(?)",
        (username.strip(), email.strip())
    ).fetchone()
    conn.close()
    if not row:
        return False, ""
    if row["username"].lower() == username.strip().lower():
        return True, "Username already exists."
    return True, "Email is already registered."


def get_smtp_setting(key: str, default: str = "") -> str:
    try:
        if "smtp" in st.secrets and key in st.secrets["smtp"]:
            return str(st.secrets["smtp"][key])
    except Exception:
        pass
    return os.getenv(f"SMTP_{key.upper()}", default)


def send_otp_email(to_email: str, username: str, otp: str) -> tuple[bool, str]:
    host = get_smtp_setting("host")
    port = int(get_smtp_setting("port", "587") or "587")
    sender = get_smtp_setting("user")
    password = get_smtp_setting("password")
    from_email = get_smtp_setting("from_email", sender)

    if not host or not sender or not password or not from_email:
        return False, "SMTP email settings are not configured."

    msg = EmailMessage()
    msg["Subject"] = f"{BRAND_NAME} password reset OTP"
    msg["From"] = from_email
    msg["To"] = to_email
    msg.set_content(
        f"Hi {username},\n\n"
        f"Your {BRAND_NAME} password reset OTP is: {otp}\n\n"
        "This code is valid for this reset session. If you did not request this, ignore this email.\n\n"
        f"{BRAND_NAME}"
    )

    try:
        with smtplib.SMTP(host, port, timeout=20) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)
        return True, "OTP sent to your registered email."
    except Exception as exc:
        return False, f"Email delivery failed: {exc}"


def can_skip_email_verification() -> bool:
    return os.getenv("ALLOW_UNVERIFIED_REGISTRATION", "").lower() in {"1", "true", "yes"}


def reset_attempts_exceeded() -> bool:
    attempts = st.session_state.get("recovery_attempts", 0)
    return attempts >= 5


def mask_email(email: str) -> str:
    if "@" not in email:
        return email
    name, domain = email.split("@", 1)
    if len(name) <= 2:
        masked = name[0] + "*"
    else:
        masked = name[0] + "*" * (len(name) - 2) + name[-1]
    return f"{masked}@{domain}"


def show_login_page():
    """Render the logged-out landing page and secondary auth step."""
    view_param = st.query_params.get("view", "") if hasattr(st, "query_params") else ""
    auth_param = st.query_params.get("auth", "") if hasattr(st, "query_params") else ""
    if view_param == "landing":
        st.session_state["landing_auth_mode"] = False
        st.session_state["reset_mode"] = "login"
        if hasattr(st, "query_params"):
            st.query_params.clear()
        st.rerun()

    if auth_param in {"login", "register"} and not st.session_state.get("landing_auth_mode"):
        st.session_state["landing_auth_mode"] = True
        st.session_state["reset_mode"] = "register" if auth_param == "register" else "login"

    if not st.session_state.get("landing_auth_mode", False):
        show_landing_page()
        return

    show_auth_step()


def show_landing_page():
    """Render premium scrollable marketing landing page for logged-out users."""
    logo_data_uri = brand_logo_data_uri()
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
    html { scroll-behavior: smooth; }
    .stApp {
        background:
            linear-gradient(rgba(255,255,255,0.028) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,0.028) 1px, transparent 1px),
            radial-gradient(circle at 18% 12%, rgba(69, 98, 255, 0.22), transparent 34%),
            radial-gradient(circle at 82% 8%, rgba(124, 58, 237, 0.18), transparent 34%),
            linear-gradient(135deg, #070b15 0%, #0a0e1a 48%, #131826 100%) !important;
        background-size: 42px 42px, 42px 42px, auto, auto, auto !important;
        color: #f7fbff;
    }
    [data-testid="stSidebar"] { display: none !important; }
    .block-container {
        max-width: 100% !important;
        padding: 0 !important;
    }
    .bv-page {
        font-family: 'Inter', system-ui, sans-serif;
        overflow: hidden;
    }
    .bv-nav {
        position: sticky;
        top: 0;
        z-index: 50;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 24px;
        padding: 14px clamp(20px, 5vw, 72px);
        background: rgba(8, 13, 31, 0.76);
        border-bottom: 1px solid rgba(148, 163, 184, 0.16);
        backdrop-filter: blur(18px);
    }
    .bv-brand { display: flex; align-items: center; gap: 12px; min-width: 210px; }
    .bv-brand img { width: 158px; height: auto; display: block; }
    .bv-links { display: flex; align-items: center; justify-content: center; gap: 26px; flex: 1; }
    .bv-links a {
        color: #aeb9d8;
        text-decoration: none;
        font-size: 0.94rem;
        font-weight: 650;
        transition: color .2s ease;
    }
    .bv-links a:hover { color: #ffffff; }
    .bv-nav-actions { display: flex; gap: 10px; align-items: center; }
    .bv-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-height: 44px;
        padding: 0 18px;
        border-radius: 12px;
        color: #ffffff !important;
        text-decoration: none !important;
        font-weight: 800;
        border: 1px solid rgba(148, 163, 184, 0.22);
        background: rgba(255,255,255,0.06);
        transition: transform .22s ease, box-shadow .22s ease, border-color .22s ease;
    }
    .bv-btn:hover { transform: translateY(-2px); border-color: rgba(0, 212, 255, .55); }
    .bv-btn.primary {
        border: 0;
        background: linear-gradient(135deg, #7c3cff 0%, #2f6bff 48%, #00d4ff 100%);
        box-shadow: 0 16px 38px rgba(47, 107, 255, 0.28);
    }
    .bv-section {
        padding: clamp(56px, 7vw, 96px) clamp(20px, 5vw, 72px);
        max-width: 1280px;
        margin: 0 auto;
    }
    .bv-hero {
        min-height: 720px;
        display: grid;
        grid-template-columns: minmax(0, 1.04fr) minmax(420px, .96fr);
        gap: clamp(34px, 5vw, 70px);
        align-items: center;
        position: relative;
    }
    .bv-eyebrow {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        color: #67e8f9;
        background: rgba(0, 212, 255, 0.09);
        border: 1px solid rgba(0, 212, 255, 0.26);
        border-radius: 999px;
        padding: 8px 13px;
        font-weight: 800;
        font-size: .82rem;
        margin-bottom: 18px;
    }
    .bv-hero h1 {
        margin: 0;
        max-width: 780px;
        color: #ffffff;
        font-size: clamp(3rem, 5.4vw, 5.95rem);
        line-height: .96;
        letter-spacing: -0.04em;
        font-weight: 900;
    }
    .bv-gradient-text {
        background: linear-gradient(135deg, #ffffff 0%, #8fdfff 48%, #9b6cff 100%);
        -webkit-background-clip: text;
        color: transparent;
    }
    .bv-subhead {
        max-width: 650px;
        margin: 24px 0 0;
        color: #aeb9d8;
        font-size: clamp(1.05rem, 1.7vw, 1.24rem);
        line-height: 1.68;
    }
    .bv-hero-actions { display: flex; flex-wrap: wrap; gap: 14px; margin-top: 34px; }
    .bv-mini-proof { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 28px; color: #ccd6f6; }
    .bv-mini-proof span {
        border: 1px solid rgba(148, 163, 184, .16);
        background: rgba(255,255,255,.045);
        border-radius: 999px;
        padding: 8px 12px;
        font-size: .86rem;
        font-weight: 700;
    }
    .bv-dashboard {
        position: relative;
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-radius: 26px;
        background: linear-gradient(145deg, rgba(20, 29, 58, .88), rgba(7, 11, 25, .92));
        box-shadow: 0 34px 90px rgba(0,0,0,.42), 0 0 64px rgba(47,107,255,.13);
        padding: 18px;
        min-height: 440px;
        overflow: hidden;
    }
    .bv-browser-bar { display: flex; align-items: center; gap: 8px; margin-bottom: 18px; }
    .bv-dot { width: 11px; height: 11px; border-radius: 50%; background: #ef4444; }
    .bv-dot:nth-child(2) { background: #f59e0b; }
    .bv-dot:nth-child(3) { background: #10b981; }
    .bv-preview-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
    .bv-preview-card {
        border: 1px solid rgba(148, 163, 184, .16);
        background: rgba(255,255,255,.055);
        border-radius: 18px;
        padding: 16px;
        min-height: 110px;
    }
    .bv-preview-card.wide { grid-column: 1 / -1; min-height: 176px; }
    .bv-label { color: #8b98bb; font-size: .78rem; font-weight: 800; text-transform: uppercase; }
    .bv-value { color: #ffffff; font-size: 1.62rem; font-weight: 900; margin-top: 8px; }
    .bv-chip { color: #50f0c8; font-size: .82rem; margin-top: 5px; font-weight: 800; }
    .bv-chart { height: 112px; margin-top: 12px; display: flex; align-items: flex-end; gap: 10px; }
    .bv-bar {
        flex: 1;
        min-height: 22px;
        border-radius: 10px 10px 4px 4px;
        background: linear-gradient(180deg, #00d4ff, #7c3cff);
        animation: bvPulse 2.6s ease-in-out infinite;
    }
    .bv-line {
        height: 128px;
        margin-top: 12px;
        border-radius: 16px;
        background:
            linear-gradient(135deg, transparent 0 18%, rgba(0,212,255,.75) 19% 21%, transparent 22% 38%, rgba(124,60,255,.85) 39% 41%, transparent 42% 58%, rgba(0,212,255,.75) 59% 61%, transparent 62%),
            linear-gradient(rgba(255,255,255,.065) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,.065) 1px, transparent 1px);
        background-size: auto, 34px 34px, 34px 34px;
        background-color: rgba(8,13,31,.62);
    }
    @keyframes bvPulse { 0%,100% { opacity:.72; transform: scaleY(.88); } 50% { opacity:1; transform: scaleY(1); } }
    .bv-stats {
        max-width: 1280px;
        margin: -32px auto 0;
        padding: 0 clamp(20px, 5vw, 72px) 34px;
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 14px;
    }
    .bv-stat {
        border: 1px solid rgba(148, 163, 184, .15);
        border-radius: 18px;
        background: rgba(255,255,255,.055);
        backdrop-filter: blur(14px);
        padding: 20px;
        box-shadow: 0 18px 44px rgba(0,0,0,.18);
    }
    .bv-stat strong { display:block; color:#fff; font-size: clamp(1.35rem, 2.8vw, 2.25rem); font-weight: 900; }
    .bv-stat span { color:#95a3c7; font-weight: 700; font-size: .9rem; }
    .bv-section-title { text-align: center; max-width: 760px; margin: 0 auto 34px; }
    .bv-section-title h2 { margin:0; font-size: clamp(2rem, 4vw, 3.4rem); line-height: 1.05; color:#fff; letter-spacing: -0.035em; }
    .bv-section-title p { color:#aeb9d8; font-size: 1.05rem; line-height:1.65; margin: 16px 0 0; }
    .bv-feature-grid { display:grid; grid-template-columns: repeat(3, 1fr); gap: 18px; }
    .bv-feature, .bv-quote {
        border: 1px solid rgba(148, 163, 184, .15);
        border-radius: 22px;
        padding: 24px;
        background: linear-gradient(145deg, rgba(255,255,255,.07), rgba(255,255,255,.035));
        min-height: 190px;
        transition: transform .22s ease, border-color .22s ease, box-shadow .22s ease;
    }
    .bv-feature:hover, .bv-quote:hover {
        transform: translateY(-6px);
        border-color: rgba(0, 212, 255, .36);
        box-shadow: 0 22px 56px rgba(0,0,0,.24);
    }
    .bv-icon {
        width: 46px;
        height: 46px;
        display:flex;
        align-items:center;
        justify-content:center;
        border-radius: 14px;
        background: linear-gradient(135deg, #7c3cff, #00d4ff);
        font-size: 1.35rem;
        margin-bottom: 18px;
    }
    .bv-feature h3 { margin:0 0 10px; color:#fff; font-size:1.15rem; }
    .bv-feature p, .bv-step p, .bv-quote p { color:#aeb9d8; line-height:1.55; margin:0; }
    .bv-timeline { display:grid; grid-template-columns: repeat(4, 1fr); gap: 16px; position:relative; }
    .bv-step {
        border: 1px solid rgba(148, 163, 184, .15);
        border-radius: 22px;
        background: rgba(255,255,255,.052);
        padding: 24px;
    }
    .bv-step-num { color:#67e8f9; font-size:.85rem; font-weight:900; margin-bottom:10px; }
    .bv-step h3 { color:#fff; margin:0 0 8px; }
    .bv-product-frame {
        border: 1px solid rgba(148, 163, 184, .18);
        border-radius: 28px;
        background: linear-gradient(145deg, rgba(21, 29, 58, .92), rgba(8, 13, 31, .94));
        box-shadow: 0 30px 80px rgba(0,0,0,.34);
        padding: 18px;
    }
    .bv-product-layout { display:grid; grid-template-columns: 220px 1fr; gap: 16px; }
    .bv-side { border-radius: 20px; background: rgba(255,255,255,.05); padding: 16px; }
    .bv-side div { height: 12px; border-radius: 99px; background: rgba(174,185,216,.22); margin: 14px 0; }
    .bv-main-preview { display:grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
    .bv-main-preview .bv-preview-card:nth-child(4) { grid-column: 1 / 3; }
    .bv-main-preview .bv-preview-card:nth-child(5) { grid-column: 3; }
    .bv-stack-row { display:flex; flex-wrap:wrap; gap: 12px; justify-content:center; }
    .bv-badge {
        border:1px solid rgba(148,163,184,.16);
        border-radius:999px;
        padding: 11px 15px;
        color:#dbeafe;
        background: rgba(255,255,255,.055);
        font-weight:800;
    }
    .bv-quotes { display:grid; grid-template-columns: repeat(3, 1fr); gap:16px; }
    .bv-quote strong { display:block; color:#fff; margin-top: 16px; }
    .bv-final {
        max-width: none;
        margin-top: 32px;
        background: linear-gradient(135deg, rgba(124,60,255,.92), rgba(47,107,255,.92), rgba(0,212,255,.78));
        text-align:center;
        padding: 80px 24px;
    }
    .bv-final h2 { color:#fff; font-size: clamp(2.2rem, 5vw, 4.2rem); margin:0 0 16px; letter-spacing:-.04em; }
    .bv-final p { color:rgba(255,255,255,.88); font-size:1.1rem; margin: 0 0 28px; }
    .bv-footer {
        padding: 36px clamp(20px, 5vw, 72px);
        border-top: 1px solid rgba(148,163,184,.14);
        color:#8b98bb;
        display:flex;
        justify-content:space-between;
        gap:24px;
        flex-wrap:wrap;
    }
    .bv-footer img { width: 150px; }
    .bv-footer a { color:#aeb9d8; margin-left:18px; text-decoration:none; font-weight:700; }
    @media (max-width: 980px) {
        .bv-links { display:none; }
        .bv-hero { grid-template-columns: 1fr; min-height: auto; padding-top: 40px; }
        .bv-dashboard { min-height: auto; }
        .bv-stats, .bv-feature-grid, .bv-timeline, .bv-quotes { grid-template-columns: repeat(2, 1fr); }
        .bv-product-layout { grid-template-columns: 1fr; }
    }
    @media (max-width: 640px) {
        .bv-nav { align-items:flex-start; flex-direction:column; }
        .bv-nav-actions { width:100%; }
        .bv-nav-actions .bv-btn { flex:1; }
        .bv-hero-actions .bv-btn { width:100%; }
        .bv-preview-grid, .bv-stats, .bv-feature-grid, .bv-timeline, .bv-quotes, .bv-main-preview { grid-template-columns: 1fr; }
        .bv-main-preview .bv-preview-card:nth-child(4), .bv-main-preview .bv-preview-card:nth-child(5) { grid-column:auto; }
        .bv-footer { flex-direction:column; }
        .bv-footer a { margin: 0 14px 0 0; }
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="bv-page">
      <nav class="bv-nav">
        <div class="bv-brand"><img src="{logo_data_uri}" alt="{BRAND_NAME} logo"></div>
        <div class="bv-links">
          <a href="#features">Features</a>
          <a href="#how">How it Works</a>
          <a href="#preview">Preview</a>
          <a href="#docs">Docs</a>
        </div>
        <div class="bv-nav-actions">
          <a class="bv-btn" href="?auth=login">Sign In</a>
          <a class="bv-btn primary" href="?auth=register">Get Started</a>
        </div>
      </nav>

      <section class="bv-section bv-hero">
        <div>
          <div class="bv-eyebrow">AI analytics workspace for business data</div>
          <h1>Turn Your Business Data Into <span class="bv-gradient-text">Instant AI Insights</span></h1>
          <p class="bv-subhead">{BRAND_NAME} converts CSV and Excel files into dashboards, quality scores, forecasts, anomaly alerts, AI answers, and export-ready PDF reports.</p>
          <div class="bv-hero-actions">
            <a class="bv-btn primary" href="?auth=register">Get Started Free</a>
            <a class="bv-btn" href="?auth=login">Sign In</a>
          </div>
          <div class="bv-mini-proof">
            <span>Smart parser</span><span>AI chat</span><span>Forecasting</span><span>Admin approvals</span>
          </div>
        </div>
        <div class="bv-dashboard" aria-label="BizVision AI dashboard preview">
          <div class="bv-browser-bar"><span class="bv-dot"></span><span class="bv-dot"></span><span class="bv-dot"></span></div>
          <div class="bv-preview-grid">
            <div class="bv-preview-card"><div class="bv-label">Data Quality</div><div class="bv-value">94/100</div><div class="bv-chip">Ready for reporting</div></div>
            <div class="bv-preview-card"><div class="bv-label">Forecast Trend</div><div class="bv-value">+18.7%</div><div class="bv-chip">Next period growth</div></div>
            <div class="bv-preview-card wide"><div class="bv-label">Revenue Momentum</div><div class="bv-chart"><span class="bv-bar" style="height:42%"></span><span class="bv-bar" style="height:58%"></span><span class="bv-bar" style="height:46%"></span><span class="bv-bar" style="height:72%"></span><span class="bv-bar" style="height:64%"></span><span class="bv-bar" style="height:88%"></span><span class="bv-bar" style="height:78%"></span></div></div>
            <div class="bv-preview-card wide"><div class="bv-label">AI Insight Path</div><div class="bv-line"></div></div>
          </div>
        </div>
      </section>

      <div class="bv-stats">
        <div class="bv-stat"><strong>10,000+</strong><span>Rows analyzed per session</span></div>
        <div class="bv-stat"><strong>99.9%</strong><span>Demo-ready uptime target</span></div>
        <div class="bv-stat"><strong>4</strong><span>AI providers supported</span></div>
        <div class="bv-stat"><strong>Live</strong><span>Real-time business insights</span></div>
      </div>

      <section class="bv-section" id="features">
        <div class="bv-section-title"><h2>Everything needed for a complete analytics flow</h2><p>From messy uploads to governed reports, BizVision AI covers the parts most dashboards skip.</p></div>
        <div class="bv-feature-grid">
          <div class="bv-feature"><div class="bv-icon">01</div><h3>Smart CSV/Excel Parser</h3><p>Detects headers, cleans blank wrappers, handles dates, currency, percentages, and horizontal matrix layouts.</p></div>
          <div class="bv-feature"><div class="bv-icon">02</div><h3>AI Chat Insights</h3><p>Ask natural-language questions over dataset summaries and get business-ready answers.</p></div>
          <div class="bv-feature"><div class="bv-icon">03</div><h3>Data Quality Scoring</h3><p>Automatically flags missing values, duplicates, risky structures, and readiness grade.</p></div>
          <div class="bv-feature"><div class="bv-icon">04</div><h3>Forecasting</h3><p>Trend analysis with future projections, MAE/RMSE metrics, and direction indicators.</p></div>
          <div class="bv-feature"><div class="bv-icon">05</div><h3>Anomaly Detection</h3><p>Isolation Forest highlights unusual business records and suspicious numeric patterns.</p></div>
          <div class="bv-feature"><div class="bv-icon">06</div><h3>PDF Reports</h3><p>Generate export-ready business reports with charts, AI summaries, and admin approval workflow.</p></div>
        </div>
      </section>

      <section class="bv-section" id="how">
        <div class="bv-section-title"><h2>How it works</h2><p>A clean four-step workflow for business users, students, and teams.</p></div>
        <div class="bv-timeline">
          <div class="bv-step"><div class="bv-step-num">STEP 01</div><h3>Upload Data</h3><p>Drop in CSV or Excel files and let the parser normalize the dataset.</p></div>
          <div class="bv-step"><div class="bv-step-num">STEP 02</div><h3>AI Analyzes</h3><p>Quality, summaries, patterns, charts, anomalies, and forecasts are generated.</p></div>
          <div class="bv-step"><div class="bv-step-num">STEP 03</div><h3>Get Insights</h3><p>Use dashboards and AI chat to explain what is happening in the business.</p></div>
          <div class="bv-step"><div class="bv-step-num">STEP 04</div><h3>Export Report</h3><p>Create PDF reports and route outputs through admin governance.</p></div>
        </div>
      </section>

      <section class="bv-section" id="preview">
        <div class="bv-section-title"><h2>Live product preview</h2><p>A dashboard-style workspace with charts, quality metrics, usage controls, and insight generation.</p></div>
        <div class="bv-product-frame">
          <div class="bv-browser-bar"><span class="bv-dot"></span><span class="bv-dot"></span><span class="bv-dot"></span></div>
          <div class="bv-product-layout">
            <div class="bv-side"><div style="width:70%"></div><div></div><div style="width:84%"></div><div style="width:58%"></div><div style="width:76%"></div><div style="width:64%"></div></div>
            <div class="bv-main-preview">
              <div class="bv-preview-card"><div class="bv-label">Rows</div><div class="bv-value">18.4K</div><div class="bv-chip">Parsed</div></div>
              <div class="bv-preview-card"><div class="bv-label">Charts</div><div class="bv-value">12</div><div class="bv-chip">Auto-generated</div></div>
              <div class="bv-preview-card"><div class="bv-label">Reports</div><div class="bv-value">PDF</div><div class="bv-chip">Ready</div></div>
              <div class="bv-preview-card wide"><div class="bv-label">Performance Chart</div><div class="bv-line"></div></div>
              <div class="bv-preview-card"><div class="bv-label">AI Summary</div><p style="color:#dbeafe;line-height:1.55;margin-top:12px">Sales momentum increased in West region while returns need review in Electronics.</p></div>
            </div>
          </div>
        </div>
      </section>

      <section class="bv-section" id="docs">
        <div class="bv-section-title"><h2>Built on a credible stack</h2><p>Lightweight, explainable, and ready for college demos or production extension.</p></div>
        <div class="bv-stack-row">
          <span class="bv-badge">Streamlit</span><span class="bv-badge">OpenAI</span><span class="bv-badge">Gemini</span><span class="bv-badge">Groq</span><span class="bv-badge">Python</span><span class="bv-badge">Plotly</span>
        </div>
      </section>

      <section class="bv-section">
        <div class="bv-section-title"><h2>Social proof</h2><p>Placeholder quotes for you to edit before final submission.</p></div>
        <div class="bv-quotes">
          <div class="bv-quote"><p>"BizVision AI helped me explain raw sales data like a complete business intelligence workflow."</p><strong>Placeholder Student</strong></div>
          <div class="bv-quote"><p>"The dashboard feels practical because it includes quality checks, forecasting, and reports."</p><strong>Placeholder Reviewer</strong></div>
          <div class="bv-quote"><p>"A strong demo for showing how AI can support real business analysis decisions."</p><strong>Placeholder Mentor</strong></div>
        </div>
      </section>

      <section class="bv-final">
        <h2>Start Analyzing Your Data Today</h2>
        <p>Upload a file, ask questions, detect patterns, forecast trends, and export your report.</p>
        <a class="bv-btn primary" href="?auth=register">Get Started Free</a>
      </section>

      <footer class="bv-footer">
        <div><img src="{logo_data_uri}" alt="{BRAND_NAME} logo"><div>{BRAND_TAGLINE}</div></div>
        <div><a href="#features">Features</a><a href="#how">Workflow</a><a href="#preview">Preview</a><a href="?auth=login">Sign In</a></div>
        <div>Copyright 2026 BizVision AI. All rights reserved.</div>
      </footer>
    </div>
    """, unsafe_allow_html=True)


def show_auth_step():
    """Render the clean centered auth form after a landing CTA is clicked."""
    logo_data_uri = brand_logo_data_uri()

    def brand_header(title: str, subtitle: str) -> str:
        return (
            '<div class="brand-lockup">'
            f'<div class="brand-logo"><img src="{logo_data_uri}" alt="{BRAND_NAME} logo"></div>'
            f'<div class="brand-kicker">{BRAND_TAGLINE}</div>'
            '</div>'
            f'<div class="login-title">{title}</div>'
            f'<div class="login-sub">{subtitle}</div>'
        )

    st.markdown("""
    <style>
    .stApp {
        background:
            linear-gradient(rgba(255,255,255,0.028) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,0.028) 1px, transparent 1px),
            radial-gradient(circle at 50% 0%, rgba(0, 212, 255, 0.18), transparent 34%),
            linear-gradient(135deg, #070b15 0%, #0a0e1a 48%, #131826 100%) !important;
        background-size: 42px 42px, 42px 42px, auto, auto !important;
    }
    [data-testid="stSidebar"] { display: none !important; }
    .block-container { padding-top: 2.4rem !important; max-width: 100% !important; }
    .auth-shell {
        width: min(100%, 1040px);
        margin: 0 auto 22px;
        padding: 0 24px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        color: #aeb9d8;
    }
    .auth-shell a { color: #67e8f9; text-decoration: none; font-weight: 800; }
    
    div[data-testid="stVerticalBlock"] > div:has(.custom-login-box) {
        background:
            radial-gradient(circle at 50% 0%, rgba(0, 212, 255, 0.16), transparent 34%),
            linear-gradient(160deg, #0f0f2a 0%, #14142e 100%) !important;
        border: 1px solid rgba(0, 212, 255, 0.22) !important;
        border-radius: 18px !important;
        padding: 34px 30px !important;
        max-width: 430px !important;
        margin: 0 auto !important;
        box-shadow: 0 22px 70px rgba(0, 0, 0, 0.42), 0 0 42px rgba(0, 102, 255, 0.12) !important;
    }
    .custom-login-box { display: none !important; }
    .login-logo { font-size: 2.8rem; text-align: center; margin-bottom: 5px; }
    .brand-lockup {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 9px;
        margin-bottom: 18px;
    }
    .brand-logo {
        width: min(100%, 310px);
        min-height: 86px;
        margin: 0 auto;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 12px 18px;
        border-radius: 18px;
        background: linear-gradient(135deg, rgba(255,255,255,0.96), rgba(214,236,255,0.9));
        border: 1px solid rgba(0, 212, 255, 0.35);
        box-shadow: 0 14px 36px rgba(0, 212, 255, 0.18), inset 0 1px 0 rgba(255,255,255,0.95);
    }
    .brand-logo img {
        width: 100%;
        max-height: 68px;
        object-fit: contain;
        filter: drop-shadow(0 8px 16px rgba(0, 28, 80, 0.18));
    }
    .brand-kicker {
        text-align: center;
        color: #3ee7ff;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0;
    }
    .login-title { text-align: center; font-size: 1.85rem; font-weight: 800; color: #c8bcff; margin-bottom: 2px; }
    .login-sub { text-align: center; color: #8d88c7; font-size: 0.92rem; margin-bottom: 22px; }
    .stTextInput > div > div > input { background: #12122a !important; border: 1px solid #2a2a5a !important; color: #e0e0ff !important; border-radius: 8px !important; }
    
    div[data-testid="stForm"] { border: none !important; padding: 0 !important; background: transparent !important; }
    div[data-testid="stFormSubmitButtonHint"] { display: none !important; }
    
    /*  TARGETED CENTER ALIGNMENT JUGAD FOR SIGN IN BUTTON */
    div[data-testid="stForm"] .stFormSubmitButton {
        display: flex !important;
        justify-content: center !important; /* Rocket center alignment block lock */
        width: 100% !important;
        margin-top: 25px !important;
    }
    div[data-testid="stForm"] .stFormSubmitButton button {
        background: linear-gradient(135deg, #4a3fa0 0%, #7c6af7 100%) !important;
        color: white !important;
        font-weight: 600 !important;
        font-size: 1.05rem !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.65rem 2.5rem !important; /* Smooth professional padding shape */
        width: auto !important;
        min-width: 160px !important; /* Perfect uniform dashboard geometry box */
        box-shadow: 0 4px 15px rgba(124, 106, 247, 0.25) !important;
    }
    
    .link-wrapper {
        text-align: center;
        margin-top: 15px;
    }
    div.link-wrapper button {
        background: transparent !important;
        color: #7c6af7 !important;
        border: none !important;
        box-shadow: none !important;
        font-size: 0.88rem !important;
        font-weight: 500 !important;
    }
    div.link-wrapper button:hover {
        color: #bfa6ff !important;
        text-decoration: underline !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(
        '<div class="auth-shell"><a href="?view=landing">Back to landing</a><span>Secure BizVision AI workspace access</span></div>',
        unsafe_allow_html=True,
    )

    # State routers initializations
    if "reset_mode" not in st.session_state:
        st.session_state["reset_mode"] = "login"
    if "show_forgot_link" not in st.session_state:
        st.session_state["show_forgot_link"] = False

    with st.container():
        st.markdown('<div class="custom-login-box"></div>', unsafe_allow_html=True)
        
        current_mode = st.session_state["reset_mode"]
        
        #  1 LOGIN VIEW MODE (CENTERED STRINGS) 
        if current_mode == "login":
            st.markdown(brand_header(BRAND_NAME, "Sign in to continue"), unsafe_allow_html=True)
            
            with st.form(key="form_execution_login_isolated"):
                username_input = st.text_input("Username", placeholder="Enter username", key="login_username_widget")
                password_input = st.text_input("Password", type="password", placeholder="Enter password", key="login_password_widget")
                login_btn = st.form_submit_button("Sign In")

                if login_btn:
                    if not username_input or not password_input:
                        st.error("Please enter both username and password.")
                    else:
                        username_clean = username_input.strip()
                        locked_until = get_login_lock(username_clean)
                        if locked_until:
                            wait_minutes = max(1, int((locked_until - datetime.now()).total_seconds() // 60) + 1)
                            st.error(f"Too many failed login attempts. Try again in about {wait_minutes} minutes.")
                            user = None
                        else:
                            user = authenticate(username_clean, password_input)
                        if user:
                            clear_login_failures(user["username"])
                            st.session_state["logged_in"] = True
                            st.session_state["role"] = user["role"]
                            st.session_state["username"] = user["username"]
                            st.session_state["current_page"] = "Dashboard"
                            st.session_state["show_forgot_link"] = False
                            log_activity(user["username"], "Login", "Session authorized.")
                            st.rerun()
                        else:
                            if not locked_until:
                                record_login_failure(username_clean)
                            st.error("Invalid username, password, or inactive account.")
                            
            st.markdown('<div class="link-wrapper">', unsafe_allow_html=True)
            link_col1, link_col2 = st.columns(2)
            with link_col1:
                if st.button("Forgot Password?", key="lnk_switch_to_forgot"):
                    st.session_state["reset_mode"] = "forgot"
                    st.rerun()
            with link_col2:
                if st.button("Create Account", key="lnk_switch_to_register"):
                    st.session_state["show_forgot_link"] = False
                    st.session_state["reset_mode"] = "register"
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        #  2 PUBLIC REGISTRATION VIEW MODE
        elif current_mode == "register":
            st.markdown(brand_header("Create Account", "Start with a standard user workspace"), unsafe_allow_html=True)

            with st.form(key="form_execution_register_isolated"):
                reg_username = st.text_input("Username", placeholder="e.g. harshit_data", key="register_username_widget")
                reg_email = st.text_input("Email Address", placeholder="name@example.com", key="register_email_widget")
                reg_password = st.text_input("Password", type="password", placeholder="Choose a password", key="register_password_widget")
                reg_confirm = st.text_input("Confirm Password", type="password", placeholder="Re-enter password", key="register_confirm_widget")

                if reg_password:
                    strength, label = password_strength(reg_password)
                    colors = ["#ff4b4b", "#ffaa00", "#ccff00", "#00ffcc"]
                    display_strength = max(strength, 1)
                    st.markdown(
                        f"<p style='font-size:0.8rem; margin:0;'>Strength: <span style='color:{colors[display_strength-1]};'>{label}</span></p>",
                        unsafe_allow_html=True
                    )
                    st.progress(strength / 4)

                register_btn = st.form_submit_button("Create Account")

                if register_btn:
                    username = reg_username.strip()
                    email = reg_email.strip()
                    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

                    if not username or not email or not reg_password or not reg_confirm:
                        st.error("Please fill all registration fields.")
                    elif not re.match(r"^[a-zA-Z0-9_]{3,30}$", username):
                        st.error("Username must be 3-30 characters and can contain only letters, numbers, and underscores.")
                    elif not re.match(email_pattern, email):
                        st.error("Invalid email format.")
                    elif reg_password != reg_confirm:
                        st.error("Password and Confirm Password do not match.")
                    elif len(reg_password) < 6:
                        st.error("Password must be at least 6 characters long.")
                    else:
                        exists, message = user_exists(username, email)
                        if exists:
                            st.error(message)
                        else:
                            generated_otp = str(secrets.randbelow(899999) + 100000)
                            if can_skip_email_verification():
                                if create_user(username, email, reg_password, "user"):
                                    log_activity(username, "Register", "Self-service user account created without email verification.")
                                    st.success("Account created successfully. Please sign in.")
                                    st.session_state["reset_mode"] = "login"
                                    st.session_state["show_forgot_link"] = False
                                    st.rerun()
                                else:
                                    st.error("Account creation failed. Try a different username or email.")
                            else:
                                sent, message = send_otp_email(email, username, generated_otp)
                                if sent:
                                    st.session_state["pending_registration"] = {
                                        "username": username,
                                        "email": email,
                                        "password": reg_password,
                                    }
                                    st.session_state["registration_otp"] = generated_otp
                                    st.session_state["registration_expires_at"] = (datetime.now() + timedelta(minutes=10)).isoformat()
                                    st.session_state["registration_attempts"] = 0
                                    st.session_state["reset_mode"] = "verify_register"
                                    st.success(f"Verification OTP sent to {mask_email(email)}.")
                                    st.rerun()
                                else:
                                    st.error(message)
                                    st.caption("Email verification is required. Configure SMTP settings or set ALLOW_UNVERIFIED_REGISTRATION=true only for local demos.")

            st.markdown('<div class="link-wrapper">', unsafe_allow_html=True)
            if st.button("Back to Login", key="lnk_register_back_to_login"):
                st.session_state["show_forgot_link"] = False
                st.session_state["reset_mode"] = "login"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        #  3 FORGOT VIEW MODE 
        elif current_mode == "forgot":
            st.markdown(brand_header(BRAND_NAME, "Reset access securely"), unsafe_allow_html=True)
            
            with st.form(key="form_execution_forgot_isolated"):
                target_user = st.text_input("Username or Email", placeholder="Enter your username or registered email", key="forgot_username_widget")
                gen_otp_btn = st.form_submit_button("Send OTP")
                
                if gen_otp_btn:
                    if target_user:
                        conn = get_conn()
                        user = conn.execute(
                            "SELECT * FROM users WHERE lower(username)=lower(?) OR lower(email)=lower(?)",
                            (target_user.strip(), target_user.strip())
                        ).fetchone()
                        conn.close()
                        
                        if user:
                            generated_otp = str(secrets.randbelow(899999) + 100000)
                            sent, message = send_otp_email(user["email"], user["username"], generated_otp)
                            if sent:
                                st.session_state["recovery_otp"] = generated_otp
                                st.session_state["recovery_user"] = user["username"]
                                st.session_state["recovery_email"] = user["email"]
                                st.session_state["recovery_expires_at"] = (datetime.now() + timedelta(minutes=10)).isoformat()
                                st.session_state["recovery_attempts"] = 0
                                st.session_state["reset_mode"] = "verify"
                                log_activity(user["username"], "Password OTP Sent", f"OTP sent to {mask_email(user['email'])}")
                                st.success(f"OTP sent to {mask_email(user['email'])}.")
                                st.rerun()
                            else:
                                st.error(message)
                                st.caption("Admin must configure SMTP settings in Streamlit secrets for email OTP delivery.")
                        else:
                            st.error("No account found for this username or email.")
                    else:
                        st.warning("Please enter your username or registered email.")
                        
            st.markdown('<div class="link-wrapper">', unsafe_allow_html=True)
            if st.button("Back to Login", key="lnk_back_to_login_view"):
                st.session_state["show_forgot_link"] = False 
                st.session_state["reset_mode"] = "login"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        elif current_mode == "verify_register":
            pending = st.session_state.get("pending_registration") or {}
            st.markdown(brand_header("Verify Email", "Confirm ownership before account creation"), unsafe_allow_html=True)
            if pending.get("email"):
                st.info(f"Enter the OTP sent to {mask_email(pending['email'])}.")

            with st.form(key="form_execution_register_verify"):
                input_otp = st.text_input("Enter 6-Digit OTP", placeholder="", key="register_verify_otp_widget")
                verify_btn = st.form_submit_button("Verify & Create Account")

                if verify_btn:
                    expires_raw = st.session_state.get("registration_expires_at")
                    expired = True
                    if expires_raw:
                        expired = datetime.now() > datetime.fromisoformat(expires_raw)
                    if expired:
                        st.error("Registration OTP expired. Please create the account again.")
                        st.session_state["reset_mode"] = "register"
                        for key in ["pending_registration", "registration_otp", "registration_expires_at", "registration_attempts"]:
                            st.session_state.pop(key, None)
                        st.rerun()
                    elif st.session_state.get("registration_attempts", 0) >= 5:
                        st.error("Too many incorrect attempts. Please restart registration.")
                        st.session_state["reset_mode"] = "register"
                        for key in ["pending_registration", "registration_otp", "registration_expires_at", "registration_attempts"]:
                            st.session_state.pop(key, None)
                        st.rerun()
                    elif input_otp == st.session_state.get("registration_otp") and pending:
                        if create_user(pending["username"], pending["email"], pending["password"], "user"):
                            log_activity(pending["username"], "Register", "Self-service account created after email OTP verification.")
                            st.success("Email verified. Account created successfully. Please sign in.")
                            st.session_state["reset_mode"] = "login"
                            for key in ["pending_registration", "registration_otp", "registration_expires_at", "registration_attempts"]:
                                st.session_state.pop(key, None)
                            st.rerun()
                        else:
                            st.error("Account creation failed. Try a different username or email.")
                    else:
                        st.session_state["registration_attempts"] = st.session_state.get("registration_attempts", 0) + 1
                        st.error("Invalid verification code.")

            st.markdown('<div class="link-wrapper">', unsafe_allow_html=True)
            if st.button("Cancel Registration", key="lnk_cancel_register_verify"):
                st.session_state["reset_mode"] = "register"
                for key in ["pending_registration", "registration_otp", "registration_expires_at", "registration_attempts"]:
                    st.session_state.pop(key, None)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        #  4 VERIFY VIEW MODE 
        elif current_mode == "verify":
            st.markdown(brand_header("Security Key", "Enter verification token"), unsafe_allow_html=True)
            
            if st.session_state.get("recovery_email"):
                st.info(f"Enter the OTP sent to {mask_email(st.session_state.get('recovery_email'))}.")
            else:
                st.info("Enter the OTP sent to your registered email.")
            
            with st.form(key="form_execution_verify_isolated"):
                input_otp = st.text_input("Enter 6-Digit OTP", placeholder="", key="verify_otp_widget")
                new_pwd = st.text_input("New Password", type="password", placeholder="", key="verify_pwd_widget")
                confirm_pwd = st.text_input("Confirm New Password", type="password", placeholder="", key="verify_confirm_widget")
                reset_submit = st.form_submit_button("Deploy New Password")
                
                if reset_submit:
                    expires_raw = st.session_state.get("recovery_expires_at")
                    expired = True
                    if expires_raw:
                        expired = datetime.now() > datetime.fromisoformat(expires_raw)

                    if expired:
                        st.error("OTP expired. Please request a new code.")
                        st.session_state["reset_mode"] = "forgot"
                        st.session_state.pop("recovery_otp", None)
                        st.session_state.pop("recovery_expires_at", None)
                        st.rerun()
                    elif reset_attempts_exceeded():
                        st.error("Too many incorrect attempts. Please request a new OTP.")
                        st.session_state["reset_mode"] = "forgot"
                        st.session_state.pop("recovery_otp", None)
                        st.session_state.pop("recovery_expires_at", None)
                        st.rerun()
                    elif input_otp == st.session_state.get("recovery_otp"):
                        if new_pwd == confirm_pwd:
                            if len(new_pwd) >= 6:
                                conn = get_conn()
                                fresh_salt, hashed_val = hash_password(new_pwd)
                                
                                conn.execute(
                                    "UPDATE users SET password = ?, salt = ? WHERE username = ?",
                                    (hashed_val, fresh_salt, st.session_state.get("recovery_user"))
                                )
                                conn.commit()
                                conn.close()
                                
                                st.success("Access credentials updated. Proceeding to login.")
                                log_activity(st.session_state.get("recovery_user"), "Password Reset", "Password reset completed after email OTP verification.")
                                st.session_state["show_forgot_link"] = False 
                                st.session_state["reset_mode"] = "login"
                                st.session_state.pop("recovery_otp", None)
                                st.session_state.pop("recovery_user", None)
                                st.session_state.pop("recovery_email", None)
                                st.session_state.pop("recovery_expires_at", None)
                                st.session_state.pop("recovery_attempts", None)
                                st.rerun()
                            else:
                                st.error("Password string must contain at least 6 characters.")
                        else:
                            st.error("Matching logic check failed: Mismatch strings.")
                    else:
                        st.session_state["recovery_attempts"] = st.session_state.get("recovery_attempts", 0) + 1
                        st.error("Token verification string match failed.")
                        
            st.markdown('<div class="link-wrapper">', unsafe_allow_html=True)
            if st.button("Cancel Process", key="lnk_cancel_otp_flow_view"):
                st.session_state["show_forgot_link"] = False
                st.session_state["reset_mode"] = "login"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

#  SINGLE DIRECT PAGE EXECUTION BRIDGE 
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if __name__ == "__main__":
    if not st.session_state["logged_in"]:
        show_login_page()
    else:
        st.markdown("<div style='text-align:center; padding:50px;'><h3>Dashboard Authenticated Successfully</h3><p style='color:#6060a0;'>Use the main sidebar panel to jump to workspaces.</p></div>", unsafe_allow_html=True)

