import os
import pandas as pd
from Backend.data_loader import load_data, build_sessions
from Backend.csp_model import solve_csp

def run_solver():
    # main function that runs everything
    
    print("=" * 60)
    print(" AUTOMATED TIMETABLE GENERATOR")
    print("=" * 60)
    
    # load CSV files
    print("\n Loading CSV data...")
    data = load_data()
    
    # build session list
    print("\n Building sessions...")
    sessions = build_sessions(data)
    
    # run the solver
    print("\n Solving CSP...")
    timetable_df = solve_csp(sessions, data)
    
    if timetable_df.empty:
        print(" Failed to generate timetable")
        return timetable_df
    
    # save output
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Output")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "generated_timetable.csv")
    
    timetable_df.to_csv(output_path, index=False)
    print(f"\n✅ Timetable saved to: {output_path}")
    print(f"📊 Generated {len(timetable_df)} scheduled sessions")
    
    return timetable_df