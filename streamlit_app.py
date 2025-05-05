import streamlit as st
import pandas as pd
import os
import re
from datetime import date

# Filenames
CSV_FILE = 'workouts.csv'
EXCEL_FILE = 'pushpull.xlsx'

# Initialize session state for form visibility
if 'show_form' not in st.session_state:
    st.session_state.show_form = False

# Load existing data or seed from Excel
def load_data():
    if os.path.exists(CSV_FILE):
        return pd.read_csv(CSV_FILE, parse_dates=['Date'], dayfirst=True)
    if os.path.exists(EXCEL_FILE):
        df_wide = pd.read_excel(EXCEL_FILE)
        if 'Oefening' in df_wide.columns:
            df_wide.rename(columns={'Oefening': 'Exercise'}, inplace=True)
        df_melt = df_wide.melt(id_vars=['Exercise'], var_name='Date', value_name='Entry')
        df_melt.dropna(subset=['Entry'], inplace=True)
        rows = []
        for _, row in df_melt.iterrows():
            try:
                entry_date = pd.to_datetime(row['Date'], dayfirst=True)
            except:
                continue
            for part in str(row['Entry']).split('+'):
                m = re.match(r"(\d+)\s*kg.*?\(([^)]+)\)", part)
                if not m:
                    continue
                weight = int(m.group(1))
                for seg in m.group(2).split('+'):
                    seg = seg.strip()
                    if 'x' not in seg:
                        continue
                    sets, reps = seg.split('x')
                    try:
                        rows.append({
                            'Date': entry_date,
                            'Exercise': row['Exercise'],
                            'Weight': weight,
                            'Sets': int(sets),
                            'Reps': int(reps),
                            'Notes': ''
                        })
                    except:
                        continue
        df = pd.DataFrame(rows)
        if not df.empty:
            df.to_csv(CSV_FILE, index=False)
        return df
    return pd.DataFrame(columns=['Date','Exercise','Weight','Sets','Reps','Notes'])

# Save DataFrame to CSV
def save_data(df):
    df.to_csv(CSV_FILE, index=False)

# App title
st.title("🏋️ Fitness Tracker")

# Load or seed data
df_all = load_data()
df_all.sort_values('Date', ascending=False, inplace=True)

# Main button to show/hide form
if st.button("Log New Workout"):
    st.session_state.show_form = True

# Display form in a container when flagged
if st.session_state.show_form:
    with st.container():
        st.subheader("Log New Workout")
        with st.form("entry_form"):
            entry_date = st.date_input("Date", date.today())
            existing = sorted(df_all['Exercise'].dropna().unique())
            existing.append("Other")
            choice = st.selectbox("Exercise", existing)
            if choice == "Other":
                exercise = st.text_input("New Exercise Name")
            else:
                exercise = choice
                history = df_all[df_all['Exercise'] == exercise]
                if not history.empty:
                    st.markdown(f"**Previous entries for {exercise}:**")
                    st.table(history[['Date','Weight','Sets','Reps','Notes']].head(5))
            weight = st.number_input("Weight (kg)", min_value=0.0, step=0.5)
            sets = st.number_input("Sets", min_value=1, step=1)
            reps = st.number_input("Reps", min_value=1, step=1)
            notes = st.text_area("Notes")
            submitted = st.form_submit_button("Add Workout")
            if submitted:
                if not exercise:
                    st.error("Please enter an exercise name.")
                else:
                    new_row = pd.DataFrame([{ 
                        'Date': entry_date,
                        'Exercise': exercise,
                        'Weight': weight,
                        'Sets': sets,
                        'Reps': reps,
                        'Notes': notes
                    }])
                    df_new = pd.concat([load_data(), new_row], ignore_index=True)
                    save_data(df_new)
                    st.success("Workout added!")
                    # hide form and rerun to refresh display
                    st.session_state.show_form = False
                    st.experimental_rerun()

# Display recent entries
st.subheader("Recent Entries")
st.dataframe(df_all.head(20))

# Progress chart
st.subheader("Progress Chart")
options = [''] + sorted(df_all['Exercise'].unique())
selected = st.selectbox("Select Exercise to Chart", options)
if selected:
    df_ex = df_all[df_all['Exercise'] == selected].sort_values('Date')
    chart_df = df_ex[['Date','Weight']].drop_duplicates(subset=['Date'], keep='last')
    st.line_chart(data=chart_df, x='Date', y='Weight', height=300)

st.markdown("---")
st.markdown("*Data stored in `workouts.csv` (seeded from Excel where available).*")
