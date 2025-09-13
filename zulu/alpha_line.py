import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

print(REPO_ROOT)
# ----------------------------------------------------------------
from alpha.a_main import run_alpha

def pop_top_line(path):
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    if not lines:
        return None  # file empty
    top_line = lines[0].rstrip("\n")
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines[1:])  
    return top_line

def append_line(path, text):
    with open(path, "a", encoding="utf-8") as f:
        f.write(text + "\n")

N = 1
for _ in range(N):
    history_path = REPO_ROOT / "video_history.txt"
    ideas_path = REPO_ROOT / "zulu" / "alpha_ideas.txt"

    topic = pop_top_line(ideas_path)
    append_line(str(history_path), topic)

    print(f"Topic: {topic}")
    # Set to None for instant, or "YYYY-MM-DD HH:MM" for scheduled (24hr time, local timezone) eg. "2025-09-04 19:30"
    schedule_time = None
    # Choose a mode: "instant" | "scheduled" | "private"
    mode = "private"
    #Topic on what to make vid on
    #topic = "I Found My Dad’s Secret Second Family. nd They Knew About Me All Along"

    run_alpha(topic, setting=mode, schedule_time=schedule_time)

print("DONE ALL")