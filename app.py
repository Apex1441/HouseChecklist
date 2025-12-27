import streamlit as st
from supabase import create_client
from datetime import datetime
from streamlit_calendar import calendar

# --- 1. CONFIGURATION AND CONNECTION ---
# These keys must be configured in your Streamlit Cloud Secrets dashboard
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase = create_client(URL, KEY)
except Exception:
    st.error("API Keys missing. Please configure Streamlit Secrets.")
    st.stop()

def main():
    st.set_page_config(page_title="Household MIS", layout="wide")

    # --- 2. USER AUTHENTICATION SYSTEM ---
    if "user" not in st.session_state:
        st.session_state.user = None

    if st.session_state.user is None:
        st.title("Household Login")
        choice = st.radio("Select Action", ["Login", "Sign Up"], horizontal=True)
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        
        if choice == "Sign Up":
            if st.button("Create Account"):
                supabase.auth.sign_up({"email": email, "password": password})
                st.info("Account created. Please log in.")
        else:
            if st.button("Log In"):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state.user = res.user
                    st.rerun()
                except Exception:
                    st.error("Invalid credentials.")
        return

    # --- 3. HOUSEHOLD AUTHORIZATION (MULTI-TENANCY) ---
    if "house_key" not in st.session_state:
        st.title("Join a Household")
        hk = st.text_input("Enter your Private House Key", type="password")
        if st.button("Enter House"):
            if len(hk) >= 4:
                st.session_state.house_key = hk
                st.rerun()
            else:
                st.error("Key must be at least 4 characters.")
        return

    # --- 4. SESSION VARIABLES ---
    user_email = st.session_state.user.email
    house_key = st.session_state.house_key
    today = datetime.now().date()

    # --- 5. LOGIC: FETCH AND RESET TASKS ---
    # Database query filtered by the unique House Key
    response = supabase.table("tasks").select("*").eq("house_key", house_key).execute()
    tasks = response.data

    for task in tasks:
        if task['frequency'] == 'one-time':
            continue

        last_reset = datetime.strptime(task['last_reset'], '%Y-%m-%d').date()
        needs_reset = False
        
        if task['frequency'] == 'daily' and last_reset < today:
            needs_reset = True
        elif task['frequency'] == 'weekly' and (today - last_reset).days >= 7:
            needs_reset = True
        elif task['frequency'] == 'monthly' and (today.month != last_reset.month or today.year != last_reset.year):
            needs_reset = True

        if needs_reset:
            supabase.table("tasks").update({"is_completed": False, "last_reset": str(today)}).eq("id", task['id']).execute()

    # --- 6. USER INTERFACE ---
    st.sidebar.title(f"House Key: {house_key}")
    st.sidebar.write(f"User: {user_email}")
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.session_state.pop("house_key")
        st.rerun()

    tab1, tab2, tab3, tab4 = st.tabs(["Checklist", "Calendar", "Audit Log", "Management"])

    with tab1:
        st.subheader("Household Tasks")
        if not tasks: st.info("No tasks registered for this household.")
        for t in tasks:
            col1, col2 = st.columns([0.1, 0.9])
            is_done = col2.checkbox(f"{t['task_name']} ({t['frequency']})", value=t['is_completed'], key=t['id'])
            
            if is_done != t['is_completed']:
                supabase.table("tasks").update({"is_completed": is_done, "last_reset": str(today)}).eq("id", t['id']).execute()
                
                # Transactional Logging
                supabase.table("audit_log").insert({
                    "task_name": t['task_name'],
                    "user_email": user_email,
                    "house_key": house_key,
                    "action": "Completed" if is_done else "Unchecked"
                }).execute()
                st.rerun()

    with tab2:
        st.subheader("Schedule View")
        events = [{"title": t['task_name'], "start": t['last_reset'], "color": "#28a745" if t['is_completed'] else "#dc3545"} for t in tasks]
        calendar(events=events, options={"initialView": "dayGridMonth"})

    with tab3:
        st.subheader("System Audit Log")
        logs = supabase.table("audit_log").select("*").eq("house_key", house_key).order("action_timestamp", desc=True).limit(15).execute().data
        for l in logs:
            st.write(f"{l['action_timestamp'][11:16]} | {l['user_email']} {l['action'].lower()} {l['task_name']}")

    with tab4:
        st.subheader("Task Administration")
        new_name = st.text_input("New Task Name")
        new_freq = st.selectbox("Frequency", ["daily", "weekly", "monthly", "one-time"])
        if st.button("Register Task"):
            supabase.table("tasks").insert({
                "task_name": new_name, 
                "frequency": new_freq, 
                "house_key": house_key, 
                "last_reset": str(today)
            }).execute()
            st.rerun()

if __name__ == "__main__":
    main()

