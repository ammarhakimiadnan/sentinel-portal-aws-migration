import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from db import (get_connection, get_incidents, get_active_incident_ids,
                get_resolved_incident_ids, insert_incident,
                resolve_incident, delete_incident, get_incidents_over_time)
from styles import load_css, show_sidebar_user

if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    st.warning("Please log in first.")
    st.stop()

st.set_page_config(page_title="Sentinel SOC", page_icon="🛡️", layout="wide")
st.markdown(load_css(), unsafe_allow_html=True)
show_sidebar_user()

# ── Global chart theme ──
CHART_LAYOUT = dict(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    font=dict(color='#8B949E', size=13),
    margin=dict(l=0, r=0, t=10, b=0),
    xaxis=dict(showgrid=False, color='#8B949E',
               linecolor='#30363D', title=None),
    yaxis=dict(showgrid=True, gridcolor='#21262D',
               color='#8B949E', title=None),
    legend=dict(orientation='h', yanchor='bottom',
                y=1.02, xanchor='right', x=1,
                font=dict(size=12)),
)

COLOR_MAP = {
    "Phishing":            "#FF4444",
    "Unauthorised Access": "#FF8800",
    "Data Leak":           "#FFD700",
    "Malware":             "#00CC66",
    "Ransomware":          "#00B4D8",
    "Brute Force":         "#A371F7",
    "DDoS":                "#F78166",
    "Insider Threat":      "#79C0FF",
    "Social Engineering":  "#FFA657",
    "Other":               "#8B949E",
}

SEV_COLORS = {
    "Critical": "#FF4444",
    "High":     "#FF8800",
    "Medium":   "#FFD700",
    "Low":      "#00CC66",
}

# ── Fetch all data in one connection ──
conn = get_connection()
cursor = conn.cursor()
cursor.execute("""
    SELECT
        SUM(CASE WHEN Status='Active'   THEN 1 ELSE 0 END),
        SUM(CASE WHEN Status='Resolved' THEN 1 ELSE 0 END),
        COUNT(*),
        SUM(CASE WHEN Status='Active' AND Severity='Critical' THEN 1 ELSE 0 END),
        SUM(CASE WHEN Status='Active' AND Severity='High'     THEN 1 ELSE 0 END),
        SUM(CASE WHEN Status='Active' AND Severity='Medium'   THEN 1 ELSE 0 END),
        SUM(CASE WHEN Status='Active' AND Severity='Low'      THEN 1 ELSE 0 END)
    FROM INCIDENTS
""")
row = cursor.fetchone()

cursor.execute("""
    SELECT Type, COUNT(*) AS Count
    FROM INCIDENTS
    WHERE Status = 'Active'
    GROUP BY Type
    ORDER BY Count DESC
""")
type_rows = cursor.fetchall()
conn.close()

active, resolved, total, critical, high, medium, low = row
resolve_rate = round((resolved / total) * 100) if total > 0 else 0
role = st.session_state['role']

# ══════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════
st.markdown("""
<div style='display:flex; align-items:center; gap:12px; margin-bottom:0.5rem;'>
    <span style='font-size:1.6rem; font-weight:700; color:#C9D1D9;'>
        🛡️ SENTINEL
    </span>
    <span style='font-size:0.9rem; color:#8B949E; margin-top:4px;'>
        Security Operations Center — Incident Management
    </span>
</div>
""", unsafe_allow_html=True)

# ── Action buttons ──
bcol1, bcol2, bcol3, _ = st.columns([1, 1, 1, 5])
with bcol1:
    if role in ['Admin', 'Analyst']:
        if st.button("➕ New Incident", use_container_width=True):
            st.session_state['show_modal'] = 'report'
with bcol2:
    if role in ['Admin', 'Analyst']:
        if st.button("✅ Resolve", use_container_width=True):
            st.session_state['show_modal'] = 'resolve'
with bcol3:
    if role == 'Admin':
        if st.button("🗑️ Delete", use_container_width=True):
            st.session_state['show_modal'] = 'delete'

# ── Modals ──
if st.session_state.get('show_modal') == 'report':
    with st.container(border=True):
        st.markdown("#### ➕ Report New Incident")
        col1, col2 = st.columns(2)
        with col1:
            inc_type = st.selectbox("Type", list(COLOR_MAP.keys()))
            severity = st.radio("Severity",
                                ["Low", "Medium", "High", "Critical"],
                                horizontal=True)
        with col2:
            details = st.text_area("Details",
                                   placeholder="Describe the incident...",
                                   height=100)
        ca, cb = st.columns(2)
        if ca.button("🚨 Submit", use_container_width=True):
            if details:
                insert_incident(inc_type, severity, details,
                                st.session_state['user_id'])
                st.success("✅ Incident reported!")
                st.session_state['show_modal'] = None
                st.rerun()
            else:
                st.warning("Please fill in the details.")
        if cb.button("✖ Cancel", use_container_width=True):
            st.session_state['show_modal'] = None
            st.rerun()

if st.session_state.get('show_modal') == 'resolve':
    with st.container(border=True):
        st.markdown("#### ✅ Resolve Incident")
        active_ids = get_active_incident_ids()
        if active_ids:
            options = {f"#{r[0]} — {r[1]}": r[0] for r in active_ids}
            selected = st.selectbox("Select", list(options.keys()))
            ca, cb = st.columns(2)
            if ca.button("✅ Confirm", use_container_width=True):
                resolve_incident(options[selected],
                                 st.session_state['user_id'])
                st.success("✅ Resolved!")
                st.session_state['show_modal'] = None
                st.rerun()
            if cb.button("✖ Cancel", use_container_width=True):
                st.session_state['show_modal'] = None
                st.rerun()
        else:
            st.info("No active incidents.")
            if st.button("✖ Close"):
                st.session_state['show_modal'] = None
                st.rerun()

if st.session_state.get('show_modal') == 'delete':
    with st.container(border=True):
        st.markdown("#### 🗑️ Delete Incident")
        st.warning("⚠️ Permanent — cannot be undone.")
        all_ids = get_active_incident_ids() + get_resolved_incident_ids()
        if all_ids:
            options = {f"#{r[0]} — {r[1]}": r[0] for r in all_ids}
            selected = st.selectbox("Select", list(options.keys()))
            confirm = st.checkbox("I confirm permanent deletion")
            ca, cb = st.columns(2)
            if ca.button("🗑️ Delete", use_container_width=True,
                         type="primary"):
                if confirm:
                    delete_incident(options[selected],
                                    st.session_state['user_id'])
                    st.success("Deleted.")
                    st.session_state['show_modal'] = None
                    st.rerun()
                else:
                    st.error("Please confirm first.")
            if cb.button("✖ Cancel", use_container_width=True):
                st.session_state['show_modal'] = None
                st.rerun()
        else:
            st.info("No incidents.")
            if st.button("✖ Close"):
                st.session_state['show_modal'] = None
                st.rerun()

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════
# ROW 1 — KPI STRIP
# ══════════════════════════════════════════
k1, k2, k3, k4, k5, k6, k7 = st.columns(7)
kpis = [
    (k1, total,           "Total",       "#C9D1D9"),
    (k2, active,          "Active",      "#FF8800"),
    (k3, resolved,        "Resolved",    "#00CC66"),
    (k4, f"{resolve_rate}%", "Res. Rate","#A371F7"),
    (k5, critical,        "Critical",    "#FF4444"),
    (k6, high,            "High",        "#FF8800"),
    (k7, f"{medium+low}", "Med / Low",   "#8B949E"),
]
for col, val, label, color in kpis:
    with col:
        st.markdown(f"""
        <div style='background:#161B22; border:0.5px solid #30363D;
                    border-top:2px solid {color};
                    border-radius:6px; padding:12px 14px;
                    text-align:center;'>
            <div style='font-size:1.6rem; font-weight:700;
                        color:{color}; line-height:1.2;'>{val}</div>
            <div style='font-size:0.8rem; color:#8B949E;
                        margin-top:4px; text-transform:uppercase;
                        letter-spacing:0.05em;'>{label}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════
# ROW 2 — TREND LINE (full width)
# ══════════════════════════════════════════
st.markdown("""
<div style='font-size:0.85rem; font-weight:600; color:#8B949E;
            text-transform:uppercase; letter-spacing:0.08em;
            margin-bottom:8px;'>📈 Incident Trend (Weekly)</div>
""", unsafe_allow_html=True)

time_data = get_incidents_over_time()
if time_data:
    data = [list(r) for r in time_data]
    df = pd.DataFrame(data, columns=['Date', 'Type', 'Count'])
    df['Date'] = pd.to_datetime(df['Date'])
    df['Week'] = df['Date'].dt.to_period('W').apply(
        lambda r: r.start_time)
    df_weekly = df.groupby(
        ['Week', 'Type'])['Count'].sum().reset_index()

    all_types = sorted(df['Type'].unique().tolist())
    selected = st.multiselect(
        "Types", all_types, default=all_types[:5],
        label_visibility="collapsed",
        key="type_filter"
    )

    if selected:
        df_f = df_weekly[df_weekly['Type'].isin(selected)]
        fig = px.line(df_f, x='Week', y='Count', color='Type',
                      color_discrete_map=COLOR_MAP,
                      markers=True, line_shape='spline')
        fig.update_traces(line=dict(width=2), marker=dict(size=5))
        fig.update_layout(**CHART_LAYOUT, height=280,
                          hovermode='x unified')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Select at least one type.")
else:
    st.info("No data.")

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════
# ROW 3 — DONUT + BAR (side by side below)
# ══════════════════════════════════════════
ch2, ch3 = st.columns([1, 1])

# Donut chart
with ch2:
    st.markdown("""
    <div style='font-size:0.85rem; font-weight:600; color:#8B949E;
                text-transform:uppercase; letter-spacing:0.08em;
                margin-bottom:8px;'>🔴 Severity Split</div>
    """, unsafe_allow_html=True)

    fig_donut = go.Figure(data=[go.Pie(
        labels=["Critical", "High", "Medium", "Low"],
        values=[critical, high, medium, low],
        hole=0.65,
        marker=dict(colors=["#FF4444", "#FF8800",
                            "#FFD700", "#00CC66"]),
        textinfo='none',
        sort=False,
        hovertemplate='%{label}: %{value}<extra></extra>'
    )])
    fig_donut.add_annotation(
        text=f"<b>{active}</b><br><span>Active</span>",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=16, color='#C9D1D9')
    )
    fig_donut.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        showlegend=True,
        legend=dict(orientation='v',
                    font=dict(size=12, color='#8B949E')),
        margin=dict(l=0, r=0, t=0, b=0),
        height=260
    )
    st.plotly_chart(fig_donut, use_container_width=True)

# Horizontal bar chart
with ch3:
    st.markdown("""
    <div style='font-size:0.85rem; font-weight:600; color:#8B949E;
                text-transform:uppercase; letter-spacing:0.08em;
                margin-bottom:8px;'>📊 By Type</div>
    """, unsafe_allow_html=True)

    if type_rows:
        type_df = pd.DataFrame(
            [(r[0], r[1]) for r in type_rows],
            columns=['Type', 'Count']
        )
        fig_bar = px.bar(
            type_df, x='Count', y='Type',
            orientation='h',
            color='Type',
            color_discrete_map=COLOR_MAP
        )
        fig_bar.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#8B949E', size=13),
            margin=dict(l=0, r=0, t=10, b=0),
            height=260,
            showlegend=False,
            xaxis=dict(showgrid=True, gridcolor='#21262D',
                       color='#8B949E', title=None),
            yaxis=dict(showgrid=False, color='#8B949E',
                       title=None,
                       categoryorder='total ascending'),
        )
        fig_bar.update_traces(marker_line_width=0)
        st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("<hr style='border-color:#21262D; margin:8px 0;'>",
            unsafe_allow_html=True)

# ══════════════════════════════════════════
# ROW 4 — INCIDENT RECORDS
# ══════════════════════════════════════════
rec_col, tog_col = st.columns([4, 1])
with rec_col:
    st.markdown("""
    <div style='font-size:0.85rem; font-weight:600; color:#8B949E;
                text-transform:uppercase; letter-spacing:0.08em;
                margin-bottom:8px;'>📋 Incident Records</div>
    """, unsafe_allow_html=True)
with tog_col:
    can_decrypt = role in ['Admin', 'Analyst']
    show_decrypted = (
        st.toggle("🔓 Decrypt", value=False, key="decrypt_toggle")
        if can_decrypt else False
    )
    if not can_decrypt:
        st.caption("🔒 Encrypted")

tab1, tab2 = st.tabs([
    f"🔴 Active ({active})",
    f"✅ Resolved ({resolved})"
])

def render_incidents(rows, resolved=False):
    if not rows:
        st.markdown("""
        <div style='text-align:center; padding:2rem;
                    color:#8B949E; font-size:0.9rem;'>
            No incidents found.
        </div>
        """, unsafe_allow_html=True)
        return

    col_a, col_b = st.columns(2)
    for i, row in enumerate(rows):
        sev_color = SEV_COLORS.get(row[2], "#888")
        border    = "#00CC66" if resolved else sev_color
        type_color = COLOR_MAP.get(row[1], "#8B949E")

        badge = (
            "<span style='color:#00CC66; font-size:0.8rem;"
            " font-weight:600; text-transform:uppercase;"
            " letter-spacing:0.05em;'>✅ RESOLVED</span>"
            if resolved else
            f"<span style='color:{sev_color}; font-size:0.8rem;"
            f" font-weight:600; text-transform:uppercase;"
            f" letter-spacing:0.05em;'>⚠ {row[2]}</span>"
        )

        card = f"""
        <div style='background:#0D1117; border:0.5px solid #21262D;
                    border-left:3px solid {border};
                    border-radius:8px; padding:14px 16px;
                    margin-bottom:10px;'>
            <div style='display:flex; justify-content:space-between;
                        align-items:center; margin-bottom:6px;'>
                <span style='color:{type_color}; font-size:0.9rem;
                             font-weight:600;'>#{row[0]} {row[1]}</span>
                {badge}
            </div>
            <div style='font-size:0.9rem; color:#C9D1D9;
                        margin-bottom:6px; line-height:1.5;'>
                {row[3]}
            </div>
            <div style='font-size:0.8rem; color:#8B949E;'>
                👤 {row[4]} &nbsp;·&nbsp; 🕒 {str(row[5])[:16]}
            </div>
        </div>
        """
        (col_a if i % 2 == 0 else col_b).markdown(
            card, unsafe_allow_html=True)

with tab1:
    render_incidents(
        get_incidents(decrypt=show_decrypted, status='Active'))
with tab2:
    render_incidents(
        get_incidents(decrypt=show_decrypted, status='Resolved'),
        resolved=True)