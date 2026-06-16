import os
import psycopg2
import re
from dotenv import load_dotenv
from cryptography.fernet import Fernet

load_dotenv()

SECRET_KEY = os.environ.get('FERNET_KEY').encode()
cipher_suite = Fernet(SECRET_KEY)

def get_connection():
    conn = psycopg2.connect(
        host=os.environ.get('DB_HOST'), 
        database=os.environ.get('DB_NAME'),
        user=os.environ.get('DB_USER'), 
        password=os.environ.get('DB_PASSWORD')  
    )
    return conn

def get_incidents(decrypt=False, status='Active'):
    conn = get_connection()
    cursor = conn.cursor()
    
    # Notice: ? placeholders changed to %s for PostgreSQL
    cursor.execute("""
        SELECT i.IncidentID, i.Type, i.Severity, i.DetailsEncrypted,
               u.Username, i.CreatedAt, i.Status
        FROM INCIDENTS i
        JOIN USERS u ON i.ReporterID = u.UserID
        WHERE i.Status = %s
        ORDER BY i.CreatedAt DESC
    """, (status,))
    rows = cursor.fetchall()
    conn.close()

    result = []
    # DECRYPTING IN PYTHON INSTEAD OF DATABASE
    for row in rows:
        incident_id, inc_type, severity, details_encrypted, username, created_at, inc_status = row
        
        if decrypt and details_encrypted:
            try:
                # Convert memoryview/BYTEA to bytes, then decrypt and decode to string
                details = cipher_suite.decrypt(bytes(details_encrypted)).decode('utf-8')
            except Exception as e:
                details = f"[Decryption Error]"
        else:
            details = '*** ENCRYPTED ***'
            
        result.append((incident_id, inc_type, severity, details, username, created_at, inc_status))

    return result

def get_incidents_over_time():
    conn = get_connection()
    cursor = conn.cursor()
    # Changed CAST(CreatedAt AS DATE) to PostgreSQL shorthand CreatedAt::DATE
    cursor.execute("""
        SELECT 
            CreatedAt::DATE AS IncidentDate,
            Type,
            COUNT(*) AS Count
        FROM INCIDENTS
        GROUP BY CreatedAt::DATE, Type
        ORDER BY IncidentDate ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_active_incident_ids():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT IncidentID, Type FROM INCIDENTS WHERE Status = 'Active' ORDER BY IncidentID")
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_resolved_incident_ids():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT IncidentID, Type FROM INCIDENTS WHERE Status = 'Resolved' ORDER BY IncidentID")
    rows = cursor.fetchall()
    conn.close()
    return rows

def sanitize_input(text):
    if not text:
        return text
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'(javascript:|on\w+=|<script)', '', text, flags=re.IGNORECASE)
    return text.strip()

def insert_incident(inc_type, severity, details, user_id):
    inc_type = sanitize_input(inc_type)
    details = sanitize_input(details)

    # ENCRYPT IN PYTHON BEFORE INSERTING
    details_encrypted = None
    if details:
        details_encrypted = cipher_suite.encrypt(details.encode('utf-8'))

    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO INCIDENTS 
            (Type, Severity, Details, DetailsEncrypted, ReporterID, Status)
        VALUES (%s, %s, %s, %s, %s, 'Active')
    """, (inc_type, severity, '***ENCRYPTED***', details_encrypted, user_id))
    
    cursor.execute("""
        INSERT INTO AUDIT_LOGS (UserID, ActionType, Status)
        VALUES (%s, 'INSERT_INCIDENT', 'Success')
    """, (user_id,))
    
    conn.commit()
    conn.close()

def resolve_incident(incident_id, user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE INCIDENTS SET Status = 'Resolved' WHERE IncidentID = %s", (incident_id,))
    cursor.execute("""
        INSERT INTO AUDIT_LOGS (UserID, ActionType, Status)
        VALUES (%s, 'RESOLVE_INCIDENT', 'Success')
    """, (user_id,))
    conn.commit()
    conn.close()

def delete_incident(incident_id, user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM INCIDENTS WHERE IncidentID = %s", (incident_id,))
    cursor.execute("""
        INSERT INTO AUDIT_LOGS (UserID, ActionType, Status)
        VALUES (%s, 'DELETE_INCIDENT', 'Success')
    """, (user_id,))
    conn.commit()
    conn.close()

def get_all_users(role):
    conn = get_connection()
    cursor = conn.cursor()
    # Fetch raw data first. We remove the SQL-side LEFT() logic used in SQL Server.
    cursor.execute("""
        SELECT u.UserID, u.Username, r.RoleName, u.ContactNumber
        FROM USERS u JOIN ROLES r ON u.RoleID = r.RoleID
    """)
    rows = cursor.fetchall()
    conn.close()

    result = []
    # PYTHON-SIDE DYNAMIC DATA MASKING
    for row in rows:
        user_id, username, role_name, contact_number = row
        
        if role != 'Admin' and contact_number:
            # Mask the contact number: '0111000001' -> 'XXXXXXX001'
            contact_number = "X" * max(0, len(contact_number) - 3) + contact_number[-3:]
            
        result.append((user_id, username, role_name, contact_number))

    return result

def get_db_stats():
    conn = get_connection()
    cursor = conn.cursor()
    stats = {}
    
    cursor.execute("SELECT COUNT(*) FROM INCIDENTS")
    stats['total_incidents'] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM INCIDENTS WHERE Status = 'Active'")
    stats['active'] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM INCIDENTS WHERE Status = 'Resolved'")
    stats['resolved'] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM USERS")
    stats['total_users'] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM AUDIT_LOGS")
    stats['total_audit'] = cursor.fetchone()[0]
    
    # Replaced CAST(GETDATE() AS DATE) with CURRENT_DATE
    cursor.execute("""
        SELECT COUNT(*) FROM AUDIT_LOGS
        WHERE ActionTime >= CURRENT_DATE
    """)
    stats['actions_today'] = cursor.fetchone()[0]
    
    conn.close()
    return stats

def get_audit_summary():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Changed SELECT TOP 10 to standard PostgreSQL LIMIT 10
    cursor.execute("""
        SELECT 
            a.ActionType,
            u.Username,
            a.ActionTime,
            a.Status
        FROM AUDIT_LOGS a
        LEFT JOIN USERS u ON a.UserID = u.UserID
        ORDER BY a.ActionTime DESC
        LIMIT 10
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_action_counts():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ActionType, COUNT(*) as Count
        FROM AUDIT_LOGS
        GROUP BY ActionType
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_roles():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT RoleID, RoleName FROM ROLES")
    rows = cursor.fetchall()
    conn.close()
    return rows

def update_user_role(user_id, role_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE USERS SET RoleID = %s WHERE UserID = %s", (role_id, user_id))
    conn.commit()
    conn.close()