import streamlit as st
import pandas as pd
import os
import re
from datetime import date

# Filenames
CSV_FILE = 'workouts.csv'
EXCEL_FILE = 'pushpull.xlsx'

# Load existing data or seed from Excel
def load_data():
    # 1) If CSV exists, load from it
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE, parse_dates=['Date'], dayfirst=True)
        return df
    # 2) Else if Excel exists, parse wide-format sheet
    if os.path.exists(EXCEL_FILE):
        df_wide = pd.read_excel(EXCEL_FILE)
        # Ensure Exercise column is named consistently
        if 'Oefening' in df_wide.columns:
            df_wide = df_wide.rename(columns={'Oefening': 'Exercise'})
        # Melt dates into rows
        df_melt = df_wide.melt(id_vars=['Exercise'], var_name='Date', value_name='Entry')
        df_melt = df_melt.dropna(subset=['Entry'])
        rows = []
        for _, row in df_melt.iterrows():
            exercise = row['Exercise']
            # Parse the column header into a date
            try:
                entry_date = pd.to_datetime(row['Date'], dayfirst=True)
            except Exception:
                continue
            entry = str(row['Entry'])
            # Split multiple weight segments by '+'
            for part in entry.split('+'):
                part = part.strip()
                # Expecting format like '20kg (1x7 + 1x6)'
                m = re.match(r"(\d+)\s*kg\s*\(([^)]+)\)", part)
                if not m:
                    continue
                weight = int(m.group(1))
                reps_info = m.group(2)
                # reps_info might contain multiple sets separated by '+'
                for seg in reps_info.split('+'):
                    seg = seg.strip()
                    if 'x' not in seg:
                        continue
                    sets_str, reps_str = seg.split('x')
                    try:
                        sets = int(sets_str)
                        reps = int(reps_str)
                    except ValueError:
                        continue
                    rows.append({
                        'Date': entry_date,
                        'Exercise': exercise,
                        'Weight': weight,
                        'Sets': sets,
                        'Reps': reps,
                        'Notes': ''
                    })
        df = pd.DataFrame(rows)
        # Save to CSV for future loads
        if not df.empty:
            df.to_csv(CSV_FILE, index=False)
        return df
    # 3) No data
    return pd.DataFrame(columns=['Date','Exercise','Weight','Sets','Reps','Notes'])

# Save DataFrame to CSV
def save_data(df):
    df.to_csv(CSV_FILE, index=False)

# App setup
st.title("🏋️ Fitness Tracker")

# Load or seed data
df_all = load_data()
# Sort by date descending
df_all = df_all.sort_values('Date', ascending=False)

# Main: Log new workout via modal
if st.button("Log New Workout"):
    with st.modal("Log New Workout"):
        entry_date = st.date_input("Date", date.today())
        # Build exercise selection list
        existing = sorted(df_all['Exercise'].dropna().unique())
        existing.append("Other")
        choice = st.selectbox("Exercise", existing)
        if choice == "Other":
            exercise = st.text_input("New Exercise Name")
        else:
            exercise = choice
            # Show recent history for this exercise
            history = df_all[df_all['Exercise'] == exercise]
            if not history.empty:
                st.markdown(f"**Previous entries for {exercise}:**")
                st.table(history[['Date','Weight','Sets','Reps','Notes']].head(5))
        weight = st.number_input("Weight (kg)", min_value=0.0, step=0.5)
        sets = st.number_input("Sets", min_value=1, step=1)
        reps = st.number_input("Reps", min_value=1, step=1)
        notes = st.text_area("Notes")
        if st.button("Add Workout"):
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
                combined = pd.concat([load_data(), new_row], ignore_index=True)
                save_data(combined)
                st.success("Workout added!")
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
    # Show weight per session
    chart_df = df_ex[['Date','Weight']].drop_duplicates(subset=['Date'], keep='last')
    st.line_chart(data=chart_df, x='Date', y='Weight', height=300)

st.markdown("---")
st.markdown("*Data stored in `workouts.csv` (seeded from Excel where available).*")
