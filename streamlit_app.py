import streamlit as st
import pandas as pd
import os
import re
from datetime import date

# Filenames
CSV_FILE = 'workouts.csv'
EXCEL_FILE = 'pushpull.xlsx'

# Session state to show form
if 'show_form' not in st.session_state:
    st.session_state.show_form = False

# Parse Excel historical data (always)
def parse_excel():
    if not os.path.exists(EXCEL_FILE):
        return pd.DataFrame(columns=['Date','Exercise','Weight','Sets','Reps','Notes'])
    df_wide = pd.read_excel(EXCEL_FILE)
    if 'Oefening' in df_wide.columns:
        df_wide.rename(columns={'Oefening':'Exercise'}, inplace=True)
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
    df_excel = pd.DataFrame(rows)
    return df_excel

# Load combined data: Excel + manual CSV entries
def load_data():
    # Historical from Excel
    df_excel = parse_excel()
    # Manual entries
    if os.path.exists(CSV_FILE):
        df_csv = pd.read_csv(CSV_FILE, parse_dates=['Date'], dayfirst=True)
    else:
        df_csv = pd.DataFrame(columns=['Date','Exercise','Weight','Sets','Reps','Notes'])
    # Combine and drop exact duplicates
    df = pd.concat([df_excel, df_csv], ignore_index=True)
    df.drop_duplicates(subset=['Date','Exercise','Weight','Sets','Reps','Notes'], inplace=True)
    df.sort_values('Date', ascending=False, inplace=True)
    return df

# Save manual entries to CSV
def save_manual(df_all):
    # Only manual ones: exclude those in Excel? But append anyway
    df_all.to_csv(CSV_FILE, index=False)

# Get full exercise list from Excel + CSV
def get_exercises_list(df_all):
    ex = df_all['Exercise'].dropna().unique().tolist()
    return sorted(ex)

# App UI
st.title("🏋️ Fitness Tracker")
# Load data
df_all = load_data()
ex_list = get_exercises_list(df_all)

# Show form button
def show_form():
    st.session_state.show_form = True
st.button("Log New Workout", on_click=show_form)

# Workout form
def workout_form():
    st.subheader("Log New Workout")
    with st.form("entry_form"):
        entry_date = st.date_input("Date", date.today())
        exercise = st.selectbox("Exercise", ex_list)
        history = df_all[df_all['Exercise']==exercise]
        if not history.empty:
            st.markdown(f"**Previous entries for {exercise}:**")
            st.table(history[['Date','Weight','Sets','Reps','Notes']].head(5))
        weight = st.number_input("Weight (kg)", min_value=0.0, step=0.5)
        sets = st.number_input("Sets", min_value=1, step=1)
        reps = st.number_input("Reps", min_value=1, step=1)
        notes = st.text_area("Notes")
        if st.form_submit_button("Add Workout"):
            # Append manual entry
            df_new = pd.DataFrame([{'Date': entry_date,
                                     'Exercise': exercise,
                                     'Weight': weight,
                                     'Sets': sets,
                                     'Reps': reps,
                                     'Notes': notes}])
            # Save combined manual entries only
            if os.path.exists(CSV_FILE):
                df_csv = pd.read_csv(CSV_FILE, parse_dates=['Date'], dayfirst=True)
            else:
                df_csv = pd.DataFrame(columns=df_new.columns)
            df_csv = pd.concat([df_csv, df_new], ignore_index=True)
            save_manual(df_csv)
            st.success("Workout added!")
            st.session_state.show_form = False
            st.experimental_rerun()

if st.session_state.show_form:
    workout_form()

# Recent entries
st.subheader("Recent Entries")
st.dataframe(df_all.head(20))

# Progress chart
st.subheader("Progress Chart")
selected = st.selectbox("Select Exercise to Chart", [''] + ex_list)
if selected:
    df_ex = df_all[df_all['Exercise']==selected]
    chart_df = df_ex[['Date','Weight']].drop_duplicates(subset=['Date'], keep='last')
    st.line_chart(data=chart_df, x='Date', y='Weight', height=300)

st.markdown("---")
st.markdown("*Data stored in `workouts.csv` (manual entries), seeded from `pushpull.xlsx`.*")
