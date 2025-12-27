import streamlit as st
from supabase import create_client
from supabase import datetime, timedelta
from streamlit_calender import calender

#1 Setup & Secrets
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

def get_tasks():
    return supabase.table("tasks").select("*").execute().data

def main ():
    st.set_page_config(page_title="Household Sync", layout="wide")
    st.title("Household Checklist")

    tasks = get_tasks()
    today = datetime.now().date()

    #2 Reset & Prediction Logic
    for tasks in tasks:
        last_reset = datetime.strptime(task['last_reset'], '%Y-%m-%d').date()
        needs_reset = False

        #daily 
        if task['frequency'] == 'daily' and last_reset < today:
            needs_reset = True
        #weekly
        elif task['frequency'] == 'daily' and (today - last_reset).days >= 7:
            needs_reset = True
        #Monthly
        elif task['frequency'] == 'monthly':
            if (today.month != last_reset.month) or (today.year != last_reset.year):
                needs_reset = True
        if needs_reset:
            supabase.table('tasks').update({
                "is_completed": False,
                "last_reset": str(today)
            }).eq("id", task['id']).execute()
    
    # Interactive Tabs
    tab1, tab2 = st.tabs(["Checklist", "Calender View"])

    with tab1:
        st.subheader("Today's Chores")
        for t in tasks:
            status = st.checkbox(f"{t['task_name']} ({t['frequency']}), value=t['is_completed'], key = t['id']")
            if status != t['is_completed']:
                supabase.table("tasks").update({"is_completed": status}).eq('id', t['id']).execute()
    
    with tab2
        #generate Calander events  
        events = []
        for t in tasks:
            #show when it was last done or when its due
            events.append({
                "title": t['task_name'],
                "start": t['last_reset'] if t['is_completed'] else str(today),
                "color": "#28a745" if t['is_completed'] else '#dc3545'
            })

        calander(events=events, options={'initialView': "dayGridMonth"})
if __name__ == "__main__":
    main()




