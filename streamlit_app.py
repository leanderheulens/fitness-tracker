import streamlit as st
import pandas as pd
import os
from datetime import date

CSV_FILE = 'workouts.csv'

# Load existing data or create new DataFrame
def load_data():
    if os.path.exists(CSV_FILE):
        return pd.read_csv(CSV_FILE, parse_dates=['Date'])
    return pd.DataFrame(columns=['Date','Exercise','Weight','Sets','Reps','Notes'])

# Save DataFrame to CSV
def save_data(df):
    df.to_csv(CSV_FILE, index=False)

st.title("🏋️ Fitness Tracker")

# Initial load
df_all = load_data()

# Sidebar: Log new workout
st.sidebar.header("Log New Workout")
with st.sidebar.form("entry_form"):
    entry_date = st.date_input("Date", date.today())
    # Exercise selection
    exercises = sorted(df_all['Exercise'].dropna().unique())
    exercises.append("Other")
    choice = st.selectbox("Exercise", exercises)
    if choice == "Other":
        exercise = st.text_input("New Exercise")
    else:
        exercise = choice
        # Show previous entries for this exercise
        prev = df_all[df_all['Exercise']==exercise].sort_values('Date', ascending=False)
        if not prev.empty:
            st.markdown("**Previous entries:**")
            st.table(prev[['Date','Weight','Sets','Reps','Notes']].head(5))
    weight = st.number_input("Weight (kg)", min_value=0.0, step=0.5)
    sets = st.number_input("Sets", min_value=1, step=1)
    reps = st.number_input("Reps", min_value=1, step=1)
    notes = st.text_area("Notes")
    submitted = st.form_submit_button("Add Entry")
    if submitted:
        if not exercise:
            st.sidebar.error("Please specify an exercise.")
        else:
            new_entry = pd.DataFrame([{ 
                'Date': entry_date,
                'Exercise': exercise,
                'Weight': weight,
                'Sets': sets,
                'Reps': reps,
                'Notes': notes
            }])
            df_all = pd.concat([load_data(), new_entry], ignore_index=True)
            save_data(df_all)
            st.sidebar.success("Entry added!")

# Main display
if df_all.empty:
    st.info("No workout data yet. Log entries using the sidebar form.")
else:
    # Ensure Date is datetime
    df_all['Date'] = pd.to_datetime(df_all['Date'], errors='coerce')
    df_all = df_all.dropna(subset=['Date'])
    st.subheader("Recent Entries")
    st.dataframe(df_all.sort_values('Date', ascending=False).head(20))

    # Progress chart: individual weight over time
    st.subheader("Progress Chart")
    exercises_chart = [''] + sorted(df_all['Exercise'].unique())
    selected = st.selectbox("Select Exercise to Chart", exercises_chart)
    if selected:
        df_ex = df_all[df_all['Exercise']==selected].sort_values('Date')
        # Line chart of weight per session
        chart_df = df_ex[['Date','Weight']].drop_duplicates(subset=['Date'], keep='last')
        st.line_chart(data=chart_df, x='Date', y='Weight', height=300)

    st.markdown("---")
    st.markdown("*Data stored locally in `workouts.csv`.*")
