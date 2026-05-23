import streamlit as st
import hashlib
import secrets
from utils.auth import get_conn, log_activity, authenticate

def show_login_page():
    """Render login screen with pixel-perfect center-aligned actions."""
    st.markdown("""
    <style>
    .stApp { background: #07070f !important; }
    [data-testid="stSidebar"] { display: none !important; }
    .block-container { padding-top: 5rem !important; }
    
    div[data-testid="stVerticalBlock"] > div:has(.custom-login-box) {
        background: linear-gradient(160deg, #0f0f2a 0%, #14142e 100%) !important;
        border: 1px solid #2a2a5a !important;
        border-radius: 16px !important;
        padding: 35px 30px !important;
        max-width: 400px !important;
        margin: 0 auto !important;
        box-shadow: 0 10px 40px rgba(124, 106, 247, 0.15) !important;
    }
    .login-logo { font-size: 2.8rem; text-align: center; margin-bottom: 5px; }
    .brand-logo {
        width: 72px;
        height: 72px;
        border-radius: 18px;
        margin: 0 auto 14px auto;
        display: flex;
        align-items: center;
        justify-content: center;
        background: linear-gradient(135deg, #4a3fa0 0%, #7c6af7 100%);
        color: #ffffff;
        font-size: 2.2rem;
        box-shadow: 0 8px 26px rgba(124, 106, 247, 0.3);
    }
    .login-title { text-align: center; font-size: 1.65rem; font-weight: 700; color: #a090f7; margin-bottom: 2px; }
    .login-sub { text-align: center; color: #6060a0; font-size: 0.88rem; margin-bottom: 20px; }
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
            st.markdown('<div class="brand-logo">📊</div><div class="login-title">AI Business Analyst</div><div class="login-sub">Sign in to continue</div>', unsafe_allow_html=True)
            
            with st.form(key="form_execution_login_isolated"):
                username_input = st.text_input("Username", placeholder="Enter username", key="login_username_widget")
                password_input = st.text_input("Password", type="password", placeholder="Enter password", key="login_password_widget")
                login_btn = st.form_submit_button("Sign In")

                if login_btn:
                    if not username_input or not password_input:
                        st.error("Please enter both username and password.")
                    else:
                        user = authenticate(username_input.strip(), password_input)
                        if user:
                            st.session_state["logged_in"] = True
                            st.session_state["role"] = user["role"]
                            st.session_state["username"] = user["username"]
                            st.session_state["current_page"] = "Dashboard"
                            st.session_state["show_forgot_link"] = False
                            log_activity(user["username"], "Login", "Session authorized.")
                            st.rerun()
                        else:
                            st.error("Invalid username, password, or inactive account.")
                            st.session_state["show_forgot_link"] = True
                            st.rerun()
                            
            # Conditional Render: Appears ONLY when wrong credentials are hit
            if st.session_state["show_forgot_link"]:
                st.markdown('<div class="link-wrapper">', unsafe_allow_html=True)
                if st.button("Forgot Password?", key="lnk_switch_to_forgot"):
                    st.session_state["reset_mode"] = "forgot"
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        #  2 FORGOT VIEW MODE 
        elif current_mode == "forgot":
            st.markdown('<div class="brand-logo">📊</div><div class="login-title">AI Business Analyst</div><div class="login-sub">Reset access securely</div>', unsafe_allow_html=True)
            
            with st.form(key="form_execution_forgot_isolated"):
                target_user = st.text_input("Target Username", placeholder="Enter your username", key="forgot_username_widget")
                gen_otp_btn = st.form_submit_button("Generate OTP")
                
                if gen_otp_btn:
                    if target_user:
                        conn = get_conn()
                        user = conn.execute("SELECT * FROM users WHERE username = ?", (target_user.strip(),)).fetchone()
                        conn.close()
                        
                        if user:
                            generated_otp = str(secrets.randbelow(899999) + 100000)
                            st.session_state["recovery_otp"] = generated_otp
                            st.session_state["recovery_user"] = target_user.strip()
                            st.session_state["reset_mode"] = "verify"
                            st.rerun()
                        else:
                            st.error("Username index not found inside database registries.")
                    else:
                        st.warning("Please specify a target username.")
                        
            st.markdown('<div class="link-wrapper">', unsafe_allow_html=True)
            if st.button("Back to Login", key="lnk_back_to_login_view"):
                st.session_state["show_forgot_link"] = False 
                st.session_state["reset_mode"] = "login"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        #  3 VERIFY VIEW MODE 
        elif current_mode == "verify":
            st.markdown('<div class="brand-logo">📊</div><div class="login-title">Security Key</div><div class="login-sub">Enter verification token</div>', unsafe_allow_html=True)
            
            st.info("A reset OTP was generated. For production, send this code by email or SMS instead of displaying it in the app.")
            
            with st.form(key="form_execution_verify_isolated"):
                input_otp = st.text_input("Enter 6-Digit OTP", placeholder="", key="verify_otp_widget")
                new_pwd = st.text_input("New Password", type="password", placeholder="", key="verify_pwd_widget")
                confirm_pwd = st.text_input("Confirm New Password", type="password", placeholder="", key="verify_confirm_widget")
                reset_submit = st.form_submit_button("Deploy New Password")
                
                if reset_submit:
                    if input_otp == st.session_state.get("recovery_otp"):
                        if new_pwd == confirm_pwd:
                            if len(new_pwd) >= 6:
                                conn = get_conn()
                                fresh_salt = secrets.token_hex(8)
                                hashed_val = hashlib.sha256(f"{fresh_salt}{new_pwd}".encode()).hexdigest()
                                
                                conn.execute(
                                    "UPDATE users SET password = ?, salt = ? WHERE username = ?",
                                    (hashed_val, fresh_salt, st.session_state.get("recovery_user"))
                                )
                                conn.commit()
                                conn.close()
                                
                                st.success("Access credentials updated. Proceeding to login.")
                                st.session_state["show_forgot_link"] = False 
                                st.session_state["reset_mode"] = "login"
                                st.rerun()
                            else:
                                st.error("Password string must contain at least 6 characters.")
                        else:
                            st.error("Matching logic check failed: Mismatch strings.")
                    else:
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

