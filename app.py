import streamlit as st
from supabase import create_client
from datetime import datetime, timedelta
from streamlit_calendar import calendar

# 1. Setup & Secrets
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

def get_tasks():
    return supabase.table("tasks").select("*").execute().data

def main():
    st.set_page_config(page_title="Household Sync", layout="wide")
    st.title(" Household Checklist")

    tasks = get_tasks()
    today = datetime.now().date()

    # 2. Reset & Prediction Logic
    for task in tasks:
        last_reset = datetime.strptime(task['last_reset'], '%Y-%m-%d').date()
        needs_reset = False

        # Daily Reset
        if task['frequency'] == 'daily' and last_reset < today:
            needs_reset = True
        
        # Weekly Reset 
        elif task['frequency'] == 'weekly' and (today - last_reset).days >= 7:
            needs_reset = True
            
        # Monthly Reset
        elif task['frequency'] == 'monthly':
            if (today.month != last_reset.month) or (today.year != last_reset.year):
                needs_reset = True
        
        if needs_reset:
            supabase.table('tasks').update({
                "is_completed": False,
                "last_reset": str(today)
            }).eq("id", task['id']).execute()
    
    # 3. Interactive Tabs

    # --- Sidebar for Management ---
    with st.sidebar:
        st.header("⚙️ Task Manager")
        
        # A. ADD NEW TASK
        st.subheader("Add New Task")
        new_name = st.text_input("Task Name", placeholder="e.g., Take out trash")
        new_freq = st.selectbox("Frequency", ["daily", "weekly", "monthly"])
        
        if st.button("➕ Add Task"):
            if new_name:
                supabase.table("tasks").insert({
                    "household_id": HOUSE_ID, # Use your specific ID
                    "task_name": new_name,
                    "frequency": new_freq,
                    "is_completed": False,
                    "last_reset": str(today)
                }).execute()
                st.success(f"Added {new_name}!")
                st.rerun()
            else:
                st.error("Please enter a name.")

        st.divider()

        # B. DELETE TASKS
        st.subheader("Remove Task")
        task_to_delete = st.selectbox("Select task to remove", [t['task_name'] for t in tasks])
        if st.button("🗑️ Delete Task", type="primary"):
            # Find the ID of the selected task name
            selected_id = next(t['id'] for t in tasks if t['task_name'] == task_to_delete)
            supabase.table("tasks").delete().eq("id", selected_id).execute()
            st.warning(f"Deleted {task_to_delete}")
            st.rerun()
    # Start of top nav bar
    tab1, tab2 = st.tabs([" Checklist", " Calendar View"])

    with tab1:
        st.subheader("Today's Chores")
        for t in tasks:
            status = st.checkbox(f"{t['task_name']} ({t['frequency']})", value=t['is_completed'], key=t['id'])
            
            if status != t['is_completed']:
                # Update both status and date so the calendar knows when it was last done
                supabase.table("tasks").update({
                    "is_completed": status,
                    "last_reset": str(today)
                }).eq('id', t['id']).execute()
                st.rerun()
    
    with tab2:
        # Generate Calendar events  
        events = []
        for t in tasks:
            events.append({
                "title": t['task_name'],
                "start": t['last_reset'] if t['is_completed'] else str(today),
                "color": "#28a745" if t['is_completed'] else '#dc3545'
            })

        calendar(events=events, options={'initialView': "dayGridMonth"})

if __name__ == "__main__":

    main()
