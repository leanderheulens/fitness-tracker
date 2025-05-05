import streamlit as st
import pandas as pd
import os
import re
from datetime import date

# Filenames
CSV_FILE = 'workouts.csv'
EXCEL_FILE = 'pushpull.xlsx'

# Session state for form visibility
if 'show_form' not in st.session_state:
    st.session_state.show_form = False

# Parse Excel to get session-level entries
def parse_excel_sessions():
    if not os.path.exists(EXCEL_FILE):
        return pd.DataFrame(columns=['Date','Exercise','Entry'])
    df_wide = pd.read_excel(EXCEL_FILE)
    # Rename header column if necessary
    if 'Oefening' in df_wide.columns:
        df_wide = df_wide.rename(columns={'Oefening': 'Exercise'})
    # Melt wide to long
    df_melt = df_wide.melt(id_vars=['Exercise'], var_name='RawDate', value_name='Entry')
    df_melt = df_melt.dropna(subset=['Entry'])
    rows = []
    for _, row in df_melt.iterrows():
        raw_date = str(row['RawDate'])
        # Strip weekday if present: split by first space
        if ' ' in raw_date:
            _, date_part = raw_date.split(' ', 1)
        else:
            date_part = raw_date
        try:
            entry_date = pd.to_datetime(date_part, dayfirst=True, errors='coerce')
        except:
            entry_date = None
        if pd.isna(entry_date):
            continue
        rows.append({'Date': entry_date, 'Exercise': row['Exercise'], 'Entry': str(row['Entry'])})
    return pd.DataFrame(rows)

# Parse Excel to get set-level entries
def parse_excel_sets():
    if not os.path.exists(EXCEL_FILE):
        return pd.DataFrame(columns=['Date','Exercise','Weight','Sets','Reps','Notes'])
    df_wide = pd.read_excel(EXCEL_FILE)
    if 'Oefening' in df_wide.columns:
        df_wide = df_wide.rename(columns={'Oefening': 'Exercise'})
    df_melt = df_wide.melt(id_vars=['Exercise'], var_name='RawDate', value_name='Entry')
    df_melt = df_melt.dropna(subset=['Entry'])
    rows = []
    for _, row in df_melt.iterrows():
        raw_date = str(row['RawDate'])
        if ' ' in raw_date:
            _, date_part = raw_date.split(' ', 1)
        else:
            date_part = raw_date
        try:
            entry_date = pd.to_datetime(date_part, dayfirst=True, errors='coerce')
        except:
            entry_date = None
        if pd.isna(entry_date):
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
                sets_str, reps_str = seg.split('x')
                try:
                    rows.append({
                        'Date': entry_date,
                        'Exercise': row['Exercise'],
                        'Weight': weight,
                        'Sets': int(sets_str),
                        'Reps': int(reps_str),
                        'Notes': ''
                    })
                except:
                    continue
    return pd.DataFrame(rows)

# Load combined data for sets and sessions
def load_data():
    # Excel data
    df_sessions = parse_excel_sessions()
    df_sets_excel = parse_excel_sets()
    # Manual CSV entries
    if os.path.exists(CSV_FILE):
        df_csv = pd.read_csv(CSV_FILE, parse_dates=['Date'], dayfirst=True)
    else:
        df_csv = pd.DataFrame(columns=['Date','Exercise','Weight','Sets','Reps','Notes'])
    # Combine sets data: excel + manual
    df_sets = pd.concat([df_sets_excel, df_csv], ignore_index=True)
    df_sets.drop_duplicates(subset=['Date','Exercise','Weight','Sets','Reps','Notes'], inplace=True)
    df_sets.sort_values('Date', ascending=False, inplace=True)
    # Combine session data: excel sessions + manual sessions
    # For manual sessions, reconstruct entry string
    rows = []
    for _, row in df_csv.iterrows():
        entry_str = f"{int(row['Weight'])}kg ({row['Sets']}x{row['Reps']})"
        rows.append({'Date': row['Date'], 'Exercise': row['Exercise'], 'Entry': entry_str})
    df_sessions_manual = pd.DataFrame(rows)
    df_sessions_combined = pd.concat([df_sessions, df_sessions_manual], ignore_index=True)
    df_sessions_combined.drop_duplicates(subset=['Date','Exercise','Entry'], inplace=True)
    df_sessions_combined.sort_values('Date', ascending=False, inplace=True)
    return df_sets, df_sessions_combined

# Save manual entries to CSV
def save_manual(df_csv):
    df_csv.to_csv(CSV_FILE, index=False)

# Get exercise list from sessions

def get_exercises_list(df_sets, df_sessions):
    ex = set(df_sets['Exercise'].dropna().unique())
    ex.update(df_sessions['Exercise'].dropna().unique())
    return sorted(ex)

# App UI
st.title("🏋️ Fitness Tracker")
# Load data
df_sets, df_sessions = load_data()
ex_list = get_exercises_list(df_sets, df_sessions)

# Show form button
def show_form():
    st.session_state.show_form = True
st.button("Log New Workout", on_click=show_form)

# Workout form
if st.session_state.show_form:
    st.subheader("Log New Workout")
    with st.form("entry_form"):
        entry_date = st.date_input("Date", date.today())
        exercise = st.selectbox("Exercise", ex_list)
        # Show last session-level history
        history = df_sessions[df_sessions['Exercise'] == exercise]
        if not history.empty:
            st.markdown(f"**Previous sessions for {exercise}:**")
            st.table(history[['Date','Entry']].head(5))
        weight = st.number_input("Weight (kg)", min_value=0.0, step=0.5)
        sets = st.number_input("Sets", min_value=1, step=1)
        reps = st.number_input("Reps", min_value=1, step=1)
        notes = st.text_area("Notes")
        if st.form_submit_button("Add Workout"):
            # Append to CSV
            if os.path.exists(CSV_FILE):
                df_csv = pd.read_csv(CSV_FILE, parse_dates=['Date'], dayfirst=True)
            else:
                df_csv = pd.DataFrame(columns=['Date','Exercise','Weight','Sets','Reps','Notes'])
            new_row = pd.DataFrame([{
                'Date': entry_date,
                'Exercise': exercise,
                'Weight': weight,
                'Sets': sets,
                'Reps': reps,
                'Notes': notes
            }])
            df_csv = pd.concat([df_csv, new_row], ignore_index=True)
            save_manual(df_csv)
            st.success("Workout added!")
            st.session_state.show_form = False
            st.experimental_rerun()

# Display recent set entries
st.subheader("Recent Entries (Set-Level)")
st.dataframe(df_sets.head(20))

# Progress chart
st.subheader("Progress Chart")
selected = st.selectbox("Select Exercise to Chart", [''] + ex_list)
if selected:
    df_ex = df_sets[df_sets['Exercise'] == selected]
    # session-level chart using last weight per date
    session_weights = df_ex.groupby('Date')['Weight'].max().reset_index()
    st.line_chart(data=session_weights, x='Date', y='Weight', height=300)

st.markdown("---")
st.markdown("*Data stored in `workouts.csv` (manual entries), seeded from `pushpull.xlsx`.*")
