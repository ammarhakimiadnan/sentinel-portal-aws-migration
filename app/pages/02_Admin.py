import streamlit as st
import pandas as pd
from db import (get_all_users, get_db_stats, get_audit_summary,
                get_action_counts, get_roles, update_user_role)
from styles import load_css, show_sidebar_user

if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    st.warning("Please log in first.")
    st.stop()

if st.session_state['role'] != 'Admin':
    st.error("🚫 Access denied. Admins only.")
    st.stop()

st.set_page_config(page_title="Admin Panel", page_icon="⚙️", layout="wide")
st.markdown(load_css(), unsafe_allow_html=True)
show_sidebar_user()

st.markdown("# ⚙️ Admin Panel")
st.caption("Full system overview — visible to Administrators only.")
st.divider()

# DB Stats
stats = get_db_stats()
st.markdown('<div class="section-header">📊 System Statistics</div>',
            unsafe_allow_html=True)

c1, c2, c3, c4, c5, c6 = st.columns(6)
for col, val, label, color in [
    (c1, stats['total_incidents'], "Total Incidents", "#00B4D8"),
    (c2, stats['active'],          "Active",          "#FF8800"),
    (c3, stats['resolved'],        "Resolved",        "#00CC66"),
    (c4, stats['total_users'],     "Users",           "#A371F7"),
    (c5, stats['total_audit'],     "Audit Entries",   "#F78166"),
    (c6, stats['actions_today'],   "Actions Today",   "#FFD700"),
]:
    with col:
        st.markdown(f"""<div class='stat-card'>
            <div class='stat-value' style='color:{color};'>{val}</div>
            <div class='stat-label'>{label}</div>
        </div>""", unsafe_allow_html=True)

st.divider()

left, right = st.columns([1, 1])

# User Management
with left:
    st.markdown('<div class="section-header">👥 User Management</div>',
                unsafe_allow_html=True)
    users = get_all_users('Admin')
    roles = get_roles()
    role_map   = {r[1]: r[0] for r in roles}
    role_names = [r[1] for r in roles]

    for user in users:
        uid, uname, urole, ucontact = user
        role_color = {
            "Admin":   "#FF4444",
            "Analyst": "#00B4D8",
            "Viewer":  "#8B949E"
        }.get(urole, "#888")

        with st.expander(f"👤 {uname}  —  [{urole}]"):
            st.markdown(f"""
            **User ID:** `{uid}`  
            **Username:** `{uname}`  
            **Role:** <span style='color:{role_color};font-weight:600;'>{urole}</span>  
            **Contact:** `{ucontact}`
            """, unsafe_allow_html=True)
            new_role = st.selectbox(
                "Change Role", role_names,
                index=role_names.index(urole),
                key=f"role_{uid}"
            )
            if st.button("💾 Update Role", key=f"update_{uid}",
                         width='stretch'):
                update_user_role(uid, role_map[new_role])
                st.success(f"✅ {uname}'s role updated to {new_role}!")
                st.rerun()

# Activity + Audit
with right:
    st.markdown('<div class="section-header">📈 Activity Overview</div>',
                unsafe_allow_html=True)
    action_counts = get_action_counts()
    if action_counts:
        try:
            chart_df = pd.DataFrame(
                [(row[0], row[1]) for row in action_counts],
                columns=["Action", "Count"]
            )
            st.bar_chart(chart_df.set_index("Action"), color="#00B4D8")
        except Exception as e:
            # Fallback — show as table if chart fails
            for row in action_counts:
                st.markdown(f"""
                <div class='audit-row'>
                    📌 <b>{row[0]}</b> — {row[1]} action(s)
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No activity data yet.")

    st.markdown('<div class="section-header">🕒 Recent Audit Activity</div>',
                unsafe_allow_html=True)
    audit = get_audit_summary()
    if audit:
        for row in audit:
            action_icon = {
                "INSERT_INCIDENT":  "➕",
                "DELETE_INCIDENT":  "🗑️",
                "RESOLVE_INCIDENT": "✅",
                "LOGIN":            "🔐"
            }.get(row[0], "📌")
            status_color = "#00CC66" if row[3] == "Success" else "#FF4444"
            st.markdown(f"""
            <div class='audit-row'>
                {action_icon} <b>{row[0]}</b> by
                <b>{row[1] or 'System'}</b>
                &nbsp;|&nbsp; 🕒 {row[2]}
                &nbsp;|&nbsp;
                <span style='color:{status_color};'>● {row[3]}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No audit logs yet.")