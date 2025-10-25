from Backend.solver import run_solver

def main():
    print("=" * 80)
    print(" AUTOMATED TIMETABLE GENERATION SYSTEM")
    print(" Using Constraint Satisfaction Problem (CSP) Model")
    print("=" * 80)
    print()
    
    try:
        # run the solver
        timetable_df = run_solver()
        
        if not timetable_df.empty:
            print("\n" + "=" * 80)
            print("  SUCCESS! Timetable Generated")
            print("=" * 80)
            print(f"\n Total Sessions Scheduled: {len(timetable_df)}")
            print(f" Unique Sections: {timetable_df['SectionID'].nunique()}")
            print(f" Unique Courses: {timetable_df['CourseID'].nunique()}")
            print(f" Unique Instructors: {timetable_df['Instructor'].nunique()}")
            print(f" Unique Rooms: {timetable_df['Room'].nunique()}")
            
            print("\n Sample of Generated Timetable:")
            print(timetable_df.head(10).to_string(index=False))
            
            print("\n Done! Timetable saved in Output/generated_timetable.csv")
            print(" Run Streamlit app to view: streamlit run Frontend/app.py")
        else:
            print("\n FAILED: Could not generate a valid timetable")
            print(" Suggestions:")
            print("   - Check if all courses have qualified instructors")
            print("   - Verify room availability")
            print("   - Consider adding more time slots or rooms")
    
    except FileNotFoundError as e:
        print(f"\n ERROR: {e}")
        print("💡 Make sure all CSV files are in the CSV/ folder")
    except Exception as e:
        print(f"\n UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()