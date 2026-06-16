import streamlit as st
import bcrypt
import time
from db import get_connection
from styles import load_css

# ==========================================
# SESSION TIMEOUT LOGIC
# ==========================================
# Check for session timeout (15 minutes = 900 seconds)
if st.session_state.get('logged_in'):
    last_activity = st.session_state.get('last_activity', time.time())
    if time.time() - last_activity > 900:
        st.session_state.clear()
        st.warning("⚠️ Session timed out due to inactivity. Please log in again.")
    else:
        # Update activity timer and bypass login screen
        st.session_state['last_activity'] = time.time()
        st.switch_page("pages/01_Incidents.py")

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="Sentinel Incident Portal",
    page_icon="🛡️",
    layout="centered"
)

st.markdown(load_css(), unsafe_allow_html=True)
st.markdown("""
<style>
    [data-testid="stSidebar"] { display: none; }
    [data-testid="collapsedControl"] { display: none; }
</style>
""", unsafe_allow_html=True)

# Initialise ONLY if key doesn't exist yet
if 'login_attempts' not in st.session_state:
    st.session_state['login_attempts'] = 0
# Track lockout separately to avoid issues with page reloads resetting attempts
if 'locked_out' not in st.session_state:
    st.session_state['locked_out'] = False

# Define maximum attempts before lockout
MAX_ATTEMPTS = 5

st.markdown('<div class="title-text">🛡️ SENTINEL</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle-text">Incident Management Portal</div>',
            unsafe_allow_html=True)
st.subheader("🔐 Secure Login")

# ==========================================
# TASK 15: LOCKOUT LOGIC
# ==========================================
# Hard stop if locked out
if st.session_state['locked_out']:
    st.error("🔒 Account locked — too many failed attempts. Contact your administrator.")
    st.markdown("---")
    if st.button("🔓 Reset Lockout (Admin Demo)", width='stretch'):
        st.session_state['login_attempts'] = 0
        st.session_state['locked_out'] = False
        st.rerun()
    st.stop()

# Show warning after first failure
if st.session_state['login_attempts'] > 0:
    remaining = MAX_ATTEMPTS - st.session_state['login_attempts']
    st.warning(f"⚠️ Failed attempts: "
               f"{st.session_state['login_attempts']}/{MAX_ATTEMPTS} — "
               f"{remaining} remaining before lockout.")

# Use a form so button click doesn't trigger double-rerun
with st.form("login_form", clear_on_submit=False):
    username = st.text_input("Username", placeholder="Enter your username")
    password = st.text_input("Password", type="password",
                             placeholder="Enter your password")
    submitted = st.form_submit_button("Login", width='stretch')

# ==========================================
# LOGIN AUTHENTICATION LOGIC
# ==========================================
# Handle login logic on submit
if submitted:
    if username and password:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Fetch user info and password hash in one query to avoid multiple DB calls
        # NOTE: Changed ? to %s for PostgreSQL compatibility
        cursor.execute("""
            SELECT u.UserID, u.Username, r.RoleName, ul.PasswordHash
            FROM USERS u
            JOIN ROLES r ON u.RoleID = r.RoleID
            JOIN USER_LOGIN ul ON u.UserID = ul.UserID
            WHERE u.Username = %s
        """, (username,))
        row = cursor.fetchone()

        if row:
            stored_hash = row[3].encode('utf-8')
            # Check password using bcrypt
            if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
                # ✅ Success — reset counter and set session state
                st.session_state['login_attempts'] = 0
                st.session_state['locked_out'] = False
                st.session_state['logged_in'] = True
                st.session_state['username'] = row[1]
                st.session_state['role'] = row[2]
                st.session_state['user_id'] = row[0]
                st.session_state['last_activity'] = time.time() # Start the 15-minute timer

                # Log successful login (Changed ? to %s)
                cursor.execute("""
                    INSERT INTO AUDIT_LOGS (UserID, ActionType, Status)
                    VALUES (%s, 'LOGIN', 'Success')
                """, (row[0],))
                conn.commit()
                conn.close()

                st.success(f"Welcome, {row[1]}!")
                st.switch_page("pages/01_Incidents.py")

            else:
                # ❌ Wrong password
                conn.close()
                st.session_state['login_attempts'] += 1

                # Log failed attempt (Changed ? to %s)
                conn2 = get_connection()
                cursor2 = conn2.cursor()
                cursor2.execute("""
                    INSERT INTO AUDIT_LOGS (UserID, ActionType, Status)
                    VALUES (%s, 'LOGIN', 'Failed')
                """, (row[0],))
                conn2.commit()
                conn2.close()

                if st.session_state['login_attempts'] >= MAX_ATTEMPTS:
                    st.session_state['locked_out'] = True
                    st.rerun()
                else:
                    remaining = MAX_ATTEMPTS - st.session_state['login_attempts']
                    st.error("❌ Invalid password.")
        else:
            # ❌ User not found
            conn.close()
            st.session_state['login_attempts'] += 1

            if st.session_state['login_attempts'] >= MAX_ATTEMPTS:
                st.session_state['locked_out'] = True
                st.rerun()
            else:
                remaining = MAX_ATTEMPTS - st.session_state['login_attempts']
                st.error("❌ User not found.")
    else:
        st.warning("⚠️ Please enter both username and password.")
