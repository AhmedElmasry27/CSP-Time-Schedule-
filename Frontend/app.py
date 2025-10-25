import streamlit as st
import pandas as pd
import os
import re
import sys
from html import escape
from datetime import datetime
import io

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
sys.path.insert(0, PROJECT_ROOT)

from Backend.data_loader import build_sessions
from Backend.solver import solve_csp

st.set_page_config(
    page_title="CSIT Timetable System",
    layout="wide",
    initial_sidebar_state="expanded"
)

OUTPUT_DIR = os.path.join(PROJECT_ROOT, "Output")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "generated_timetable.csv")

st.markdown("""
<style>
.main-header {
    font-size: 2.5rem;
    font-weight: 700;
    color: #1f2937;
    margin-bottom: 0.5rem;
}

.stat-card {
    background: #4f46e5;
    padding: 1.2rem;
    border-radius: 8px;
    color: white;
    text-align: center;
}

.stat-number {
    font-size: 2rem;
    font-weight: bold;
}

.stat-label {
    font-size: 0.9rem;
    opacity: 0.9;
    margin-top: 0.3rem;
}

.timetable-container { 
    max-width: 100%; 
    overflow-x: auto; 
    margin-bottom: 20px;
    border-radius: 8px;
}

.time-table { 
    width: 100%; 
    border-collapse: collapse; 
    table-layout: fixed; 
    min-width: 1500px;
    background: white;
}

.time-table th, .time-table td { 
    border: 1px solid #e5e7eb; 
    padding: 0; 
    height: 55px; 
    vertical-align: top; 
    font-size: 10px; 
}

.time-table th { 
    color: white; 
    padding: 5px; 
    font-weight: 600; 
    text-align: center; 
}

.group-header th { 
    background: #4f46e5;
    height: 35px; 
    font-size: 13px;
}

.section-header th { 
    background: #6366f1;
    height: 45px; 
    font-size: 11px; 
    padding: 8px 4px;
}

.day-label-col { 
    width: 80px; 
    background: #ec4899;
    color: white;
    font-weight: 600; 
    vertical-align: middle !important;
    text-align: center;
    font-size: 12px;
}

.time-label-col { 
    width: 80px; 
    background: #f9fafb;
    color: #374151; 
    font-weight: 500; 
    vertical-align: middle !important;
    text-align: center;
    font-size: 9px;
}

.section-col-cell { 
    min-width: 130px; 
    max-width: 160px; 
} 

.day-separator td { 
    background: #06b6d4;
    color: white;
    font-weight: 600; 
    text-align: center;
    padding: 6px;
    height: 30px; 
    font-size: 12px;
}

.course-card {
    height: 100%;
    width: 100%;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    padding: 4px;
    overflow: hidden;
    text-align: center;
    line-height: 1.3;
    cursor: pointer;
    border-radius: 3px;
}

.course-card:hover {
    transform: scale(1.03);
    box-shadow: 0 2px 6px rgba(0,0,0,0.15);
}

.course-code { 
    font-weight: 700; 
    font-size: 11px; 
    color: #111827;
    margin-bottom: 2px;
}

.course-info { 
    font-size: 9px; 
    color: #4b5563;
    margin-top: 1px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 100%;
}

.empty-cell { 
    background: #fafafa;
}

.stButton>button {
    background: #4f46e5;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 0.6rem 1.5rem;
    font-weight: 500;
    width: 100%;
}

.stButton>button:hover {
    background: #4338ca;
}

.upload-section {
    background: #f9fafb;
    padding: 1.5rem;
    border-radius: 8px;
    border: 2px dashed #d1d5db;
    margin-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)

COLOR_MAP = {
    "Lab": "#90EE90",
    "Lecture": "#FFD580",
    "Seminar": "#FF8C94",
    "Project": "#87CEFA"
}

YEAR_LABELS = {
    "L1": "Year 1",
    "L2": "Year 2",
    "L3": "Year 3",
    "L4": "Year 4"
}

def extract_year(section_id):
    if "_L1" in section_id: return "L1"
    elif "_L2" in section_id: return "L2"
    elif "_L3" in section_id: return "L3"
    elif "_L4" in section_id: return "L4"
    return "Unknown"

def extract_track(section_id):
    if "AID" in section_id: return "AID"
    elif "CNC" in section_id: return "CNC"
    elif "CSC" in section_id: return "CSC"
    elif "BIF" in section_id: return "BIF"
    return "General"

def infer_group_from_section(section_id, year_token):
    if not isinstance(section_id, str) or not year_token:
        return "Unknown Group"
    
    sid = section_id.upper()
    
    try:
        match = re.search(r'S(\d+)', sid)
        sec_num = int(match.group(1)) if match else 0
        
        if year_token == "L1":
            if 1 <= sec_num <= 3: return "Group 1"
            if 4 <= sec_num <= 6: return "Group 2"
            if 7 <= sec_num <= 9: return "Group 3"
            if 10 <= sec_num <= 12: return "Group 4"
            
        elif year_token == "L2":
            if 1 <= sec_num <= 3: return "Group 1"
            if 4 <= sec_num <= 6: return "Group 2"
            if 7 <= sec_num <= 9: return "Group 3"
            
        elif year_token in ["L3", "L4"]:
            if "CNC" in sid: return "CNC"
            if "AID" in sid: return "AID"
            if "CSC" in sid: return "CSC"
            if "BIF" in sid: return "BIF"
    except:
        pass
    
    return "Unknown Group"

def parse_time_label(time_label):
    try:
        start_time = time_label.split(" - ")[0]
        return datetime.strptime(start_time, "%I:%M %p")
    except:
        return datetime.min

def generate_timetable_from_files(courses_file, instructors_file, rooms_file, sections_file, timeslots_file):
    try:
        with st.spinner("Loading data..."):
            data = {
                "courses": pd.read_csv(courses_file),
                "instructors": pd.read_csv(instructors_file),
                "rooms": pd.read_csv(rooms_file),
                "sections": pd.read_csv(sections_file),
                "timeslots": pd.read_csv(timeslots_file)
            }
        
        with st.spinner("Building sessions..."):
            sessions = build_sessions(data)
        
        with st.spinner("Running solver..."):
            timetable_df = solve_csp(sessions, data)
        
        if timetable_df.empty:
            return None, "Failed to generate timetable", None
        
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        timetable_df.to_csv(OUTPUT_FILE, index=False)
        
        return timetable_df, "Success", data
    
    except Exception as e:
        return None, str(e), None

st.markdown('<div class="main-header">CSIT Timetable System</div>', unsafe_allow_html=True)
st.caption("Automated scheduling using constraint satisfaction")

st.markdown("---")

# Upload section
with st.expander("📤 Upload CSV Files", expanded=True):
    st.markdown('<div class="upload-section">', unsafe_allow_html=True)
    st.write("Upload all required CSV files to generate a timetable")
    
    col1, col2 = st.columns(2)
    
    with col1:
        courses_file = st.file_uploader("Courses.csv", type=['csv'], key="courses")
        instructors_file = st.file_uploader("Instructors.csv", type=['csv'], key="instructors")
        rooms_file = st.file_uploader("Rooms.csv", type=['csv'], key="rooms")
    
    with col2:
        sections_file = st.file_uploader("Sections.csv", type=['csv'], key="sections")
        timeslots_file = st.file_uploader("TimeSlots.csv", type=['csv'], key="timeslots")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    all_files_uploaded = all([courses_file, instructors_file, rooms_file, sections_file, timeslots_file])
    
    if all_files_uploaded:
        if st.button("Generate Timetable from Uploaded Files"):
            timetable_df, status, data = generate_timetable_from_files(
                courses_file, instructors_file, rooms_file, sections_file, timeslots_file
            )
            
            if timetable_df is not None:
                st.success(f"Generated {len(timetable_df)} sessions successfully")
                st.session_state['generated_df'] = timetable_df
                st.session_state['data'] = data
                st.rerun()
            else:
                st.error(f"Generation failed: {status}")
    else:
        st.info("Please upload all 5 CSV files to generate a timetable")

st.markdown("---")

# Check if we have generated data or existing file
df = None
courses_df = None
instructors_df = None
timeslots_df = None
rooms_df = None

if 'generated_df' in st.session_state and 'data' in st.session_state:
    df = st.session_state['generated_df']
    courses_df = st.session_state['data']['courses']
    instructors_df = st.session_state['data']['instructors']
    timeslots_df = st.session_state['data']['timeslots']
    rooms_df = st.session_state['data']['rooms']
elif os.path.exists(OUTPUT_FILE):
    try:
        df = pd.read_csv(OUTPUT_FILE)
        
        # Try to load from CSV folder as fallback
        csv_folder = os.path.join(PROJECT_ROOT, "CSV")
        courses_df = pd.read_csv(os.path.join(csv_folder, "Courses.csv"))
        instructors_df = pd.read_csv(os.path.join(csv_folder, "Instructors.csv"))
        timeslots_df = pd.read_csv(os.path.join(csv_folder, "TimeSlots.csv"))
        rooms_df = pd.read_csv(os.path.join(csv_folder, "Rooms.csv"))
    except Exception as e:
        st.warning(f"Could not load existing timetable: {e}")

if df is None:
    st.info("No timetable generated yet. Upload CSV files above to get started.")
    st.stop()

df['YearToken'] = df['SectionID'].apply(extract_year)
df['YearLabel'] = df['YearToken'].map(YEAR_LABELS)
df['Track'] = df['SectionID'].apply(extract_track)
df['GroupLabel'] = df.apply(lambda r: infer_group_from_section(r['SectionID'], r['YearToken']), axis=1)

timeslot_map = timeslots_df.set_index('TimeSlotID').to_dict('index')
def get_time_label(ts_id):
    ts = timeslot_map.get(ts_id)
    if ts:
        return f"{ts['StartTime']} - {ts['EndTime']}"
    return ""

df['TimeLabel'] = df['TimeSlot'].apply(get_time_label)

courses_dict = courses_df.set_index('CourseID')['CourseName'].to_dict()
def get_course_name(course_id):
    return courses_dict.get(course_id, course_id)

df['CourseName'] = df['CourseID'].apply(get_course_name)

days_ordered = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"]
unique_days = [d for d in days_ordered if d in df['Day'].unique()]
timeslot_order = sorted(df['TimeLabel'].unique(), key=parse_time_label)

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-number">{len(df)}</div>
        <div class="stat-label">Sessions</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-number">{df['SectionID'].nunique()}</div>
        <div class="stat-label">Sections</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-number">{df['CourseID'].nunique()}</div>
        <div class="stat-label">Courses</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-number">{df['Instructor'].nunique()}</div>
        <div class="stat-label">Instructors</div>
    </div>
    """, unsafe_allow_html=True)

with col5:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-number">{df['Room'].nunique()}</div>
        <div class="stat-label">Rooms</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

col_filter1, col_filter2 = st.columns(2)

with col_filter1:
    year_options = ["All Years"] + list(YEAR_LABELS.values())
    selected_year = st.selectbox("Select Year:", year_options, index=0)

with col_filter2:
    if selected_year != "All Years":
        year_token = [k for k, v in YEAR_LABELS.items() if v == selected_year][0]
        if year_token in ["L3", "L4"]:
            track_options = ["All Tracks", "AID", "CNC", "CSC", "BIF"]
            selected_track = st.selectbox("Select Track:", track_options)
        else:
            selected_track = "All Tracks"
    else:
        selected_track = "All Tracks"

filtered_df = df.copy()

if selected_year != "All Years":
    filtered_df = filtered_df[filtered_df['YearLabel'] == selected_year]

if selected_track != "All Tracks":
    filtered_df = filtered_df[filtered_df['Track'] == selected_track]

st.markdown("---")

def build_year_schedule(df_year):
    if df_year.empty:
        return "<p>No classes scheduled.</p>"
    
    df_sections = df_year[['SectionID', 'GroupLabel']].drop_duplicates()
    
    # Custom sort order for L3 and L4: CNC, AID, CSC, BIF
    track_order = {'CNC': 0, 'AID': 1, 'CSC': 2, 'BIF': 3}
    
    def sort_key(row):
        group = row['GroupLabel']
        if group in ['CNC', 'AID', 'CSC', 'BIF']:
            return (track_order.get(group, 99), row['SectionID'])
        else:
            return (group, row['SectionID'])
    
    df_sections['sort_key'] = df_sections.apply(sort_key, axis=1)
    df_sections = df_sections.sort_values(by='sort_key')
    df_sections = df_sections.drop('sort_key', axis=1)
    
    all_sections = df_sections['SectionID'].tolist()
    groups_map = df_sections.groupby('GroupLabel', sort=False)['SectionID'].apply(list).to_dict()
    section_to_group = df_sections.set_index('SectionID')['GroupLabel'].to_dict()
    
    schedule_grouped = df_year.groupby(["Day", "TimeLabel", "SectionID"])[
        ["CourseID", "CourseName", "SessionType", "Instructor", "Room"]
    ].first().to_dict(orient='index')
    
    final_schedule = schedule_grouped.copy()
    
    for (day, tl, section_id), course_data in schedule_grouped.items():
        if course_data.get("SessionType", "") == "Lecture" and section_id in section_to_group:
            group_label = section_to_group[section_id]
            sibling_sections = groups_map.get(group_label, [])
            
            for sibling in sibling_sections:
                sibling_key = (day, tl, sibling)
                if sibling_key not in final_schedule:
                    final_schedule[sibling_key] = course_data
    
    html = ['<div class="timetable-container">', '<table class="time-table">']
    
    html.append('<thead><tr class="group-header">')
    html.append('<th colspan="2" rowspan="2"></th>')
    for group, sections in groups_map.items():
        html.append(f'<th colspan="{len(sections)}">{escape(group)}</th>')
    html.append('</tr>')
    
    html.append('<tr class="section-header">')
    for section_id in all_sections:
        html.append(f'<th class="section-col-cell">{escape(section_id)}</th>')
    html.append('</tr></thead>')
    
    html.append('<tbody>')
    
    for day in unique_days:
        html.append(f'<tr class="day-separator"><td colspan="{len(all_sections) + 2}">{escape(day)}</td></tr>')
        
        for idx, tl in enumerate(timeslot_order):
            time_parts = tl.split(" - ")
            time_start = time_parts[0] if len(time_parts) > 0 else tl
            time_end = time_parts[1] if len(time_parts) > 1 else ""
            
            time_start_clean = time_start.replace(" AM", "").replace(" PM", "")
            time_end_clean = time_end.replace(" AM", "").replace(" PM", "")
            
            period = "AM" if "AM" in time_start else "PM"
            
            html.append('<tr>')
            
            if idx == 0:
                html.append(f'<td class="day-label-col" rowspan="{len(timeslot_order)}">{escape(day[:3])}</td>')
            
            html.append(f'<td class="time-label-col">{escape(time_start_clean)}<br>{escape(time_end_clean)}<br><span style="font-size:8px">{period}</span></td>')
            
            for section_id in all_sections:
                course_data = final_schedule.get((day, tl, section_id))
                
                if course_data:
                    session_type = course_data.get('SessionType', '')
                    color = COLOR_MAP.get(session_type, "#FFD580")
                    course_name = course_data.get('CourseName', course_data['CourseID'])
                    instructor_name = course_data['Instructor']
                    
                    display_name = course_name if len(course_name) <= 30 else course_name[:27] + "..."
                    
                    card_html = (
                        f"<div class='course-card' style='background-color:{color}'>"
                        f"<span class='course-code'>{escape(course_data['CourseID'])}</span>"
                        f"<span class='course-info' style='font-size: 8px;'>{escape(display_name)}</span>"
                        f"<span class='course-info'>{escape(session_type)}</span>"
                        f"<span class='course-info'>{escape(instructor_name)}</span>"
                        f"<span class='course-info'>{escape(course_data['Room'])}</span>"
                        f"</div>"
                    )
                    html.append(f'<td class="section-col-cell">{card_html}</td>')
                else:
                    html.append('<td class="empty-cell section-col-cell"></td>')
            
            html.append('</tr>')
    
    html.append('</tbody></table></div>')
    return "\n".join(html)

if selected_year == "All Years":
    for token, label in YEAR_LABELS.items():
        st.markdown(f"### {label}")
        df_year = filtered_df[filtered_df['YearToken'] == token]
        
        if df_year.empty:
            st.info(f"No classes for {label}")
        else:
            html_schedule = build_year_schedule(df_year)
            st.markdown(html_schedule, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
else:
    st.markdown(f"### {selected_year}")
    html_schedule = build_year_schedule(filtered_df)
    st.markdown(html_schedule, unsafe_allow_html=True)

st.markdown("---")
csv_data = filtered_df.to_csv(index=False).encode('utf-8')
st.download_button(
    label="Download CSV",
    data=csv_data,
    file_name=f"timetable_{selected_year.replace(' ', '_')}.csv",
    mime="text/csv"
)