import os
import pandas as pd

def load_data():
    # load all the CSV files we need
    base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "CSV")
    
    files = {
        "courses": "Courses.csv",
        "instructors": "Instructors.csv", 
        "rooms": "Rooms.csv",
        "timeslots": "TimeSlots.csv",
        "sections": "Sections.csv"
    }
    
    data = {}
    
    for key, filename in files.items():
        filepath = os.path.join(base_path, filename)
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"❌ Can't find: {filepath}")
        
        data[key] = pd.read_csv(filepath)
        print(f"✅ Loaded {filename}: {len(data[key])} rows")
    
    return data


def define_groups(sections_df):
    # group sections together - they share lectures but have separate labs
    groups = {}
    
    # level 1 has 12 sections, split into 4 groups of 3
    for i in range(4):
        group_name = f"L1_G{i+1}"
        sections = [f"S{j+1}_L1" for j in range(i*3, (i+1)*3)]
        groups[group_name] = sections
    
    # level 2 has 9 sections, 3 groups of 3
    for i in range(3):
        group_name = f"L2_G{i+1}"
        sections = [f"S{j+1}_L2" for j in range(i*3, (i+1)*3)]
        groups[group_name] = sections
    
    # level 3 is track-based
    groups["L3_AID"] = ["S1_AID_L3", "S2_AID_L3", "S3_AID_L3", "S4_AID_L3"]
    groups["L3_CNC"] = ["S1_CNC_L3", "S2_CNC_L3", "S3_CNC_L3", "S4_CNC_L3"]
    groups["L3_CSC"] = ["S1_CSC_L3"]
    groups["L3_BIF"] = ["S1_BIF_L3"]
    
    # level 4 tracks
    groups["L4_AID"] = ["S1_AID_L4", "S2_AID_L4", "S3_AID_L4", "S4_AID_L4"]
    groups["L4_CNC"] = ["S1_CNC_L4", "S2_CNC_L4", "S3_CNC_L4", "S4_CNC_L4"]
    groups["L4_CSC"] = ["S1_CSC_L4"]
    groups["L4_BIF"] = ["S1_BIF_L4"]
    
    return groups


def build_sessions(data):
    # create all the sessions we need to schedule
    sessions = []
    
    courses_df = data["courses"]
    sections_df = data["sections"]
    groups = define_groups(sections_df)
    
    # make a reverse lookup: section -> group
    section_to_group = {}
    for group_name, section_list in groups.items():
        for sec_id in section_list:
            section_to_group[sec_id] = group_name
    
    # keep track of lectures we already added per group
    lectures_done = set()
    
    for _, section_row in sections_df.iterrows():
        section_id = section_row["SectionID"]
        course_ids = [c.strip().upper() for c in str(section_row["Courses"]).split(",")]
        group_name = section_to_group.get(section_id)
        
        if not group_name:
            print(f"⚠️ Warning: Section {section_id} has no group")
            continue
        
        for course_id in course_ids:
            # find course details
            course_info = courses_df[courses_df["CourseID"].str.upper() == course_id]
            
            if course_info.empty:
                print(f"⚠️ Warning: Course {course_id} not found")
                continue
            
            course_type = str(course_info.iloc[0]["Type"])
            
            # check what type of sessions this course needs
            has_lecture = "lecture" in course_type.lower()
            has_lab = "lab" in course_type.lower()
            
            # add lecture (only once per group)
            if has_lecture:
                lec_key = (group_name, course_id, "Lecture")
                if lec_key not in lectures_done:
                    sessions.append({
                        "group": group_name,
                        "sections": groups[group_name],
                        "course_id": course_id,
                        "session_type": "Lecture",
                        "variable_name": f"{group_name}_{course_id}_LEC"
                    })
                    lectures_done.add(lec_key)
            
            # add lab (one per section)
            if has_lab:
                sessions.append({
                    "group": group_name,
                    "sections": [section_id],
                    "course_id": course_id,
                    "session_type": "Lab",
                    "variable_name": f"{section_id}_{course_id}_LAB"
                })
    
    print(f"✅ Built {len(sessions)} sessions")
    return sessions