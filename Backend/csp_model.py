import pandas as pd
import random
from collections import defaultdict

def solve_csp(sessions, data):
    # greedy solver - try to spread classes across all 5 days to avoid conflicts
    
    print("🚀 Starting greedy solver (using full week)...")
    
    instructors_df = data["instructors"]
    rooms_df = data["rooms"]
    times_df = data["timeslots"]
    
    # parse instructor info
    instructor_courses = {}
    instructor_roles = {}
    instructor_prefs = {}
    
    for _, row in instructors_df.iterrows():
        name = row["Name"]
        role = str(row.get("Role", "Professor"))
        
        # get their qualified courses
        qualified = [x.strip().upper() for x in str(row["QualifiedCourses"]).split(",") if x.strip()]
        instructor_courses[name] = qualified
        instructor_roles[name] = role
        
        # check if they don't want to teach on certain days
        pref = str(row["PreferredSlots"]).lower()
        if "not on" in pref:
            day = pref.split("not on")[-1].strip()
            instructor_prefs[name] = day
        else:
            instructor_prefs[name] = None
    
    # map timeslots to days
    timeslot_to_day = {}
    day_to_timeslots = defaultdict(list)
    
    for _, ts_row in times_df.iterrows():
        ts_id = ts_row["TimeSlotID"]
        day = ts_row["Day"]
        timeslot_to_day[ts_id] = day
        day_to_timeslots[day].append(ts_id)
    
    days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"]
    print(f"📅 Working with: {', '.join(days)}")
    
    # get room lists
    lecture_rooms = rooms_df[rooms_df["Type"].str.contains("Lecture", case=False)]["RoomID"].tolist()
    lab_rooms = rooms_df[rooms_df["Type"].str.contains("Lab", case=False)]["RoomID"].tolist()
    
    print(f"🏫 Got {len(lecture_rooms)} lecture rooms and {len(lab_rooms)} lab rooms")
    
    # track what's scheduled where/when
    instructor_schedule = defaultdict(set)
    room_schedule = defaultdict(set)
    section_schedule = defaultdict(set)
    group_days_used = defaultdict(set)  # which days each group is using
    
    solution = {}
    
    # sort sessions - do lectures first since they're harder
    sessions_sorted = sorted(sessions, key=lambda s: (0 if s['session_type'] == 'Lecture' else 1, -len(s['sections'])))
    
    total = len(sessions_sorted)
    assigned = 0
    failed = []
    
    print(f"📊 Trying to assign {total} sessions...\n")
    
    for idx, session in enumerate(sessions_sorted):
        if (idx + 1) % 20 == 0:
            print(f"   Progress: {idx + 1}/{total} sessions...")
        
        var_name = session["variable_name"]
        course_id = session["course_id"]
        session_type = session["session_type"]
        sections = session["sections"]
        group_name = session.get("group", "Unknown")
        
        # get all possible timeslots
        all_timeslots = times_df["TimeSlotID"].tolist()
        
        # figure out which rooms we can use
        valid_rooms = lab_rooms if session_type == "Lab" else lecture_rooms
        
        # find instructors who can teach this
        valid_instructors = []
        for name, courses in instructor_courses.items():
            if course_id in courses:
                role = instructor_roles.get(name, "Professor")
                
                if session_type == "Lecture":
                    # lectures need actual professors
                    if "Professor" in role and "Assistant" not in role:
                        valid_instructors.append(name)
                else:  # labs
                    # labs can be taught by assistants
                    if "Assistant" in role:
                        valid_instructors.append(name)
        
        if not valid_instructors:
            failed.append({
                "session": var_name,
                "course": course_id,
                "type": session_type,
                "reason": f"No qualified instructor"
            })
            continue
        
        # try to pick days this group hasn't used yet
        days_already_used = group_days_used[group_name]
        days_not_used = [d for d in days if d not in days_already_used]
        
        # if we've used all days already, just use any
        if not days_not_used:
            days_not_used = days.copy()
        
        # build timeslot list with priorities
        timeslots_prioritized = []
        
        # prefer unused days first
        for day in days_not_used:
            for ts in day_to_timeslots[day]:
                if ts not in timeslots_prioritized:
                    timeslots_prioritized.append(ts)
        
        # then add already-used days
        for ts in all_timeslots:
            if ts not in timeslots_prioritized:
                timeslots_prioritized.append(ts)
        
        # shuffle to add some randomness
        random.shuffle(valid_instructors)
        random.shuffle(valid_rooms)
        
        # try to find a valid assignment
        found = False
        
        for instructor in valid_instructors:
            if found:
                break
            
            for timeslot in timeslots_prioritized:
                if found:
                    break
                
                # check instructor preferences (not a hard rule)
                blocked_day = instructor_prefs.get(instructor)
                if blocked_day:
                    actual_day = timeslot_to_day.get(timeslot, "").lower()
                    if blocked_day in actual_day:
                        continue
                
                # instructor can't teach two things at once
                if timeslot in instructor_schedule[instructor]:
                    continue
                
                # sections can't have two classes at once
                has_conflict = False
                for sec_id in sections:
                    if timeslot in section_schedule[sec_id]:
                        has_conflict = True
                        break
                
                if has_conflict:
                    continue
                
                # try to find an available room
                for room in valid_rooms:
                    if timeslot in room_schedule[room]:
                        continue
                    
                    # found a valid combo!
                    solution[var_name] = (instructor, room, timeslot)
                    
                    # update schedules
                    instructor_schedule[instructor].add(timeslot)
                    room_schedule[room].add(timeslot)
                    for sec_id in sections:
                        section_schedule[sec_id].add(timeslot)
                    
                    # track day usage
                    assigned_day = timeslot_to_day[timeslot]
                    group_days_used[group_name].add(assigned_day)
                    
                    found = True
                    assigned += 1
                    break
        
        if not found:
            failed.append({
                "session": var_name,
                "course": course_id,
                "type": session_type,
                "reason": "No valid combination found"
            })
    
    print(f"\n✅ Successfully assigned: {assigned}/{total} sessions")
    
    if failed:
        print(f"\n⚠️  Failed to assign {len(failed)} sessions:")
        for f in failed[:15]:  # show first 15
            print(f"   - {f['session']} ({f['course']} - {f['type']}): {f['reason']}")
        if len(failed) > 15:
            print(f"   ... and {len(failed) - 15} more")
    
    # show day distribution
    print(f"\n📊 Day Distribution per Group:")
    for group_name in sorted(group_days_used.keys()):
        days_used = sorted(group_days_used[group_name])
        print(f"   {group_name}: {len(days_used)}/5 days → {', '.join(days_used)}")
    
    if assigned == 0:
        print("❌ Couldn't assign anything!")
        return pd.DataFrame()
    
    # convert to dataframe
    timetable_rows = []
    times_dict = times_df.set_index("TimeSlotID").to_dict('index')
    
    for session in sessions_sorted:
        var_name = session["variable_name"]
        if var_name not in solution:
            continue
        
        instructor, room, timeslot = solution[var_name]
        time_info = times_dict[timeslot]
        
        for sec_id in session["sections"]:
            timetable_rows.append({
                "SectionID": sec_id,
                "CourseID": session["course_id"],
                "SessionType": session["session_type"],
                "Instructor": instructor,
                "Room": room,
                "TimeSlot": timeslot,
                "Day": time_info["Day"],
                "StartTime": time_info["StartTime"],
                "EndTime": time_info["EndTime"]
            })
    
    df = pd.DataFrame(timetable_rows)
    
    if df.empty:
        print("❌ No timetable generated!")
    else:
        print(f"\n✅ Generated timetable with {len(df)} entries")
    
    return df