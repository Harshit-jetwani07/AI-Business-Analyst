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
    """Render login screen with pixel-perfect center-aligned actions."""
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
    .stApp { background: #07070f !important; }
    [data-testid="stSidebar"] { display: none !important; }
    .block-container { padding-top: 5rem !important; }
    
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

