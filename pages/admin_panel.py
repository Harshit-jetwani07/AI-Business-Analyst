import streamlit as st
import pandas as pd
import os
import re
import secrets
from datetime import datetime
from utils.auth import (
    get_all_users, get_activity_log, get_all_datasets, get_all_reports,
    log_activity, get_conn, delete_user, update_user_role, toggle_user_active,
    approve_dataset, reject_dataset, approve_report, reject_report,
    get_admin_metrics, get_user_activity, hash_password
)

def show_admin_panel():
    #   NESTED SECURITY PRIVILEGE CHECK (SAME) 
    if not st.session_state.get("logged_in", False):
        st.warning("Session context unauthenticated. Access denied.")
        st.stop()
        
    if st.session_state.get("role") != "admin":
        st.error("Access denied: unauthorized privilege. This workspace is restricted to system administrators.")
        st.stop()

    #   PREMIUM SMOOTH FLAT UI DESIGN (COMPACT & BALANCED) 
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght=400;500;600;700&family=Inter:wght=400;500;600&display=swap');
        
        .stApp { background: #07070c !important; }
        html, body, [class*="css"] { font-family: 'Space Grotesk', 'Inter', sans-serif !important; }
        
        /* Glassmorphic Minimal Top Hero Header */
        .admin-hero {
            background: linear-gradient(135deg, #0f0f24 0%, #12122b 100%);
            border: 1px solid #1f1f3e;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 25px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
        }
        .hero-title { color: #ffffff; font-size: 1.75rem; font-weight: 700; margin: 0; }
        .hero-sub { color: #6c6c9c; font-size: 0.9rem; margin-top: 4px; }
        
        /* Section Title Line Indicators */
        .panel-section-title {
            color: #a394f7; font-size: 1.15rem; font-weight: 600;
            margin-bottom: 12px; margin-top: 10px;
            border-left: 3px solid #7c6af7; padding-left: 8px;
        }

        /* Compact Dashboard Cards */
        .functional-card {
            background: #0e0e1f !important; 
            border: 1px solid #1f1f3e !important;
            border-radius: 10px !important; 
            padding: 16px !important; 
            margin-bottom: 15px !important;
        }
        
        /* Modern Slim Tabs Custom Layout */
        .stTabs [data-baseweb="tab-list"] {
            background: #0e0e1f !important; 
            border: 1px solid #1f1f3e !important;
            border-radius: 8px !important; 
            padding: 4px !important; 
            gap: 6px !important;
        }
        .stTabs [data-baseweb="tab"] {
            color: #6c6c9c !important; 
            font-weight: 600 !important; 
            padding: 8px 16px !important; 
            border-radius: 6px !important;
            border: none !important;
        }
        .stTabs [aria-selected="true"] { 
            background: linear-gradient(135deg, #5646c7 0%, #7c6af7 100%) !important; 
            color: #ffffff !important; 
        }
        
        /* Inputs & Selection Boxes Frame Optimizations */
        .stTextInput > div > div > input, .stSelectbox div[data-baseweb="select"] {
            background: #06060d !important; 
            border: 1px solid #1f1f3e !important; 
            color: #e2e2ff !important; 
            border-radius: 6px !important;
            height: 38px !important;
        }
        
        /* Centered Buttons & Compact Actions System */
        .stButton > button {
            background: linear-gradient(135deg, #5646c7 0%, #7c6af7 100%) !important; 
            color: #ffffff !important;
            border: none !important; 
            border-radius: 6px !important; 
            font-weight: 600; 
            height: 38px !important;
            transition: all 0.2s;
        }
        .stButton > button:hover { transform: translateY(-1px); opacity: 0.95; }
        div.destructive-btn-block button { background: linear-gradient(135deg, #a62b2b 0%, #d93838 100%) !important; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="admin-hero">
        <div class="hero-title">Enterprise Control Center</div>
        <div class="hero-sub">Manage secure user isolation, token financial costs, database persistence, and advanced analytics pipelines.</div>
    </div>
    """, unsafe_allow_html=True)

    tabs = st.tabs([
        "Identity & Auth", 
        "Storage & Isolation", 
        "Token Cost Control", 
        "Advanced Core Engines",
        "Activity Audits"
    ])

    #  1. IDENTITY & AUTH (COMPACTED & CLEAN MATRIX)
    with tabs[0]:
        st.markdown('<div class="panel-section-title">System Profiles Management</div>', unsafe_allow_html=True)
        
        #  Table View: Always Full Width and on Top
        try:
            conn = get_conn()
            db_users = conn.execute("SELECT id, username, email, role, active, created, last_login FROM users").fetchall()
            conn.close()
            
            if db_users:
                df_profiles = pd.DataFrame(db_users, columns=["System ID", "Profile Username", "Email Address", "System Role", "Active", "Creation Timestamp", "Last Login"])
                st.dataframe(df_profiles, use_container_width=True, hide_index=True, height=180)
            else:
                st.info("No active user accounts registered in the database registries.")
        except Exception as table_err:
            st.error(f"Error loading users table: {table_err}")

        try:
            users_for_control = get_all_users()
            editable_users = [u for u in users_for_control if u["username"] != st.session_state.get("username")]
            if editable_users:
                st.markdown('<div class="panel-section-title">Privilege & Access Controls</div>', unsafe_allow_html=True)
                p1, p2, p3 = st.columns([2, 1, 1])
                selected_user = p1.selectbox("Target Profile", editable_users, format_func=lambda u: f"{u['username']} ({u['role']})")
                new_role_value = p2.selectbox("Role", ["user", "admin"], index=0 if selected_user["role"] == "user" else 1)
                if p3.button("Apply Role", use_container_width=True):
                    update_user_role(selected_user["id"], new_role_value)
                    log_activity(st.session_state.username, "Update User Role", f"{selected_user['username']} -> {new_role_value}")
                    st.success("Role updated.")
                    st.rerun()
                active_label = "Deactivate User" if selected_user["active"] else "Reactivate User"
                if st.button(active_label, use_container_width=True):
                    toggle_user_active(selected_user["id"])
                    log_activity(st.session_state.username, "Toggle User Active", f"Toggled active state for {selected_user['username']}")
                    st.rerun()
        except Exception as control_err:
            st.error(f"Access control error: {control_err}")

        #  Action Row: Horizontal split configuration so forms don't stretch forever
        c1, c2 = st.columns(2, gap="medium")
        
        with c1:
            st.markdown('<div class="functional-card">', unsafe_allow_html=True)
            st.markdown("<h5 style='margin-top:0; margin-bottom:10px; color:#e2e2ff;'>Register Validated Profile</h5>", unsafe_allow_html=True)
            
            new_user = st.text_input("Username", key="ent_un", placeholder="e.g. harshit_data")
            new_email = st.text_input("Email Address", key="ent_em", placeholder="name@domain.com")
            
            # Sub-columns inside form for space efficiency
            sc1, sc2 = st.columns(2)
            with sc1:
                new_pass = st.text_input("Secure Password", type="password", key="ent_pw", placeholder="")
            with sc2:
                confirm_pass = st.text_input("Confirm Password", type="password", key="ent_cpw", placeholder="")
                
            new_role = st.selectbox("System Privilege", ["user", "admin"], key="ent_rl")
            
            #  Password Strength Indicator Logic (Intact)
            if new_pass:
                strength = 0
                if len(new_pass) >= 8: strength += 1
                if re.search(r"[a-z]", new_pass) and re.search(r"[A-Z]", new_pass): strength += 1
                if re.search(r"\d", new_pass): strength += 1
                if re.search(r"[_@$%&*!]", new_pass): strength += 1
                
                colors = ["#ff4b4b", "#ffaa00", "#ccff00", "#00ffcc"]
                labels = ["Weak", "Moderate", "Strong", "Excellent"]
                display_strength = max(strength, 1)
                st.markdown(f"<p style='font-size:0.8rem; margin:0;'>Strength: <span style='color:{colors[display_strength-1]};'>{labels[display_strength-1]}</span></p>", unsafe_allow_html=True)
                st.progress(strength / 4)

            st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
            if st.button("Initialize Account", use_container_width=True):
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, new_email.strip()):
                    st.error("Invalid email format syntax.")
                elif new_pass != confirm_pass:
                    st.error("Password and Confirm Password do not match.")
                elif len(new_pass) < 6:
                    st.error("Password must be at least 6 characters long.")
                else:
                    try:
                        conn = get_conn()
                        salt, hpwd = hash_password(new_pass)
                        conn.execute(
                            "INSERT INTO users (username,email,salt,password,role,created) VALUES (?,?,?,?,?,?)",
                            (new_user.strip(), new_email.strip(), salt, hpwd, new_role, datetime.now().isoformat())
                        )
                        conn.commit()
                        conn.close()
                        st.success(f"Profile for **{new_user}** initialized.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"DB fault: {e}")
            st.markdown('</div>', unsafe_allow_html=True)

        with c2:
            # Compact Reset Card
            st.markdown('<div class="functional-card">', unsafe_allow_html=True)
            st.markdown("<h5 style='margin-top:0; margin-bottom:10px; color:#ff6b6b;'>Password Reset Loop Emulator</h5>", unsafe_allow_html=True)
            
            reset_target = st.text_input("Target Account Username", key="otp_user")
            if st.button("Trigger Secure Reset Token", use_container_width=True):
                if reset_target:
                    mock_token = secrets.token_hex(16)
                    mock_otp = secrets.randbelow(899999) + 100000
                    st.info(f"**Emulated Broadcast Reset**\n* **OTP Code:** `{mock_otp}`\n* **Token:** `{mock_token[:10]}...`")
                    log_activity(st.session_state.username, "Forgot Password Trigger", f"Generated OTP/Token loop for: {reset_target}")
                else:
                    st.warning("Please specify a target profile workspace.")
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Compact Deletion Card
            st.markdown('<div class="functional-card" style="border-color: #441515 !important;">', unsafe_allow_html=True)
            st.markdown("<h5 style='margin-top:0; margin-bottom:10px; color:#ff4b4b;'>Wipe Session Profile</h5>", unsafe_allow_html=True)
            try:
                users_list = get_all_users()
                current_user = st.session_state.get("username", "")
                available_to_delete = [u["username"] for u in users_list if u["username"] != current_user]
                if available_to_delete:
                    user_to_drop = st.selectbox("Choose Target Account", options=available_to_delete)
                    st.markdown('<div class="destructive-btn-block">', unsafe_allow_html=True)
                    if st.button("Permanently Delete Account", use_container_width=True):
                        target_id = next((u["id"] for u in users_list if u["username"] == user_to_drop), None)
                        if target_id:
                            delete_user(target_id)
                            log_activity(st.session_state.username, "Delete User", f"Dropped user: {user_to_drop}")
                            st.success(f"Account for {user_to_drop} deleted.")
                            st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.caption("No other deletable user profiles located.")
            except: pass
            st.markdown('</div>', unsafe_allow_html=True)

    #  2. FILE PERSISTENCE & DATASET ISOLATION TRACKING (SAME)
    with tabs[1]:
        st.markdown('<div class="panel-section-title">Tenant Isolation & Storage File Persistence Matrix</div>', unsafe_allow_html=True)
        for path in ["uploads", "reports", "exports"]:
            if not os.path.exists(path): os.makedirs(path)
            
        st.caption(f"**Active Paths:** `/uploads` ({len(os.listdir('uploads'))} files) | `/reports` | `/exports`")
        st.markdown("""
        <div style='background:#12122a; padding:10px; border-radius:6px; border:1px solid #2a2a5a; margin-bottom:12px; font-size:0.85rem;'>
            <span style='color:#00ffcc;'><b>Isolation Active:</b></span> Query sandboxing locks down records strictly via session state IDs. 
        </div>
        """, unsafe_allow_html=True)
        
        try:
            datasets_list = get_all_datasets()
            if datasets_list:
                df_data = pd.DataFrame(datasets_list)
                st.dataframe(df_data, use_container_width=True, height=150)
                
                st.markdown("##### Dataset Review Queue")
                selected_dataset_id = st.selectbox(
                    "Select dataset record",
                    df_data["id"].tolist(),
                    format_func=lambda x: f"#{x} - {df_data.loc[df_data['id'] == x, 'name'].iloc[0]} ({df_data.loc[df_data['id'] == x, 'status'].iloc[0] if 'status' in df_data else 'pending'})",
                )
                selected_record = df_data[df_data["id"] == selected_dataset_id].iloc[0].to_dict()
                q1, q2, q3, q4 = st.columns(4)
                q1.metric("Rows", int(selected_record.get("rows") or 0))
                q2.metric("Columns", int(selected_record.get("cols") or 0))
                q3.metric("Quality", f"{int(selected_record.get('quality_score') or 0)}/100")
                q4.metric("Status", str(selected_record.get("status") or "pending").title())

                review_notes = st.text_area("Admin Review Notes", value=str(selected_record.get("admin_notes") or ""), key=f"dataset_notes_{selected_dataset_id}")
                a1, a2, a3 = st.columns(3)
                if a1.button("Approve Dataset", use_container_width=True):
                    approve_dataset(selected_dataset_id, review_notes)
                    log_activity(st.session_state.username, "Approve Dataset", f"Approved dataset #{selected_dataset_id}")
                    st.rerun()
                if a2.button("Reject Dataset", use_container_width=True):
                    reject_dataset(selected_dataset_id, review_notes)
                    log_activity(st.session_state.username, "Reject Dataset", f"Rejected dataset #{selected_dataset_id}")
                    st.rerun()
                if a3.button("Preview Saved File", use_container_width=True):
                    file_path = str(selected_record.get("file_path") or "")
                    if file_path and os.path.exists(file_path):
                        try:
                            if file_path.lower().endswith((".xlsx", ".xls")):
                                preview_df = pd.read_excel(file_path).head(20)
                            else:
                                preview_df = pd.read_csv(file_path).head(20)
                            st.dataframe(preview_df, use_container_width=True)
                        except Exception as preview_err:
                            st.error(f"Preview failed: {preview_err}")
                    else:
                        st.warning("Saved file path not found for this record.")
            else:
                st.info("No files registered in database storage systems yet.")
        except Exception as e: st.error(str(e))

        st.markdown('<div class="panel-section-title">Report Approval Queue</div>', unsafe_allow_html=True)
        try:
            reports_list = get_all_reports()
            if reports_list:
                df_reports = pd.DataFrame(reports_list)
                st.dataframe(df_reports, use_container_width=True, height=150)
                selected_report_id = st.selectbox(
                    "Select report record",
                    df_reports["id"].tolist(),
                    format_func=lambda x: f"#{x} - {df_reports.loc[df_reports['id'] == x, 'title'].iloc[0]}",
                    key="report_review_select",
                )
                selected_report = df_reports[df_reports["id"] == selected_report_id].iloc[0].to_dict()
                report_notes = st.text_area("Report Admin Notes", value=str(selected_report.get("admin_notes") or ""), key=f"report_notes_{selected_report_id}")
                r1, r2 = st.columns(2)
                if r1.button("Approve Report", use_container_width=True):
                    approve_report(selected_report_id, report_notes)
                    log_activity(st.session_state.username, "Approve Report", f"Approved report #{selected_report_id}")
                    st.rerun()
                if r2.button("Reject Report", use_container_width=True):
                    reject_report(selected_report_id, report_notes)
                    log_activity(st.session_state.username, "Reject Report", f"Rejected report #{selected_report_id}")
                    st.rerun()
            else:
                st.info("No report records registered yet.")
        except Exception as report_err:
            st.error(f"Report review error: {report_err}")

    #  3. AI COST CONTROLS & MONITORING (SAME)
    with tabs[2]:
        st.markdown('<div class="panel-section-title">LLM Cost Safeguards & Token Analytics</div>', unsafe_allow_html=True)
        metrics = get_admin_metrics()
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        estimated_tokens = metrics["ai_queries"] * 1800
        estimated_cost = (estimated_tokens / 1_000_000) * 0.60
        col_m1.metric("AI Requests", f"{metrics['ai_queries']:,} reqs")
        col_m2.metric("Estimated Tokens", f"{estimated_tokens:,} tk")
        col_m3.metric("Estimated Cost", f"${estimated_cost:.2f}", "approx")
        col_m4.metric("Top Active User", metrics["top_user"]["username"], f"{metrics['top_user']['total']} events")

        try:
            logs_for_chart = pd.DataFrame(get_activity_log(500))
            if not logs_for_chart.empty:
                logs_for_chart["date"] = pd.to_datetime(logs_for_chart["timestamp"]).dt.date
                daily_usage = logs_for_chart.groupby(["date", "action"]).size().reset_index(name="events")
                st.line_chart(daily_usage.pivot_table(index="date", columns="action", values="events", fill_value=0))
        except Exception as chart_err:
            st.caption(f"Usage chart unavailable: {chart_err}")
        
        st.markdown("#### Consumption Guardrails")
        c_c1, c_c2 = st.columns(2)
        with c_c1:
            st.markdown('<div class="functional-card">', unsafe_allow_html=True)
            st.markdown("##### Tenant Daily Safety Caps")
            st.slider("Max Requests per User / 24 Hours", 10, 500, 50, key="c_req_cap")
            st.slider("Max Budget Cap ($ USD) per Client Module", 5, 200, 25, key="c_bud_cap")
            st.markdown('</div>', unsafe_allow_html=True)
        with c_c2:
            st.markdown('<div class="functional-card">', unsafe_allow_html=True)
            st.markdown("##### Token Cost Evaluation")
            pricing_data = {
                "Model Engine Target": ["gpt-4o", "gpt-3.5-turbo", "gemini-pro"],
                "Input Cost / 1M Reqs": ["$5.00", "$0.50", "$1.00"],
                "Output Cost / 1M Reqs": ["$15.00", "$1.50", "$2.00"]
            }
            st.table(pd.DataFrame(pricing_data))
            st.markdown('</div>', unsafe_allow_html=True)

    #  4. ADVANCED ANALYTICS CORE ENGINE CONTROLS (SAME)
    with tabs[3]:
        st.markdown('<div class="panel-section-title">AI Business Analyst Processing Modules</div>', unsafe_allow_html=True)
        col_an1, col_an2 = st.columns(2)
        with col_an1:
            st.markdown('<div class="functional-card">', unsafe_allow_html=True)
            st.markdown("##### Statistical Learning Overlays")
            st.checkbox("Anomaly Detection (Isolation Forest)", value=True)
            st.checkbox("Unsupervised Clustering (K-Means Centroids)", value=True)
            st.checkbox("Churn Prediction & Logistic Vectors", value=False)
            st.markdown('</div>', unsafe_allow_html=True)
        with col_an2:
            st.markdown('<div class="functional-card">', unsafe_allow_html=True)
            st.markdown("##### Automation Core Parameters")
            st.checkbox("Automated KPI Discovery Engine", value=True)
            st.checkbox("Self-Generating Executive Summaries", value=True)
            st.markdown('</div>', unsafe_allow_html=True)

    #  5. AUDIT LOGS VIEW (SAME)
    with tabs[4]:
        st.markdown('<div class="panel-section-title">Production Audit Trail Logging Array</div>', unsafe_allow_html=True)
        try:
            logs_list = get_activity_log(150)
            if logs_list:
                st.dataframe(pd.DataFrame(logs_list), use_container_width=True, height=350)
            else:
                st.info("Audit log stack tracks currently empty.")
        except Exception as e: st.error(str(e))

        st.markdown('<div class="panel-section-title">Per-User Activity Timeline</div>', unsafe_allow_html=True)
        try:
            users = get_all_users()
            if users:
                selected_timeline_user = st.selectbox("Timeline User", [u["username"] for u in users], key="timeline_user")
                timeline = get_user_activity(selected_timeline_user, 60)
                if timeline:
                    timeline_df = pd.DataFrame(timeline)
                    st.dataframe(timeline_df[["timestamp", "action", "detail"]], use_container_width=True, height=260)
                else:
                    st.info("No activity found for this user.")
        except Exception as timeline_err:
            st.error(f"Timeline error: {timeline_err}")

#  STREAMLIT ROUTING BINDINGS 
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["role"] = "guest"
    st.session_state["username"] = "Guest"

if __name__ == "__main__" or st.session_state.get("current_page") == "Admin Panel":
    try:
        import inspect
        frame_stack = [frame.filename for frame in inspect.stack()]
        is_called_from_main = any("app.py" in f for f in frame_stack)
        if not is_called_from_main or st.session_state.get("current_page") == "Admin Panel":
            show_admin_panel()
    except: pass

