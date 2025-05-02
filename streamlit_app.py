import streamlit as st
import pandas as pd
import os
from datetime import date

# File to store workout data
CSV_FILE = 'workouts.csv'

# Load existing data or create new DataFrame
def load_data():
    if os.path.exists(CSV_FILE):
        return pd.read_csv(CSV_FILE, parse_dates=['Date'])
    return pd.DataFrame(columns=['Date','Exercise','Weight','Sets','Reps','Notes'])

def save_data(df):
    df.to_csv(CSV_FILE, index=False)

# App title
st.title("🏋️ Fitness Tracker")

# Always reload data for fresh display
df_all = load_data()

# Sidebar: Logging form
st.sidebar.header("Log New Workout")
with st.sidebar.form("entry_form"):
    entry_date = st.date_input("Date", date.today())
    exercises_list = sorted(df_all['Exercise'].dropna().unique())
    exercises_list.append("Other")
    choice = st.selectbox("Exercise", exercises_list)
    if choice == "Other":
        exercise = st.text_input("New Exercise")
    else:
        exercise = choice
    weight = st.number_input("Weight (kg)", min_value=0.0, step=0.5)
    sets = st.number_input("Sets", min_value=1, step=1)
    reps = st.number_input("Reps", min_value=1, step=1)
    notes = st.text_area("Notes")
    if st.form_submit_button("Add Entry"):
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
            updated_df = pd.concat([load_data(), new_entry], ignore_index=True)
            save_data(updated_df)
            st.sidebar.success("Entry added!")
            # update in-memory df for immediate display
            df_all = updated_df

# Main display
if df_all.empty:
    st.info("No workout data yet. Log entries using the sidebar form.")
else:
    # Ensure Date column is datetime
    df_all['Date'] = pd.to_datetime(df_all['Date'])

    st.subheader("Recent Entries")
    st.dataframe(df_all.sort_values('Date', ascending=False).head(20))

    st.subheader("Progress Charts")
    exercises_for_chart = [''] + sorted(df_all['Exercise'].unique())
    selected = st.selectbox("Select Exercise to Chart", exercises_for_chart)
    if selected:
        df_ex = df_all[df_all['Exercise'] == selected].sort_values('Date')
        # Plot max weight per date
        max_df = df_ex.groupby('Date', as_index=False)['Weight'].max()
        st.line_chart(data=max_df, x='Date', y='Weight')
        # Plot weekly volume
        df_ex['Volume'] = df_ex['Weight'] * df_ex['Sets'] * df_ex['Reps']
        weekly = df_ex.resample('W-MON', on='Date')['Volume'].sum().reset_index()
        st.bar_chart(data=weekly, x='Date', y='Volume')

    st.markdown("---")
    st.markdown("*Data stored locally in `workouts.csv`.*")
