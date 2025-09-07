import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

print(REPO_ROOT)
# ----------------------------------------------------------------

from alpha.a_main import run_alpha

# Set to None for instant, or "YYYY-MM-DD HH:MM" for scheduled (24hr time, local timezone) eg. "2025-09-04 19:30"
schedule_time = None
# Choose a mode: "instant" | "scheduled" | "private"
mode = "private"
#Topic on what to make vid on
topic = "I Found My Dad’s Secret Second Family. nd They Knew About Me All Along"

run_alpha(topic, setting=mode, schedlue_time=schedule_time)