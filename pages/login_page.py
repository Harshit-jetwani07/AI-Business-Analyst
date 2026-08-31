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
from utils.branding import BRAND_NAME, BRAND_TAGLINE, brand_icon_data_uri, brand_logo_data_uri


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
    """Render the logged-out landing page with embedded auth access."""
    if "reset_mode" not in st.session_state:
        st.session_state["reset_mode"] = "login"
    requested_auth_tab = st.query_params.get("auth_tab", "")
    if (
        requested_auth_tab in {"login", "register"}
        and requested_auth_tab != st.session_state.get("auth_tab")
    ):
        st.session_state["auth_tab"] = requested_auth_tab
        st.session_state["reset_mode"] = requested_auth_tab
    show_landing_page()


def set_auth_mode(mode: str):
    st.session_state["reset_mode"] = mode
    if mode in {"login", "register"}:
        st.session_state["auth_tab"] = mode
        st.query_params["auth_tab"] = mode
    else:
        st.session_state["auth_tab"] = mode
        st.query_params.clear()


def show_landing_page():
    """Render premium scrollable marketing landing page for logged-out users."""
    logo_data_uri = brand_logo_data_uri()
    icon_data_uri = brand_icon_data_uri()
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
    :root {
        --bv-bg: #0a0a0f;
        --bv-surface: #0d0d14;
        --bv-purple: #7c6af7;
        --bv-cyan: #00d4ff;
        --bv-text: #ffffff;
        --bv-muted: #9ca3af;
        --bv-line: rgba(156, 163, 175, .16);
    }
    html { scroll-behavior: smooth; }
    .stApp {
        background:
            radial-gradient(circle at 18% 12%, rgba(69, 98, 255, 0.22), transparent 34%),
            radial-gradient(circle at 82% 8%, rgba(124, 58, 237, 0.18), transparent 34%),
            linear-gradient(135deg, #070b15 0%, #0a0e1a 48%, #131826 100%) !important;
        background-size: auto, auto, auto !important;
        color: #f7fbff;
    }
    [data-testid="stSidebar"] { display: none !important; }
    [data-testid="stHeader"],
    [data-testid="stToolbar"],
    .stDeployButton {
        display: none !important;
    }
    header[data-testid="stHeader"] {
        height: 0 !important;
        min-height: 0 !important;
        background: transparent !important;
    }
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
        padding: 54px clamp(20px, 5vw, 72px);
        max-width: 1200px;
        margin: 0 auto;
    }
    .bv-section + .bv-section { padding-top: 18px; }
    #features { padding-bottom: 24px; }
    #how { padding-top: 0; }
    .bv-hero {
        min-height: 720px;
        display: grid;
        grid-template-columns: minmax(0, 1.04fr) minmax(420px, .96fr);
        gap: clamp(34px, 5vw, 70px);
        align-items: center;
        position: relative;
    }
    .bv-auth-hero {
        max-width: 1200px;
        margin: 0 auto;
        padding: 80px clamp(20px, 5vw, 72px);
        position: relative;
    }
    .bv-pitch {
        min-height: 560px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        position: relative;
        animation: bvEnter .72s ease both;
    }
    .bv-mini-brand {
        display: inline-flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 22px;
    }
    .bv-mini-brand img {
        width: 170px;
        height: auto;
        display: block;
    }
    .bv-mini-brand span {
        color: #67e8f9;
        font-weight: 850;
        font-size: .9rem;
    }
    .bv-pitch h1 {
        margin: 0;
        color: #ffffff;
        font-size: clamp(3rem, 5.1vw, 5rem);
        line-height: .98;
        letter-spacing: -0.04em;
        font-weight: 900;
        max-width: 760px;
    }
    .bv-pitch p {
        color: #aeb9d8;
        font-size: clamp(1.05rem, 1.7vw, 1.22rem);
        line-height: 1.7;
        max-width: 660px;
        margin: 24px 0 0;
    }
    .bv-floating-shape {
        position: absolute;
        width: 74px;
        height: 74px;
        border-radius: 22px;
        border: 1px solid rgba(0,212,255,.22);
        background: linear-gradient(135deg, rgba(124,60,255,.18), rgba(0,212,255,.10));
        box-shadow: 0 18px 48px rgba(47,107,255,.16);
        transform: rotate(12deg);
        right: 8%;
        top: 18%;
        opacity: .72;
    }
    .bv-floating-shape.two {
        width: 42px;
        height: 42px;
        border-radius: 14px;
        right: 20%;
        top: 72%;
        transform: rotate(-18deg);
    }
    @keyframes bvEnter { from { opacity: 0; transform: translateY(18px); } to { opacity: 1; transform: translateY(0); } }
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
        height: var(--h);
        min-height: 22px;
        border-radius: 10px 10px 4px 4px;
        background: linear-gradient(180deg, #00d4ff, #7c3cff);
        transform-origin: bottom;
        animation: bvGrow 1.15s cubic-bezier(.22, 1, .36, 1) both, bvGlow 3s ease-in-out infinite;
        animation-delay: var(--d, 0ms);
    }
    .bv-line-chart {
        height: 138px;
        margin-top: 12px;
        border-radius: 16px;
        overflow: hidden;
        border: 1px solid rgba(148, 163, 184, .12);
        background:
            linear-gradient(rgba(255,255,255,.06) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,.06) 1px, transparent 1px),
            rgba(8,13,31,.62);
        background-size: 34px 34px;
    }
    .bv-line-chart svg { width: 100%; height: 100%; display: block; }
    .bv-line-chart path.main-line {
        stroke-dasharray: 520;
        stroke-dashoffset: 520;
        animation: bvDraw 1.45s ease-out forwards;
    }
    .bv-line-chart .area { opacity: .22; }
    @keyframes bvGrow { from { transform: scaleY(.08); opacity: .32; } to { transform: scaleY(1); opacity: 1; } }
    @keyframes bvGlow { 0%,100% { filter: drop-shadow(0 0 0 rgba(0,212,255,0)); } 50% { filter: drop-shadow(0 0 10px rgba(0,212,255,.28)); } }
    @keyframes bvDraw { to { stroke-dashoffset: 0; } }
    .bv-stats {
        max-width: 1200px;
        margin: 0 auto;
        padding: 22px clamp(20px, 5vw, 72px) 24px;
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 24px;
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
    .bv-section-title { text-align: center; max-width: 760px; margin: 0 auto 48px; }
    .bv-section-title h2 { margin:0; font-size: clamp(2rem, 4vw, 3.4rem); line-height: 1.05; color:#fff; letter-spacing: -0.035em; }
    .bv-section-title p { color:#aeb9d8; font-size: 1.05rem; line-height:1.65; margin: 16px 0 0; }
    .bv-feature-grid { display:grid; grid-template-columns: repeat(3, 1fr); gap: 24px; }
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
        border-color: rgba(148, 163, 184, .15);
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
    .bv-feature h3 a, .bv-feature h3 svg { display: none !important; }
    .bv-feature p, .bv-step p, .bv-quote p { color:#aeb9d8; line-height:1.55; margin:0; }
    .bv-timeline { display:grid; grid-template-columns: repeat(4, 1fr); gap: 24px; position:relative; }
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
        padding: 20px;
        overflow: hidden;
    }
    .bv-product-layout { display:grid; grid-template-columns: 220px 1fr; gap: 24px; }
    .bv-side {
        border-radius: 20px;
        background: rgba(255,255,255,.05);
        padding: 14px;
        min-height: 360px;
        display: flex;
        flex-direction: column;
        gap: 14px;
    }
    .bv-workspace {
        display: grid;
        grid-template-columns: 34px 1fr;
        gap: 10px;
        align-items: center;
        padding-bottom: 14px;
        border-bottom: 1px solid rgba(148,163,184,.13);
    }
    .bv-avatar {
        width: 34px;
        height: 34px;
        border-radius: 50%;
        background: linear-gradient(135deg, #7c3cff, #00d4ff);
        box-shadow: 0 0 22px rgba(0,212,255,.18);
    }
    .bv-workspace-name {
        color: #f7fbff;
        font-size: .82rem;
        font-weight: 850;
        line-height: 1.2;
    }
    .bv-plan-badge {
        display: inline-flex;
        width: fit-content;
        margin-top: 4px;
        padding: 3px 7px;
        border-radius: 999px;
        border: 1px solid rgba(80,240,200,.28);
        color: #50f0c8;
        background: rgba(80,240,200,.08);
        font-size: .66rem;
        font-weight: 850;
    }
    .bv-side-nav {
        display: flex;
        flex-direction: column;
        gap: 5px;
        flex: 1;
    }
    .bv-nav-item {
        display: flex;
        align-items: center;
        gap: 9px;
        min-height: 32px;
        padding: 0 9px;
        border-radius: 10px;
        color: #aeb9d8;
        font-size: .78rem;
        font-weight: 780;
        border-left: 3px solid transparent;
    }
    .bv-nav-item svg {
        width: 17px;
        height: 17px;
        flex: 0 0 17px;
        stroke: currentColor;
    }
    .bv-nav-item.active {
        color: #ffffff;
        background: linear-gradient(135deg, rgba(124,60,255,.35), rgba(0,212,255,.16));
        border-left-color: #67e8f9;
        box-shadow: inset 0 0 0 1px rgba(103,232,249,.15);
    }
    .bv-nav-item.muted {
        margin-top: auto;
        color: #8b98bb;
        border-top: 1px solid rgba(148,163,184,.12);
        border-radius: 0 0 10px 10px;
        padding-top: 11px;
    }
    .bv-main-preview { display:grid; grid-template-columns: repeat(3, 1fr); gap: 24px; align-items: stretch; }
    .bv-main-preview .performance-card { grid-column: 1 / 3; min-height: 260px; }
    .bv-main-preview .summary-card { grid-column: 3; min-height: 260px; }
    .bv-main-preview .performance-card .bv-line-chart { height: 188px; }
    .bv-security-row { display:flex; flex-wrap:wrap; gap: 12px; justify-content:center; margin-bottom: 24px; }
    .bv-badge {
        border:1px solid rgba(148,163,184,.16);
        border-radius:999px;
        padding: 12px 16px;
        color:#dbeafe;
        background: rgba(255,255,255,.055);
        font-weight:800;
    }
    .bv-pricing-card {
        max-width: 620px;
        margin: 0 auto;
        border: 1px solid rgba(103,232,249,.24);
        border-radius: 24px;
        background: linear-gradient(145deg, rgba(255,255,255,.075), rgba(255,255,255,.035));
        padding: 28px;
        text-align: center;
        box-shadow: 0 24px 62px rgba(0,0,0,.22);
    }
    .bv-pricing-card strong {
        display: block;
        color: #ffffff;
        font-size: clamp(1.8rem, 3vw, 2.55rem);
        line-height: 1.05;
        margin-bottom: 10px;
    }
    .bv-pricing-card p { color: #aeb9d8; line-height: 1.6; margin: 0 0 18px; }
    .bv-pricing-points {
        display: flex;
        justify-content: center;
        flex-wrap: wrap;
        gap: 10px;
        color: #dbeafe;
        font-size: .86rem;
        font-weight: 800;
    }
    .bv-pricing-points span {
        border: 1px solid rgba(148,163,184,.16);
        border-radius: 999px;
        background: rgba(255,255,255,.055);
        padding: 8px 12px;
    }
    .bv-quotes { display:grid; grid-template-columns: repeat(3, 1fr); gap:24px; }
    .bv-quote strong { display:block; color:#fff; margin-top: 16px; }
    .bv-final {
        max-width: none;
        position: relative;
        overflow: hidden;
        margin: 0 clamp(18px, 4vw, 58px);
        isolation: isolate;
        border-radius: 24px;
        border: 1px solid transparent;
        background:
            linear-gradient(145deg, rgba(10,10,15,.94), rgba(13,15,28,.90)) padding-box,
            linear-gradient(135deg, rgba(124,106,247,.95), rgba(0,212,255,.82)) border-box;
        text-align:center;
        padding: 82px clamp(22px, 5vw, 72px);
        box-shadow:
            0 34px 110px rgba(0, 0, 0, .48),
            0 0 72px rgba(124, 106, 247, .18),
            0 0 90px rgba(0, 212, 255, .12);
        backdrop-filter: blur(18px);
    }
    .bv-final::before {
        content: "";
        position: absolute;
        inset: -120px;
        z-index: -2;
        background:
            radial-gradient(circle at 18% 12%, rgba(124,106,247,.24), transparent 26%),
            radial-gradient(circle at 86% 78%, rgba(0,212,255,.22), transparent 28%),
            radial-gradient(circle at 52% 10%, rgba(124,106,247,.13), transparent 22%);
        filter: blur(120px);
        pointer-events: none;
    }
    .bv-final::after {
        content: "";
        position: absolute;
        inset: 0;
        z-index: -1;
        background-image:
            radial-gradient(circle, rgba(255,255,255,.34) 0 1px, transparent 1px),
            linear-gradient(180deg, rgba(255,255,255,.06), transparent 38%, rgba(0,212,255,.035));
        background-size: 18px 18px, 100% 100%;
        opacity: .045;
        pointer-events: none;
    }
    .bv-final h2, .bv-final p, .bv-final .bv-btn, .bv-final-trust { position: relative; z-index: 1; }
    .bv-final h2 { color:#fff; font-size: clamp(2.2rem, 5vw, 4.2rem); margin:0 0 16px; letter-spacing:-.04em; }
    .bv-final-accent {
        background: linear-gradient(135deg, #ffffff 0%, #c9c2ff 42%, #8fefff 100%);
        -webkit-background-clip: text;
        color: transparent;
    }
    .bv-final p {
        color: #b8c4e4;
        font-size:1.1rem;
        line-height: 1.65;
        margin: 0 auto 30px;
        max-width: 720px;
    }
    .bv-final .bv-btn.primary {
        min-height: 52px;
        padding: 0 28px;
        gap: 9px;
        background: linear-gradient(135deg, #7c6af7 0%, #5f8dff 48%, #00d4ff 100%);
        box-shadow:
            0 18px 42px rgba(0, 212, 255, .22),
            0 18px 54px rgba(124, 106, 247, .24);
    }
    .bv-btn-arrow {
        font-size: 1.05rem;
        line-height: 1;
    }
    .bv-final .bv-btn.primary:hover {
        transform: translateY(-3px) scale(1.03);
        box-shadow:
            0 22px 52px rgba(0, 212, 255, .34),
            0 24px 66px rgba(124, 106, 247, .34);
    }
    .bv-final-trust {
        display: flex;
        justify-content: center;
        flex-wrap: wrap;
        gap: 12px;
        margin-top: 24px;
        color: #dce6ff;
        font-weight: 800;
        font-size: .9rem;
    }
    .bv-final-trust span {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        border: 1px solid rgba(143,239,255,.24);
        border-radius: 999px;
        background: rgba(10, 10, 15, .44);
        padding: 9px 13px;
        box-shadow: inset 0 1px 0 rgba(255,255,255,.06);
        transition: border-color .22s ease, color .22s ease, transform .22s ease;
    }
    .bv-trust-check {
        color: #00d4ff;
        font-weight: 900;
    }
    .bv-final-trust span:hover {
        border-color: rgba(124,106,247,.62);
        color: #ffffff;
        transform: translateY(-1px);
    }
    .bv-footer {
        position: relative;
        overflow: hidden;
        margin-top: 70px;
        padding: 72px clamp(20px, 5vw, 72px) 34px;
        border-top: 1px solid rgba(124,106,247,.16);
        background:
            radial-gradient(circle at 16% 0%, rgba(124,106,247,.12), transparent 30%),
            radial-gradient(circle at 88% 18%, rgba(0,212,255,.10), transparent 26%),
            linear-gradient(180deg, var(--bv-bg), var(--bv-surface));
        color: var(--bv-muted);
        box-shadow: inset 0 1px 0 rgba(255,255,255,.04);
    }
    .bv-footer-grid {
        display: grid;
        grid-template-columns: minmax(260px, 1.55fr) repeat(3, minmax(140px, .72fr));
        gap: clamp(26px, 4vw, 54px);
        max-width: 1200px;
        margin: 0 auto;
        padding: 0;
    }
    .bv-footer-brand {
        max-width: 410px;
    }
    .bv-footer-logo {
        display: inline-flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 14px;
    }
    .bv-footer-logo img {
        width: auto;
        height: 32px;
        margin: 0;
    }
    .bv-footer-logo span {
        color: var(--bv-text);
        font-size: 1.08rem;
        font-weight: 900;
        letter-spacing: 0;
    }
    .bv-footer-kicker {
        margin: 0;
        color: var(--bv-muted);
        font-size: .95rem;
        font-weight: 650;
        line-height: 1.7;
    }
    .bv-footer-col h4 {
        color: var(--bv-text);
        margin: 0 0 16px;
        font-size: .88rem;
        font-weight: 850;
        text-transform: uppercase;
        letter-spacing: .08em;
    }
    .bv-footer-col a {
        display: block;
        width: fit-content;
        color: var(--bv-muted);
        text-decoration: none;
        font-weight: 700;
        font-size: .94rem;
        margin: 10px 0;
        transition: color .22s ease, transform .22s ease;
    }
    .bv-footer-col a:hover {
        color: var(--bv-cyan);
        transform: translateX(2px);
    }
    .bv-socials {
        display:flex;
        gap: 10px;
        flex-wrap: wrap;
    }
    .bv-socials a {
        width: 40px;
        height: 40px;
        display:flex;
        align-items:center;
        justify-content:center;
        margin: 0;
        border-radius: 999px;
        border:1px solid rgba(156,163,175,.22);
        background:rgba(255,255,255,.025);
        color: #dce6ff;
        transition: border-color .22s ease, box-shadow .22s ease, color .22s ease, transform .22s ease;
    }
    .bv-socials a:hover {
        color: #ffffff;
        border-color: rgba(0,212,255,.58);
        box-shadow: 0 0 24px rgba(0,212,255,.16), 0 0 28px rgba(124,106,247,.14);
        transform: translateY(-2px);
    }
    .bv-socials svg {
        width: 18px;
        height: 18px;
        fill: none;
        stroke: currentColor;
        stroke-width: 2;
        stroke-linecap: round;
        stroke-linejoin: round;
    }
    .bv-footer-divider {
        max-width: 1200px;
        height: 1px;
        margin: 42px auto 24px;
        background: linear-gradient(90deg, transparent, rgba(124,106,247,.32), rgba(0,212,255,.28), transparent);
    }
    .bv-footer-bottom {
        max-width: 1200px;
        margin: 0 auto;
        display:flex;
        align-items: center;
        justify-content:space-between;
        gap:18px;
        flex-wrap:wrap;
        color: var(--bv-muted);
        font-size:.88rem;
    }
    .bv-footer-bottom-links {
        display:flex;
        align-items:center;
        gap: 10px;
    }
    .bv-footer-bottom-links a {
        display: inline-flex;
        color: var(--bv-muted);
        text-decoration: none;
        font-weight: 750;
        transition: color .22s ease;
    }
    .bv-footer-bottom-links a:hover { color: var(--bv-cyan); }
    .bv-footer-dot { color: rgba(156,163,175,.45); }
    @media (max-width: 980px) {
        .bv-links { display:none; }
        .bv-hero { grid-template-columns: 1fr; min-height: auto; padding-top: 40px; }
        .bv-dashboard { min-height: auto; }
        .bv-stats, .bv-feature-grid, .bv-timeline, .bv-quotes { grid-template-columns: repeat(2, 1fr); }
        .bv-product-layout { grid-template-columns: 1fr; }
        .bv-footer-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    @media (max-width: 640px) {
        .bv-nav { align-items:flex-start; flex-direction:column; }
        .bv-nav-actions { width:100%; }
        .bv-nav-actions .bv-btn { flex:1; }
        .bv-section, .bv-auth-hero, .bv-stats, .bv-footer { padding-top: 46px; padding-bottom: 46px; }
        .bv-section-title { margin-bottom: 32px; }
        .bv-hero-actions .bv-btn { width:100%; }
        .bv-preview-grid, .bv-stats, .bv-feature-grid, .bv-timeline, .bv-quotes, .bv-main-preview { grid-template-columns: 1fr; gap: 16px; }
        .bv-main-preview .performance-card, .bv-main-preview .summary-card { grid-column:auto; min-height: auto; }
        .bv-main-preview .performance-card .bv-line-chart { height: 150px; }
        .bv-footer-grid { grid-template-columns: 1fr; }
        .bv-footer-bottom { flex-direction: column; align-items: flex-start; }
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
          <a href="#security">Security</a>
        </div>
        <div class="bv-nav-actions">
          <a class="bv-btn" href="?auth_tab=login#top-auth">Sign In</a>
          <a class="bv-btn primary" href="?auth_tab=register#top-auth">Get Started</a>
        </div>
      </nav>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div id="top-auth" class="bv-auth-hero">', unsafe_allow_html=True)
    pitch_col, auth_col = st.columns([1.15, 0.85], gap="large")
    with pitch_col:
        st.markdown(f"""
        <div class="bv-pitch">
          <div class="bv-floating-shape"></div>
          <div class="bv-floating-shape two"></div>
          <div class="bv-mini-brand"><img src="{logo_data_uri}" alt="{BRAND_NAME} logo"><span>{BRAND_TAGLINE}</span></div>
          <h1>Turn Your Business Data Into <span class="bv-gradient-text">Instant AI Insights</span></h1>
          <p>A premium AI analytics workspace for business teams. Upload your data, chat with AI, detect anomalies, forecast trends, and export polished reports from one connected dashboard.</p>
          <div class="bv-hero-actions">
            <a class="bv-btn primary" href="#features">Explore Features</a>
            <a class="bv-btn" href="#preview">See Live Demo</a>
          </div>
          <div class="bv-mini-proof">
            <span>10,000+ rows analyzed</span><span>4 AI providers</span><span>PBKDF2 passwords</span><span>Admin approvals</span>
          </div>
        </div>
        """, unsafe_allow_html=True)
    with auth_col:
        show_auth_step(embedded=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(f"""
    <div class="bv-page">
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

      <section class="bv-section" id="security">
        <div class="bv-section-title"><h2>Security & Privacy</h2><p>Built-in safeguards protect accounts, AI requests, and report approval workflows.</p></div>
        <div class="bv-feature-grid">
          <div class="bv-feature"><div class="bv-icon">PB</div><h3>PBKDF2 Password Hashing</h3><p>Passwords are salted and hashed before storage using PBKDF2-based credentials.</p></div>
          <div class="bv-feature"><div class="bv-icon">AI</div><h3>Masked AI Context</h3><p>Sensitive values are redacted before dataset summaries are sent to AI providers.</p></div>
          <div class="bv-feature"><div class="bv-icon">RB</div><h3>Role-Based Approval</h3><p>Admin workflows control dataset status and report approval before final use.</p></div>
          <div class="bv-feature"><div class="bv-icon">LK</div><h3>Login Lockout</h3><p>Repeated failed sign-in attempts trigger temporary account access lockouts.</p></div>
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
            <aside class="bv-side" aria-label="Product preview navigation">
              <div class="bv-workspace">
                <span class="bv-avatar" aria-hidden="true"></span>
                <span>
                  <span class="bv-workspace-name">Acme Retail Co.</span>
                  <span class="bv-plan-badge">Free Plan</span>
                </span>
              </div>
              <nav class="bv-side-nav">
                <span class="bv-nav-item active"><svg viewBox="0 0 24 24" fill="none" stroke-width="2"><path d="M4 13h7V4H4v9Z"/><path d="M13 20h7V4h-7v16Z"/><path d="M4 20h7v-5H4v5Z"/></svg>Dashboard</span>
                <span class="bv-nav-item"><svg viewBox="0 0 24 24" fill="none" stroke-width="2"><path d="M4 7c0 1.7 3.6 3 8 3s8-1.3 8-3-3.6-3-8-3-8 1.3-8 3Z"/><path d="M4 7v5c0 1.7 3.6 3 8 3s8-1.3 8-3V7"/><path d="M4 12v5c0 1.7 3.6 3 8 3s8-1.3 8-3v-5"/></svg>Datasets</span>
                <span class="bv-nav-item"><svg viewBox="0 0 24 24" fill="none" stroke-width="2"><path d="M5 5h14v10H8l-3 3V5Z"/><path d="M9 9h6"/><path d="M9 12h4"/></svg>AI Chat</span>
                <span class="bv-nav-item"><svg viewBox="0 0 24 24" fill="none" stroke-width="2"><path d="M4 18h16"/><path d="m5 15 4-4 4 3 6-7"/><path d="M17 7h2v2"/></svg>Forecasting</span>
                <span class="bv-nav-item"><svg viewBox="0 0 24 24" fill="none" stroke-width="2"><path d="M12 3 3 20h18L12 3Z"/><path d="M12 9v5"/><path d="M12 17h.01"/></svg>Anomaly Detection</span>
                <span class="bv-nav-item"><svg viewBox="0 0 24 24" fill="none" stroke-width="2"><path d="M7 3h7l4 4v14H7V3Z"/><path d="M14 3v5h5"/><path d="M9 13h6"/><path d="M9 17h6"/></svg>Reports</span>
                <span class="bv-nav-item muted"><svg viewBox="0 0 24 24" fill="none" stroke-width="2"><path d="M12 15.5A3.5 3.5 0 1 0 12 8a3.5 3.5 0 0 0 0 7.5Z"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2 3.4-.2-.1a1.7 1.7 0 0 0-2 .1 1.7 1.7 0 0 0-.9 1.6v.2H9.3V22a1.7 1.7 0 0 0-.9-1.6 1.7 1.7 0 0 0-2-.1l-.2.1-2-3.4.1-.1A1.7 1.7 0 0 0 4.6 15 1.7 1.7 0 0 0 3 14H2.8v-4H3a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9l-.1-.1 2-3.4.2.1a1.7 1.7 0 0 0 2-.1A1.7 1.7 0 0 0 9.3 2v-.2h5.4V2a1.7 1.7 0 0 0 .9 1.6 1.7 1.7 0 0 0 2 .1l.2-.1 2 3.4-.1.1a1.7 1.7 0 0 0-.3 1.9A1.7 1.7 0 0 0 21 10h.2v4H21a1.7 1.7 0 0 0-1.6 1Z"/></svg>Settings</span>
              </nav>
            </aside>
            <div class="bv-main-preview">
              <div class="bv-preview-card"><div class="bv-label">Rows</div><div class="bv-value">18.4K</div><div class="bv-chip">Parsed</div></div>
              <div class="bv-preview-card"><div class="bv-label">Charts</div><div class="bv-value">12</div><div class="bv-chip">Auto-generated</div></div>
              <div class="bv-preview-card"><div class="bv-label">Reports</div><div class="bv-value">PDF</div><div class="bv-chip">Ready</div></div>
              <div class="bv-preview-card performance-card">
                <div class="bv-label">Performance Chart</div>
                <div class="bv-line-chart">
                  <svg viewBox="0 0 520 138" preserveAspectRatio="none" aria-hidden="true">
                    <defs>
                      <linearGradient id="previewLine" x1="0" y1="0" x2="520" y2="0"><stop stop-color="#00d4ff"/><stop offset=".45" stop-color="#2f6bff"/><stop offset="1" stop-color="#9b6cff"/></linearGradient>
                      <linearGradient id="previewLineTwo" x1="0" y1="0" x2="520" y2="0"><stop stop-color="#9b6cff"/><stop offset=".5" stop-color="#7c3cff"/><stop offset="1" stop-color="#50f0c8"/></linearGradient>
                    </defs>
                    <path class="area" d="M16 108 C66 90 104 94 138 68 S218 30 268 56 S346 90 398 50 S462 38 504 32 L504 138 L16 138 Z" fill="url(#previewLine)"/>
                    <path class="main-line" d="M16 108 C66 90 104 94 138 68 S218 30 268 56 S346 90 398 50 S462 38 504 32" fill="none" stroke="url(#previewLine)" stroke-width="5" stroke-linecap="round"/>
                    <path class="main-line" d="M16 84 C74 76 98 42 154 58 S246 104 306 78 S398 26 504 64" fill="none" stroke="url(#previewLineTwo)" stroke-width="4" stroke-linecap="round" opacity=".95"/>
                  </svg>
                </div>
              </div>
              <div class="bv-preview-card summary-card"><div class="bv-label">AI Summary</div><p style="color:#dbeafe;line-height:1.55;margin-top:12px">Sales momentum increased in West region while returns need review in Electronics.</p></div>
            </div>
          </div>
        </div>
      </section>

      <section class="bv-section">
        <div class="bv-security-row">
          <span class="bv-badge">Private workspace</span><span class="bv-badge">Masked AI context</span><span class="bv-badge">Role-based access</span><span class="bv-badge">Admin review flow</span>
        </div>
        <div class="bv-section-title"><h2>Social proof</h2><p>Feedback from realistic business, review, and product evaluation workflows.</p></div>
        <div class="bv-quotes">
          <div class="bv-quote"><p>"BizVision AI helped me explain raw sales data like a complete business intelligence workflow."</p><strong>Priya Sharma - Business Analyst</strong></div>
          <div class="bv-quote"><p>"The dashboard feels practical because it includes quality checks, forecasting, and reports."</p><strong>Rohan Mehta - Data Reviewer</strong></div>
          <div class="bv-quote"><p>"A strong demo for showing how AI can support real business analysis decisions."</p><strong>Ananya Iyer - Product Mentor</strong></div>
        </div>
      </section>

      <section class="bv-section" id="pricing">
        <div class="bv-section-title"><h2>Simple pricing</h2><p>Start with the complete workspace and upgrade only when your deployment needs grow.</p></div>
        <div class="bv-pricing-card">
          <strong>Free</strong>
          <p>All core analytics, AI chat, forecasting, anomaly detection, quality scoring, and PDF reporting features are included.</p>
          <div class="bv-pricing-points"><span>No credit card required</span><span>All features included</span><span>Local demo ready</span></div>
        </div>
      </section>

      <section class="bv-final">
        <h2>Start Analyzing Your <span class="bv-final-accent">Data Today</span></h2>
        <p>Upload a file, ask questions, detect patterns, forecast trends, and export your report.</p>
        <a class="bv-btn primary" href="?auth_tab=register#top-auth">Get Started Free <span class="bv-btn-arrow" aria-hidden="true">→</span></a>
        <div class="bv-final-trust">
          <span><span class="bv-trust-check" aria-hidden="true">✓</span>No credit card required</span>
          <span><span class="bv-trust-check" aria-hidden="true">✓</span>Free forever plan</span>
          <span><span class="bv-trust-check" aria-hidden="true">✓</span>Setup in 2 minutes</span>
        </div>
      </section>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <footer class="bv-footer" id="resources">
      <div class="bv-footer-grid">
        <div class="bv-footer-brand bv-footer-col">
          <div class="bv-footer-logo">
            <img src="{icon_data_uri}" alt="{BRAND_NAME} icon">
            <span>{BRAND_NAME}</span>
          </div>
          <p class="bv-footer-kicker">{BRAND_TAGLINE}</p>
        </div>
        <div class="bv-footer-col">
          <h4>Product</h4>
          <a href="#features">Features</a>
          <a href="#preview">Dashboard</a>
          <a href="#how">Forecasting</a>
          <a href="#pricing">Reports</a>
        </div>
        <div class="bv-footer-col">
          <h4>Company</h4>
          <a href="#resources">About</a>
          <a href="#resources">Contact</a>
          <a href="#resources">Privacy Policy</a>
          <a href="#resources">Terms of Service</a>
        </div>
        <div class="bv-footer-col">
          <h4>Connect</h4>
          <div class="bv-socials">
            <a href="https://github.com/Harshit-jetwani07/AI-Business-Analyst" aria-label="GitHub">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 22v-4a4.8 4.8 0 0 0-1.3-3.6c4.3-.5 8.8-2.1 8.8-9.5a7.4 7.4 0 0 0-2-5.1 6.9 6.9 0 0 0-.1-5.1s-1.6-.5-5.3 2a18.2 18.2 0 0 0-9.6 0c-3.7-2.5-5.3-2-5.3-2a6.9 6.9 0 0 0-.1 5.1 7.4 7.4 0 0 0-2 5.1c0 7.4 4.5 9 8.8 9.5A4.8 4.8 0 0 0 9 18v4"/><path d="M9 18c-4.5 2-5-2-7-2"/></svg>
            </a>
            <a href="mailto:contact@bizvision.ai" aria-label="Email">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2Z"/><path d="m22 6-10 7L2 6"/></svg>
            </a>
            <a href="https://www.linkedin.com/" aria-label="LinkedIn">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-4 0v7h-4v-7a6 6 0 0 1 6-6Z"/><path d="M2 9h4v12H2z"/><path d="M4 4h.01"/></svg>
            </a>
          </div>
        </div>
      </div>
      <div class="bv-footer-divider"></div>
      <div class="bv-footer-bottom">
        <span>© 2026 {BRAND_NAME}. All rights reserved.</span>
        <span>Made with Streamlit</span>
        <span class="bv-footer-bottom-links">
          <a href="#resources">Privacy</a>
          <span class="bv-footer-dot">·</span>
          <a href="#resources">Terms</a>
        </span>
      </div>
    </footer>
    """, unsafe_allow_html=True)


def show_auth_step(embedded: bool = False):
    """Render the clean centered auth form."""
    logo_data_uri = brand_logo_data_uri()

    def render_brand_header(title: str) -> str:
        return (
            '<div class="brand-lockup">'
            f'<div class="brand-logo"><img src="{logo_data_uri}" alt="{BRAND_NAME} logo"></div>'
            '</div>'
            f'<div class="login-title">{title}</div>'
            f'<div class="login-sub">{BRAND_TAGLINE}</div>'
        )

    st.markdown("""
    <style>
    .stApp {
        background:
            radial-gradient(circle at 50% 0%, rgba(0, 212, 255, 0.18), transparent 34%),
            linear-gradient(135deg, #070b15 0%, #0a0e1a 48%, #131826 100%) !important;
        background-size: auto, auto !important;
    }
    [data-testid="stSidebar"] { display: none !important; }
    [data-testid="stHeader"],
    [data-testid="stToolbar"],
    .stDeployButton {
        display: none !important;
    }
    header[data-testid="stHeader"] {
        height: 0 !important;
        min-height: 0 !important;
        background: transparent !important;
    }
    .block-container { max-width: 100% !important; }
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
    
    div[data-testid="column"]:has(.custom-login-box) {
        position: relative !important;
        background:
            linear-gradient(180deg, rgba(255,255,255,.075), rgba(255,255,255,.03)),
            radial-gradient(circle at 50% 0%, rgba(0, 212, 255, 0.18), transparent 38%),
            linear-gradient(160deg, rgba(15,15,42,.98) 0%, rgba(20,20,46,.96) 100%) !important;
        border: 1px solid rgba(103, 232, 249, 0.42) !important;
        border-radius: 22px !important;
        padding: 34px 30px 30px !important;
        max-width: 470px !important;
        margin: 0 auto !important;
        box-shadow:
            0 28px 76px rgba(0, 0, 0, 0.5),
            0 0 0 1px rgba(255,255,255,.05) inset,
            0 0 46px rgba(0, 212, 255, 0.13) !important;
        animation: bvEnter .82s ease both;
    }
    div[data-testid="column"]:has(.custom-login-box)::before {
        content: "";
        position: absolute;
        inset: 10px;
        border: 1px solid rgba(255,255,255,.055);
        border-radius: 17px;
        pointer-events: none;
    }
    .custom-login-box { display: none !important; }
    .login-logo { font-size: 2.8rem; text-align: center; margin-bottom: 5px; }
    .brand-lockup {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 10px;
        margin-bottom: 22px;
    }
    .brand-logo {
        width: min(100%, 330px);
        min-height: 78px;
        margin: 0 auto;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 0 !important;
        background: transparent !important;
        border: 0 !important;
        border-radius: 0 !important;
        box-shadow: none !important;
    }
    .brand-logo img {
        width: 100%;
        max-height: 90px;
        object-fit: contain;
        filter: none;
    }
    .login-title { text-align: center; font-size: 1.85rem; font-weight: 800; color: #c8bcff; margin-bottom: 2px; }
    .login-sub { text-align: center; color: #8d88c7; font-size: 0.92rem; margin-bottom: 22px; }
    .stTextInput label {
        color: #f5f7ff !important;
        font-weight: 800 !important;
        font-size: .88rem !important;
    }
    .stTextInput > div > div {
        border: 1px solid rgba(139, 116, 255, .52) !important;
        border-radius: 10px !important;
        background: rgba(18,18,42,.92) !important;
        box-shadow: 0 0 0 1px rgba(255,255,255,.035) inset !important;
    }
    .stTextInput > div > div:focus-within {
        border-color: rgba(103,232,249,.9) !important;
        box-shadow: 0 0 0 3px rgba(0,212,255,.15), 0 0 0 1px rgba(255,255,255,.06) inset !important;
    }
    .stTextInput > div > div > input {
        background: transparent !important;
        border: 0 !important;
        color: #f3f6ff !important;
        border-radius: 10px !important;
        min-height: 44px !important;
    }
    .stTextInput input::placeholder { color: rgba(224,224,255,.68) !important; }
    .stTextInput button {
        color: #ffffff !important;
        background: rgba(124,106,247,.12) !important;
        border-radius: 0 10px 10px 0 !important;
    }
    
    div[data-testid="stForm"] {
        border: 1px solid rgba(103,232,249,.34) !important;
        border-radius: 16px !important;
        padding: 18px 18px 16px !important;
        background:
            linear-gradient(180deg, rgba(13,18,44,.86), rgba(10,12,31,.78)) !important;
        box-shadow:
            0 18px 46px rgba(0,0,0,.28),
            0 0 0 1px rgba(255,255,255,.045) inset !important;
    }
    div[data-testid="stForm"]:focus-within {
        border-color: rgba(103,232,249,.62) !important;
        box-shadow:
            0 18px 46px rgba(0,0,0,.28),
            0 0 0 3px rgba(0,212,255,.08),
            0 0 0 1px rgba(255,255,255,.055) inset !important;
    }
    div[data-testid="stFormSubmitButtonHint"] { display: none !important; }
    
    div[data-testid="stForm"] .stFormSubmitButton {
        display: flex !important;
        justify-content: center !important;
        width: 100% !important;
        margin-top: 25px !important;
    }
    div[data-testid="stForm"] .stFormSubmitButton button {
        background: linear-gradient(135deg, #604fd8 0%, #836dff 100%) !important;
        color: white !important;
        font-weight: 800 !important;
        font-size: 1.05rem !important;
        border: 1px solid rgba(255,255,255,.14) !important;
        border-radius: 9px !important;
        padding: 0.65rem 2.5rem !important;
        width: auto !important;
        min-width: 180px !important;
        box-shadow: 0 14px 32px rgba(124, 106, 247, 0.3), 0 0 26px rgba(103,232,249,.1) !important;
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
    .auth-mode-caption {
        color: #8d88c7;
        text-align: center;
        font-size: .78rem;
        font-weight: 800;
        margin: 0 0 8px;
        text-transform: uppercase;
    }
    div[data-testid="stHorizontalBlock"]:has(button[kind]) {
        gap: .55rem;
    }
    </style>
    """, unsafe_allow_html=True)

    if embedded:
        form_parent = st.container()
    else:
        st.markdown(
            '<div class="auth-shell"><a href="#top-auth">Back to landing</a><span>Secure BizVision AI workspace access</span></div>',
            unsafe_allow_html=True,
        )
        form_parent = st.container()

    # State routers initializations
    if "reset_mode" not in st.session_state:
        st.session_state["reset_mode"] = "login"
    if "show_forgot_link" not in st.session_state:
        st.session_state["show_forgot_link"] = False

    with form_parent:
        st.markdown('<div class="custom-login-box"></div>', unsafe_allow_html=True)
        if embedded and st.session_state.get("reset_mode") in {"login", "register"}:
            st.markdown('<div class="auth-mode-caption">Workspace access</div>', unsafe_allow_html=True)
            tab_login, tab_register = st.columns(2)
            with tab_login:
                if st.button(
                    "Login",
                    key="auth_tab_login",
                    use_container_width=True,
                    type="primary" if st.session_state["reset_mode"] == "login" else "secondary",
                ):
                    set_auth_mode("login")
                    st.rerun()
            with tab_register:
                if st.button(
                    "Register",
                    key="auth_tab_register",
                    use_container_width=True,
                    type="primary" if st.session_state["reset_mode"] == "register" else "secondary",
                ):
                    set_auth_mode("register")
                    st.rerun()
        
        current_mode = st.session_state["reset_mode"]
        
        #  1 LOGIN VIEW MODE (CENTERED STRINGS) 
        if current_mode == "login":
            st.markdown(render_brand_header(BRAND_NAME), unsafe_allow_html=True)
            
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
                    set_auth_mode("forgot")
                    st.rerun()
            with link_col2:
                if st.button("Don't have an account? Register", key="lnk_switch_to_register"):
                    st.session_state["show_forgot_link"] = False
                    set_auth_mode("register")
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        #  2 PUBLIC REGISTRATION VIEW MODE
        elif current_mode == "register":
            st.markdown(render_brand_header("Create Account"), unsafe_allow_html=True)

            with st.form(key="form_execution_register_isolated"):
                reg_full_name = st.text_input("Full Name", placeholder="e.g. Harshit Jetwani", key="register_full_name_widget")
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

                    if not reg_full_name.strip() or not username or not email or not reg_password or not reg_confirm:
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
                                    set_auth_mode("login")
                                    st.session_state["show_forgot_link"] = False
                                    st.rerun()
                                else:
                                    st.error("Account creation failed. Try a different username or email.")
                            else:
                                sent, message = send_otp_email(email, username, generated_otp)
                                if sent:
                                    st.session_state["pending_registration"] = {
                                        "full_name": reg_full_name.strip(),
                                        "username": username,
                                        "email": email,
                                        "password": reg_password,
                                    }
                                    st.session_state["registration_otp"] = generated_otp
                                    st.session_state["registration_expires_at"] = (datetime.now() + timedelta(minutes=10)).isoformat()
                                    st.session_state["registration_attempts"] = 0
                                    set_auth_mode("verify_register")
                                    st.success(f"Verification OTP sent to {mask_email(email)}.")
                                    st.rerun()
                                else:
                                    st.error(message)
                                    st.caption("Email verification is required. Configure SMTP settings or set ALLOW_UNVERIFIED_REGISTRATION=true only for local demos.")

            st.markdown('<div class="link-wrapper">', unsafe_allow_html=True)
            if st.button("Already have an account? Login", key="lnk_register_back_to_login"):
                st.session_state["show_forgot_link"] = False
                set_auth_mode("login")
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        #  3 FORGOT VIEW MODE 
        elif current_mode == "forgot":
            st.markdown(render_brand_header(BRAND_NAME), unsafe_allow_html=True)
            
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
                                set_auth_mode("verify")
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
                set_auth_mode("login")
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        elif current_mode == "verify_register":
            pending = st.session_state.get("pending_registration") or {}
            st.markdown(render_brand_header("Verify Email"), unsafe_allow_html=True)
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
                        set_auth_mode("register")
                        for key in ["pending_registration", "registration_otp", "registration_expires_at", "registration_attempts"]:
                            st.session_state.pop(key, None)
                        st.rerun()
                    elif st.session_state.get("registration_attempts", 0) >= 5:
                        st.error("Too many incorrect attempts. Please restart registration.")
                        set_auth_mode("register")
                        for key in ["pending_registration", "registration_otp", "registration_expires_at", "registration_attempts"]:
                            st.session_state.pop(key, None)
                        st.rerun()
                    elif input_otp == st.session_state.get("registration_otp") and pending:
                        if create_user(pending["username"], pending["email"], pending["password"], "user"):
                            log_activity(pending["username"], "Register", "Self-service account created after email OTP verification.")
                            st.success("Email verified. Account created successfully. Please sign in.")
                            set_auth_mode("login")
                            for key in ["pending_registration", "registration_otp", "registration_expires_at", "registration_attempts"]:
                                st.session_state.pop(key, None)
                            st.rerun()
                        else:
                            st.error("Account creation failed. Try a different username or email.")
                    else:
                        st.session_state["registration_attempts"] = st.session_state.get("registration_attempts", 0) + 1
                        st.error("Invalid verification code.")

            st.markdown('<div class="link-wrapper">', unsafe_allow_html=True)
            if pending.get("email") and st.button("Resend OTP", key="lnk_resend_register_otp"):
                generated_otp = str(secrets.randbelow(899999) + 100000)
                sent, message = send_otp_email(pending["email"], pending["username"], generated_otp)
                if sent:
                    st.session_state["registration_otp"] = generated_otp
                    st.session_state["registration_expires_at"] = (datetime.now() + timedelta(minutes=10)).isoformat()
                    st.session_state["registration_attempts"] = 0
                    st.success(f"New verification OTP sent to {mask_email(pending['email'])}.")
                else:
                    st.error(message)
            if st.button("Cancel Registration", key="lnk_cancel_register_verify"):
                set_auth_mode("register")
                for key in ["pending_registration", "registration_otp", "registration_expires_at", "registration_attempts"]:
                    st.session_state.pop(key, None)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        #  4 VERIFY VIEW MODE 
        elif current_mode == "verify":
            st.markdown(render_brand_header("Security Key"), unsafe_allow_html=True)
            
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
                        set_auth_mode("forgot")
                        st.session_state.pop("recovery_otp", None)
                        st.session_state.pop("recovery_expires_at", None)
                        st.rerun()
                    elif reset_attempts_exceeded():
                        st.error("Too many incorrect attempts. Please request a new OTP.")
                        set_auth_mode("forgot")
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
                                set_auth_mode("login")
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
                set_auth_mode("login")
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

