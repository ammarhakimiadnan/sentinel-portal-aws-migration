import streamlit as st
from db import get_connection
from styles import load_css, show_sidebar_user

if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    st.warning("Please log in first.")
    st.stop()

if st.session_state['role'] != 'Admin':
    st.error("🚫 Access denied. Admins only.")
    st.stop()

st.set_page_config(page_title="Audit Logs", page_icon="📋", layout="wide")
st.markdown(load_css(), unsafe_allow_html=True)
show_sidebar_user()

st.markdown("# 📋 Audit Logs")
st.caption("All database actions recorded for compliance and monitoring.")
st.divider()

conn = get_connection()
cursor = conn.cursor()

# Fetch audit logs joined with incident details where possible
cursor.execute("""
    SELECT
        a.AuditID,
        ISNULL(u.Username, 'Unknown') AS Username,
        a.ActionType,
        a.ActionTime,
        a.Status,
        u.UserID,
        r.RoleName
    FROM AUDIT_LOGS a
    LEFT JOIN USERS u ON a.UserID = u.UserID
    LEFT JOIN ROLES r ON u.RoleID = r.RoleID
    ORDER BY a.ActionTime DESC
""")
rows = cursor.fetchall()
conn.close()

if rows:
    # Summary stat cards
    action_types = [r[2] for r in rows]
    c1, c2, c3, c4 = st.columns(4)
    for col, val, label, color in [
        (c1, len(rows),                              "Total Entries", "#00B4D8"),
        (c2, action_types.count("INSERT_INCIDENT"),  "Inserts",       "#00CC66"),
        (c3, action_types.count("RESOLVE_INCIDENT"), "Resolves",      "#FFD700"),
        (c4, action_types.count("DELETE_INCIDENT"),  "Deletes",       "#FF4444"),
    ]:
        with col:
            st.markdown(f"""<div class='stat-card'>
                <div class='stat-value' style='color:{color};'>{val}</div>
                <div class='stat-label'>{label}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Filter bar
    col1, col2 = st.columns([2, 2])
    with col1:
        filter_action = st.selectbox("Filter by Action", [
            "All", "INSERT_INCIDENT", "RESOLVE_INCIDENT", "DELETE_INCIDENT"
        ])
    with col2:
        filter_user = st.text_input("Filter by Username", placeholder="e.g. alex")

    st.markdown("<br>", unsafe_allow_html=True)

    # Apply filters
    filtered = rows
    if filter_action != "All":
        filtered = [r for r in filtered if r[2] == filter_action]
    if filter_user:
        filtered = [r for r in filtered if filter_user.lower() in r[1].lower()]

    st.caption(f"Showing {len(filtered)} of {len(rows)} entries")
    st.markdown("---")

    for row in filtered:
        audit_id   = row[0]
        username   = row[1]
        action     = row[2]
        time       = row[3]
        status     = row[4]
        user_id    = row[5]
        role_name  = row[6] or "Unknown"

        status_color = "#00CC66" if status == "Success" else "#FF4444"
        action_icon = {
            "INSERT_INCIDENT":  "➕",
            "DELETE_INCIDENT":  "🗑️",
            "RESOLVE_INCIDENT": "✅",
            "LOGIN":            "🔐"
        }.get(action, "📌")

        action_label = {
            "INSERT_INCIDENT":  "New incident reported",
            "DELETE_INCIDENT":  "Incident permanently deleted",
            "RESOLVE_INCIDENT": "Incident marked as resolved",
            "LOGIN":            "User login"
        }.get(action, action)

        # Expandable row
        with st.expander(
            f"{action_icon}  {action_label}  —  "
            f"by **{username}**  |  🕒 {time}  |  "
            f"{'✅ Success' if status == 'Success' else '❌ Failed'}"
        ):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown("**👤 User Details**")
                st.markdown(f"""
                <div class='audit-row'>
                    <b>Username:</b> {username}<br>
                    <b>User ID:</b> {user_id}<br>
                    <b>Role:</b> <span style='color:#00B4D8;'>{role_name}</span>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                st.markdown("**📋 Action Details**")
                st.markdown(f"""
                <div class='audit-row'>
                    <b>Action:</b> {action}<br>
                    <b>Description:</b> {action_label}<br>
                    <b>Audit ID:</b> #{audit_id}
                </div>
                """, unsafe_allow_html=True)

            with col3:
                st.markdown("**🕒 Time & Status**")
                status_badge = (
                    f"<span style='color:#00CC66;'>✅ {status}</span>"
                    if status == "Success"
                    else f"<span style='color:#FF4444;'>❌ {status}</span>"
                )
                st.markdown(f"""
                <div class='audit-row'>
                    <b>Timestamp:</b> {time}<br>
                    <b>Status:</b> {status_badge}
                </div>
                """, unsafe_allow_html=True)

            # If it's an incident action, fetch the related incident
            if action in ["INSERT_INCIDENT", "DELETE_INCIDENT", "RESOLVE_INCIDENT"]:
                st.markdown("**🚨 Related Incident**")
                try:
                    conn2 = get_connection()
                    cursor2 = conn2.cursor()

                    if action == "INSERT_INCIDENT":
                        # Get the most recent incident by this user
                        cursor2.execute("""
                            SELECT TOP 1 IncidentID, Type, Severity, Status, CreatedAt
                            FROM INCIDENTS
                            WHERE ReporterID = ?
                            ORDER BY CreatedAt DESC
                        """, (user_id,))
                    elif action in ["DELETE_INCIDENT", "RESOLVE_INCIDENT"]:
                        # Get recently modified incident
                        cursor2.execute("""
                            SELECT TOP 1 IncidentID, Type, Severity, Status, CreatedAt
                            FROM INCIDENTS
                            WHERE ReporterID = ?
                            ORDER BY CreatedAt DESC
                        """, (user_id,))

                    inc = cursor2.fetchone()
                    conn2.close()

                    if inc:
                        sev_color = {
                            "Critical": "#FF4444", "High": "#FF8800",
                            "Medium":   "#FFD700", "Low":  "#00CC66"
                        }.get(inc[2], "#888")
                        st.markdown(f"""
                        <div class='audit-row'>
                            <b>Incident ID:</b> #{inc[0]}<br>
                            <b>Type:</b> {inc[1]}<br>
                            <b>Severity:</b>
                            <span style='color:{sev_color};'>{inc[2]}</span><br>
                            <b>Current Status:</b> {inc[3]}<br>
                            <b>Created:</b> {inc[4]}
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.caption("No related incident found "
                                   "(may have been deleted).")
                except Exception:
                    st.caption("Could not fetch related incident details.")
else:
    st.info("No audit logs found.")