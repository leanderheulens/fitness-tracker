import streamlit as st
import pandas as pd
import os
import re
from datetime import date

# Filenames
CSV_FILE = 'workouts.csv'
EXCEL_FILE = 'pushpull.xlsx'

# Session state for form visibility
def init_state():
    if 'show_form' not in st.session_state:
        st.session_state.show_form = False
init_state()

# Utility: ordinal suffix for day

def ordinal(n):
    if 11 <= (n % 100) <= 13:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"

# Parse Excel sessions

def parse_excel_sessions():
    if not os.path.exists(EXCEL_FILE):
        return pd.DataFrame(columns=['Date','Exercise','Entry'])
    df_wide = pd.read_excel(EXCEL_FILE)
    if 'Oefening' in df_wide.columns:
        df_wide.rename(columns={'Oefening':'Exercise'}, inplace=True)
    df_melt = df_wide.melt(id_vars=['Exercise'], var_name='RawDate', value_name='Entry')
    df_melt.dropna(subset=['Entry'], inplace=True)
    rows = []
    for _, row in df_melt.iterrows():
        raw_date = str(row['RawDate']).split(' ',1)[-1]
        try:
            entry_date = pd.to_datetime(raw_date, dayfirst=True, errors='coerce')
        except:
            continue
        if pd.isna(entry_date):
            continue
        rows.append({'Date': entry_date, 'Exercise': row['Exercise'], 'Entry': str(row['Entry'])})
    df_sessions = pd.DataFrame(rows)
    df_sessions.sort_values('Date', ascending=False, inplace=True)
    return df_sessions

# Parse Excel set-level data for charting

def parse_excel_sets():
    if not os.path.exists(EXCEL_FILE):
        return pd.DataFrame(columns=['Date','Exercise','Weight','Sets','Reps','Notes'])
    df_wide = pd.read_excel(EXCEL_FILE)
    if 'Oefening' in df_wide.columns:
        df_wide.rename(columns={'Oefening':'Exercise'}, inplace=True)
    df_melt = df_wide.melt(id_vars=['Exercise'], var_name='RawDate', value_name='Entry')
    df_melt.dropna(subset=['Entry'], inplace=True)
    rows = []
    for _, row in df_melt.iterrows():
        raw_date = str(row['RawDate']).split(' ',1)[-1]
        try:
            entry_date = pd.to_datetime(raw_date, dayfirst=True, errors='coerce')
        except:
            continue
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
                    rows.append({'Date': entry_date,
                                 'Exercise': row['Exercise'],
                                 'Weight': weight,
                                 'Sets': int(sets_str.strip()),
                                 'Reps': int(reps_str.strip()),
                                 'Notes': ''})
                except:
                    continue
    df_sets = pd.DataFrame(rows)
    df_sets.sort_values('Date', ascending=False, inplace=True)
    return df_sets

# Load combined data
def load_data():
    df_sessions_excel = parse_excel_sessions()
    df_sets_excel = parse_excel_sets()
    # Manual CSV entries
    if os.path.exists(CSV_FILE):
        df_sets_csv = pd.read_csv(CSV_FILE, parse_dates=['Date'], dayfirst=True)
    else:
        df_sets_csv = pd.DataFrame(columns=['Date','Exercise','Weight','Sets','Reps','Notes'])
    # Combine for charting
    df_sets = pd.concat([df_sets_excel, df_sets_csv], ignore_index=True)
    df_sets.drop_duplicates(subset=['Date','Exercise','Weight','Sets','Reps','Notes'], inplace=True)
    df_sets.sort_values('Date', ascending=False, inplace=True)
    # Combine sessions (Excel + manual)
    rows = []
    for _, row in df_sets_csv.iterrows():
        entry_str = f"{int(row['Weight'])}kg ({row['Sets']}x{row['Reps']})"
        rows.append({'Date': row['Date'], 'Exercise': row['Exercise'], 'Entry': entry_str})
    df_sessions_csv = pd.DataFrame(rows)
    df_sessions = pd.concat([df_sessions_excel, df_sessions_csv], ignore_index=True)
    df_sessions.drop_duplicates(subset=['Date','Exercise','Entry'], inplace=True)
    df_sessions.sort_values('Date', ascending=False, inplace=True)
    return df_sets, df_sessions

# Save manual entries
def save_manual(df_csv):
    df_csv.to_csv(CSV_FILE, index=False)

# Build exercise list
def get_ex_list(df_sets, df_sessions):
    ex = set(df_sets['Exercise'].dropna()) | set(df_sessions['Exercise'].dropna())
    return sorted(ex)

# Main UI
st.title("🏋️ Fitness Tracker")

# Load data
df_sets, df_sessions = load_data()
ex_list = get_ex_list(df_sets, df_sessions)

# Show form button
if st.button("Log New Workout"):
    st.session_state.show_form = True

# Workout form when visible
if st.session_state.show_form:
    st.subheader("Log New Workout")
    # Exercise dropdown (reactive)
    selected_ex = st.selectbox("Exercise", ex_list)
    # Show last 5 sessions with formatted dates
    history = df_sessions[df_sessions['Exercise'] == selected_ex].head(5)
    if not history.empty:
        display = history.copy()
        display['Date'] = display['Date'].dt.day.apply(lambda d: f"{ordinal(d)} of {display['Date'].dt.strftime('%B %Y')}" )
        st.markdown(f"**Previous sessions for {selected_ex}:**")
        st.table(display[['Date','Entry']])
    # Entry form
    with st.form("entry_form"):
        entry_date = st.date_input("Date", date.today())
        weight = st.number_input("Weight (kg)", min_value=0.0, step=0.5)
        sets = st.number_input("Sets", min_value=1, step=1)
        reps = st.number_input("Reps", min_value=1, step=1)
        notes = st.text_area("Notes")
        if st.form_submit_button("Add Workout"):
            if os.path.exists(CSV_FILE):
                df_csv = pd.read_csv(CSV_FILE, parse_dates=['Date'], dayfirst=True)
            else:
                df_csv = pd.DataFrame(columns=['Date','Exercise','Weight','Sets','Reps','Notes'])
            new = pd.DataFrame([{'Date': entry_date,
                                 'Exercise': selected_ex,
                                 'Weight': weight,
                                 'Sets': sets,
                                 'Reps': reps,
                                 'Notes': notes}])
            df_csv = pd.concat([df_csv, new], ignore_index=True)
            save_manual(df_csv)
            st.success("Workout added!")
            st.session_state.show_form = False
            st.experimental_rerun()

# Recent entries
st.subheader("Recent Entries (Set-Level)")
st.dataframe(df_sets.head(20))

# Progress chart
st.subheader("Progress Chart")
chart_ex = st.selectbox("Select Exercise to Chart", [''] + ex_list)
if chart_ex:
    df_ex = df_sets[df_sets['Exercise'] == chart_ex]
    session_weights = df_ex.groupby('Date')['Weight'].max().reset_index()
    st.line_chart(data=session_weights, x='Date', y='Weight', height=300)

st.markdown("---")
st.markdown("*Data stored in `workouts.csv` (manual entries), seeded from `pushpull.xlsx`.*")
