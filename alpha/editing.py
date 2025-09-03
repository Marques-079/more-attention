#!/usr/bin/env python3
import subprocess
import time
import psutil
from pathlib import Path
import pyautogui
import platform
import math
import re
from datetime import datetime
import math, random
from typing import Optional, Tuple

#media_options = | (0,1), (1, 0), (1, 1), (2, 0), (2, 1)
media_options = [(459, 238), (255,358), (453, 357), (253, 478), (453, 475)]
clip_durations= [7226, 4577, 4813, 3600, 1313]

APP_PATH = "/Applications/Wondershare Filmora Mac.app"
APP_NAME = "Wondershare Filmora Mac"

def is_running() -> bool:
    for p in psutil.process_iter(attrs=["name"]):
        try:
            n = p.info.get("name") or ""
            if APP_NAME in n:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False

def open_app():
    if not Path(APP_PATH).exists():
        raise FileNotFoundError(f"App not found at: {APP_PATH}")
    # Use `open` on the .app bundle
    subprocess.Popen(["open", APP_PATH])

def activate_and_fullscreen():
    applescript = f'''
    set appName to "{APP_NAME}"
    tell application appName to activate
    tell application "System Events"
        tell process appName
            set frontmost to true

            -- Wait up to ~15s for a window to appear
            repeat with i from 1 to 60
                if (count of windows) > 0 then exit repeat
                delay 0.25
            end repeat

            if (count of windows) > 0 then
                set theWindow to window 1

                -- Unminimize if needed
                try
                    if value of attribute "AXMinimized" of theWindow is true then ¬
                        set value of attribute "AXMinimized" of theWindow to false
                end try

                -- Prefer native macOS Full Screen if supported
                set didFS to false
                try
                    set value of attribute "AXFullScreen" of theWindow to true
                    set didFS to true
                end try

                if didFS is false then
                    -- Fallback: maximize to main display bounds
                    tell application "Finder" to set screenBounds to bounds of window of desktop
                    set screenWidth to item 3 of screenBounds
                    set screenHeight to item 4 of screenBounds
                    set position of theWindow to {{0, 0}}
                    set size of theWindow to {{screenWidth, screenHeight}}
                    try
                        set zoomed of theWindow to true
                    end try
                end if
            end if
        end tell
    end tell
    '''
    subprocess.run(["osascript", "-e", applescript], check=False)

def detect_state():
    import pyautogui, time
    size = 4
    tol = int(round(255 * 0.2))  # 5% per-channel wiggle
    # --- step 1 ---
    x, y = 265, 180
    pyautogui.moveTo(x, y); time.sleep(0.05)
    img = pyautogui.screenshot(region=(x - size // 2, y - size // 2, size, size))
    tr, tg, tb = 0, 240, 214
    w, h = img.size
    ok = True
    for px in range(w):
        for py in range(h):
            r, g, b = img.getpixel((px, py))[:3]
            if abs(r - tr) > tol or abs(g - tg) > tol or abs(b - tb) > tol:
                ok = False
                break
        if not ok:
            break
    if ok:
        return 0
    # --- step 2 ---
    x, y = 908, 379
    pyautogui.moveTo(x, y); time.sleep(0.05)
    img = pyautogui.screenshot(region=(x - size // 2, y - size // 2, size, size))
    tr, tg, tb = 4, 172, min(255, 256)
    w, h = img.size
    for px in range(w):
        for py in range(h):
            r, g, b = img.getpixel((px, py))[:3]
            if abs(r - tr) <= tol and abs(g - tg) <= tol and abs(b - tb) <= tol:
                return 1
    return 2

def centre_proj():
    # pyautogui.moveTo(55, 52)
    # time.sleep(0.5)
    # pyautogui.click()

    pyautogui.moveTo(48, 240)
    # time.sleep(0.5)
    # pyautogui.moveTo(285, 242)
    # pyautogui.leftClick()

def escape_proj_screen():
    pyautogui.moveTo(219, 16)
    time.sleep(1.0)
    pyautogui.click()
    pyautogui.moveTo(215, 402)
    time.sleep(1.0)
    pyautogui.click()
    time.sleep(0.5)

def full_scren_main():
    time.sleep(0.5)
    pyautogui.moveTo(289, 126)
    pyautogui.click()

def adjust_clip_duration(audio_duration):
    """We are ready to type in our length adjustment"""
    pyautogui.press("backspace", presses=1)  # clear existing

    tot = int(audio_duration)              # floor to whole second (or use round(...))
    h = tot // 3600
    m = (tot % 3600) // 60
    s = tot % 60
    timecode = f"{h:02d}:{m:02d}:{s:02d}:00"

    pyautogui.click(); time.sleep(0.05)
    pyautogui.hotkey("command" if platform.system()=="Darwin" else "ctrl", "a")
    pyautogui.typewrite(timecode, interval=0.02)

    pyautogui.press("enter", presses = 2) #Complete cropping to audio length
    return

#================================================================Typing and saving functions=================================================================
def _slug(s: str) -> str:
    s = re.sub(r"\s+", "_", str(s).strip())
    return re.sub(r"[^A-Za-z0-9_.-]", "", s)

def build_timestamp_title(base: str,
                          duration_sec: float | int | None = None,
                          channel: str | None = None,
                          extra: str | None = None,
                          max_len: int = 64) -> str:
    """
    Make a unique, filesystem-safe title like:
      2025-09-03_23-41-12_My_Video_29s_main
    - base: human name for the video
    - duration_sec/channel/extra: optional bits to encode
    - max_len: clamp length to keep UI happy
    """
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    parts = [ts, _slug(base)]
    if duration_sec is not None:
        parts.append(f"{int(round(float(duration_sec)))}s")
    if channel:
        parts.append(_slug(channel))
    if extra:
        parts.append(_slug(extra))
    name = "_".join(p for p in parts if p)
    if len(name) > max_len:
        name = name[:max_len].rstrip("_")
    return name

def type_export_title(title: str, key_interval: float = 0.02) -> None:
    """Types the given title into the currently focused text box."""
    pyautogui.typewrite(title, interval=key_interval)

#=========== Navigate to folder in exposed dialog =========== 

def navigate_open_dialog_to_folder(dir_path: str):
    p = Path(dir_path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(p)

    ascript = f'''
    set appName to "{APP_NAME}"
    set targetDir to POSIX path of "{p.as_posix()}"

    tell application appName to activate
    delay 0.1
    tell application "System Events"
        -- Open "Go to the folder" in the NSOpenPanel
        keystroke "g" using {{command down, shift down}}
        delay 0.15
        keystroke targetDir
        keystroke return
    end tell
    '''
    subprocess.run(["osascript", "-e", ascript], check=False)

#=========================================================================#=========================================================================
def area_has_color_match(x: int, y: int,
                         target_rgba=(86, 231, 199, 255),
                         tol: float = 0.05,
                         size: int = 30):
    """
    Returns True if ANY pixel in a size×size area centered at (x, y)
    is within per-channel tolerance of target_rgba. Silent (no prints, no saves).
    """
    half = size // 2
    left, top = int(x - half), int(y - half)

    # Grab the region (no saving)
    img = pyautogui.screenshot(region=(left, top, size, size)).convert("RGBA")

    # Color match check
    thr = int(round(255 * tol))
    tr, tg, tb, ta = (tuple(target_rgba) + (255,))[:4]

    w, h = img.size
    for iy in range(h):
        for ix in range(w):
            r, g, b, a = img.getpixel((ix, iy))
            if (abs(r - tr) <= thr and
                abs(g - tg) <= thr and
                abs(b - tb) <= thr and
                abs(a - ta) <= thr):
                return True
    return False

def pick_random_crop_start(
    duration: float,
    clip_total: float,
    buffer_s: float = 60.0,
    integer_seconds: bool = False,
    rng: Optional[random.Random] = None,
) -> Tuple[float, str]:
    if duration <= 0 or clip_total <= 0:
        raise ValueError("duration and clip_total must be > 0.")
    if duration + 2 * buffer_s > clip_total:
        raise ValueError("clip_total too short for duration + buffers.")

    # honor the buffer you pass (don't hardcode 5)
    start_min = buffer_s
    start_max = clip_total - buffer_s - duration
    if start_max < start_min:
        raise ValueError("No start position fits the constraints.")

    r = rng or random  # use provided RNG or module RNG (no reseeding)

    if integer_seconds:
        imin = math.ceil(start_min)
        imax = math.floor(start_max)
        if imax < imin:
            raise ValueError("No integer start fits the constraints.")
        start = float(r.randrange(imin, imax + 1))
    else:
        start = r.uniform(start_min, start_max)

    return start, _to_timecode(start)

def _to_timecode(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


#============================================Random scrolling to stagger start=====================================================================
import time, platform, pyautogui

pyautogui.FAILSAFE = True

def mac_hscroll_pixels(delta_x_px: int, bursts: int = 1, pause: float = 0.0):
    """
    Send horizontal scroll in pixel units on macOS using Quartz.
    """
    from Quartz import (
        CGEventCreateScrollWheelEvent, CGEventPost,
        kCGHIDEventTap, kCGScrollEventUnitPixel
    )
    ev = CGEventCreateScrollWheelEvent(
        None, kCGScrollEventUnitPixel, 2, 0, int(delta_x_px)
    )
    CGEventPost(kCGHIDEventTap, ev)
    if pause:
        time.sleep(pause)

def scroll_left_incremental(start=(500, 700), pixels=114, steps=5, pause=0.01):
    """
    Focus the timeline, then scroll left in fixed increments.
    Each step = `pixels`. Run fast with tiny pauses.
    """
    # 1) Focus the timeline
    pyautogui.moveTo(*start)
    pyautogui.click()
    time.sleep(0.05)

    if platform.system() == "Darwin":
        for _ in range(steps):
            mac_hscroll_pixels(-abs(pixels))
            time.sleep(pause)
    else:
        # fallback drag for non-macOS
        thumb_x, thumb_y = start[0] + 400, start[1] + 320
        pyautogui.moveTo(thumb_x, thumb_y)
        pyautogui.mouseDown(button='left')
        for _ in range(steps):
            pyautogui.moveRel(-abs(pixels), 0, duration=0.05)
            time.sleep(pause)
        pyautogui.mouseUp(button='left')

    # 3) Return to starting position
    pyautogui.moveTo(*start)

def scroll_right_incremental(start=(500, 700), pixels=114, steps=5, pause=0.01):
    """
    Focus the timeline, then scroll right in fixed increments.
    Each step = `pixels`. Run fast with tiny pauses.
    """
    # 1) Focus timeline
    pyautogui.moveTo(*start)
    pyautogui.click()
    time.sleep(0.05)

    if platform.system() == "Darwin":
        for _ in range(steps):
            mac_hscroll_pixels(+abs(pixels))  # <-- positive for right
            time.sleep(pause)
    else:
        # fallback drag for non-macOS
        thumb_x, thumb_y = start[0] + 400, start[1] + 320
        pyautogui.moveTo(thumb_x, thumb_y)
        pyautogui.mouseDown(button='left')
        for _ in range(steps):
            pyautogui.moveRel(+abs(pixels), 0, duration=0.05)
            time.sleep(pause)
        pyautogui.mouseUp(button='left')

    # 3) Return cursor to starting point
    pyautogui.moveTo(*start)


#==========================================================================================================================================


APP_NAME = "Wondershare Filmora Mac"

def import_audio_clip(target_dir_audio: str, target_name_audio: str) -> None:
    pdir  = Path(target_dir_audio).expanduser().resolve()
    pfile = pdir / target_name_audio
    if not pfile.exists():
        raise FileNotFoundError(f"Audio file not found: {pfile}")

    ascript = f'''
    set appName    to "{APP_NAME}"
    set targetDir  to "{pdir.as_posix()}"
    set targetName to "{target_name_audio}"

    tell application appName to activate
    delay 0.3

    tell application "System Events"
        -- Ensure Filmora process exists and is frontmost
        repeat 60 times
            if (exists process appName) then exit repeat
            delay 0.1
        end repeat
        if (exists process appName) is false then return

        tell process appName
            set frontmost to true
            delay 0.1

            -- Open the Import dialog (supports both direct and nested menus)
            set fileMenu to menu "File" of menu bar 1
            set directItems to (menu items of fileMenu whose name contains "Import Media Files")
            if (count of directItems) > 0 then
                click item 1 of directItems
            else
                set parents to (menu items of fileMenu whose name contains "Import Media")
                if (count of parents) > 0 then
                    click (menu item 1 of (menu 1 of (item 1 of parents)))
                else
                    return
                end if
            end if

            -- Wait for the Open panel (as a sheet in fullscreen, or as a window)
            set thePanel to missing value
            repeat 100 times
                if (exists sheet 1 of window 1) then
                    set thePanel to sheet 1 of window 1
                    exit repeat
                else if (exists window 1 whose subrole is "AXDialog") then
                    set thePanel to (first window whose subrole is "AXDialog")
                    exit repeat
                end if
                delay 0.5
            end repeat
            if thePanel is missing value then return

            -- Bring focus to the panel and open 'Go to Folder…'
            set frontmost to true
            delay 0.3
            keystroke "g" using {{command down, shift down}}

            -- Wait for the small 'Go to the folder' sheet inside the panel
            set goSheet to missing value
            repeat 100 times
                if (exists sheet 1 of thePanel) then
                    set goSheet to sheet 1 of thePanel
                    exit repeat
                end if
                delay 0.3
            end repeat
            if goSheet is missing value then return

            -- Type the directory path precisely, then press Return
            -- (Direct value-setting can fail on some builds; keystroke is most compatible.)
            delay 0.2
            keystroke targetDir
            key code 36  -- Return

            -- Give Finder time to navigate the panel
            delay 0.4

            -- Now type the filename and press Return to open
            keystroke targetName
            key code 36  -- Return
        end tell
    end tell
    '''
    subprocess.run(["osascript", "-e", ascript], check=False)

def make_edits(media_to_use, audio_duration, target_dir_audio, target_name_audio):
    if not is_running():
        print("Filmora not running. Opening...")
        open_app()
        # Poll until the process appears (up to ~15s)
        for _ in range(60):
            if is_running():
                break
            time.sleep(0.25)
        time.sleep(3.0)  # small extra settle

    print("Focusing Filmora and full-screening…")
    activate_and_fullscreen()

    filmora_state = detect_state()
    if filmora_state == 0:
        print('We are in startup screen - primed')
    elif filmora_state == 1:
        print("We need to fullscreen")
        full_scren_main()

    elif filmora_state == 2:
        print("We are in project screen")
        escape_proj_screen()
        time.sleep(1.0)
        full_scren_main()
    else:
        print("ERROR")
    
    pyautogui.click(320, 220)
    time.sleep(2)
    
    #Prime workspace
    centre_proj()

    #Ready to start edit. 
    audio_duration = math.ceil(audio_duration)

    """entering global media and adding background to timeline"""
    pyautogui.moveTo(48, 240)   
    pyautogui.leftClick()

    media_x, media_y = media_options[media_to_use]
    pyautogui.moveTo(media_x, media_y)

    #Location to drop into time
    end_x1, end_y1     = 225, 785  
    time.sleep(2.0)
    pyautogui.moveTo(media_x, media_y, duration=0.15)  # hover to start
    time.sleep(0.15)
    pyautogui.mouseDown(button="left")                 # press & hold
    pyautogui.moveTo(end_x1, end_y1, duration=0.25)
    time.sleep(0.15)      # drag while holding
    pyautogui.mouseUp(button="left")                   # release

    time.sleep(3.0)

    "Random cropping to starttime + offset"
    rng = random.SystemRandom()
    start_s, tc = pick_random_crop_start(duration=audio_duration, clip_total=clip_durations[media_to_use], buffer_s = 60, integer_seconds=True,rng = rng)
    print(f"Picked start time: {start_s:.3f} s = {tc}")
    start_s = math.floor(start_s // 5) - 1

    #Pixels 114 -> 5 seconds move around
    time.sleep(2.0)
    scroll_left_incremental(start=(500, 700), pixels=114 * start_s, steps=start_s, pause=0.0005)

    #Crop here wit offset
    time.sleep(2.0)
    pyautogui.moveTo(213, 637)  # hover to start
    pyautogui.leftClick()

    #Cut 
    time.sleep(2.0)
    pyautogui.moveTo(214, 700)  # hover to start
    pyautogui.leftClick()

    #Delete
    time.sleep(2.0)
    pyautogui.moveTo(156, 754)  # hover to start
    pyautogui.leftClick()
    pyautogui.hotkey("backspace")

    #Reselect clip so we can edit duration -> Reselecting
    time.sleep(1.0)
    pyautogui.moveTo(115, 758)
    pyautogui.leftClick()


    """Adjust duration to fit audio clip"""

    #Move to extra options above timeline
    pyautogui.moveTo(520,600)
    time.sleep(0.3)
    pyautogui.leftClick()

    #Click into duration editor
    pyautogui.moveTo(520,655)
    time.sleep(0.3)
    pyautogui.leftClick()

    #Enter time adjustment window
    pyautogui.moveTo(749, 413)
    time.sleep(0.3)
    pyautogui.leftClick()

    #Adjust clip duration to audio length
    time.sleep(0.3)
    adjust_clip_duration(audio_duration)

    """Rescoll to realign after random clip cropping"""
    scroll_right_incremental(start=(500, 700), pixels=114 * start_s, steps= math.floor(start_s * 1.2), pause=0.0005)


    #Move mouse to prject relevant area zone
    time.sleep(2.0)
    pyautogui.moveTo(73, 154)
    pyautogui.leftClick()

    print('Working on importing audio')
    import_audio_clip(target_dir_audio, target_name_audio)
    time.sleep(2.0)
    pyautogui.leftClick(1096, 675)

    """Add audio clip to timeline"""
    end_x2, end_y2 = 88, 822

    pyautogui.moveTo(450, 265, duration=0.2)  # hover to start
    time.sleep(0.05)
    pyautogui.mouseDown(button="left")                 # press & hold
    pyautogui.moveTo(end_x2, end_y2, duration=0.25)      # drag while holding
    pyautogui.mouseUp(button="left")                   # release

    #Mute sound for gameplay background
    time.sleep(3.0)
    pyautogui.moveTo(48, 769)
    pyautogui.leftClick()

    #Save and prepare for subtitle prep.
    pyautogui.moveTo(1445, 56)
    pyautogui.leftClick()

    #Change name
    time.sleep(0.5)
    pyautogui.moveTo(695, 247)
    pyautogui.click(clicks=2, interval=0.12, button="left")
    time.sleep(0.5)
    pyautogui.hotkey("command", "a")
    time.sleep(0.5)
    pyautogui.press("backspace")

    export_title = build_timestamp_title(base="My Video")
    time.sleep(0.5)
    type_export_title(export_title)

    #AS navigate pathing for save 
    #/Users/marcus/Downloads/reddit1_filmora_clipstore
    pyautogui.click(1077,305)
    time.sleep(0.1)

    navigate_open_dialog_to_folder("/Users/marcus/Downloads/reddit1_filmora_clipstore")

    pyautogui.move(1153, 582)
    time.sleep(2.0)
    pyautogui.leftClick(1153, 582) 

    #Maximise resolution quality set to high

    pyautogui.moveTo(906, 560)
    time.sleep(0.5)
    pyautogui.leftClick(906, 560)

    pyautogui.moveTo(909, 661)
    time.sleep(0.5)
    pyautogui.leftClick(909, 661)

    '''
    Insert here to boost resolution -> Inflates storage
    '''


    #here!


    ''''''
    
    #Disable saving any previews (Update: I think it hold state between projects) 
    # time.sleep(0.1)
    # pyautogui.click(679, 714)

    #Export
    pyautogui.moveTo(1092, 760)
    time.sleep(0.5)
    pyautogui.leftClick(1092, 760)

    #Checking until export is finished exporting LOL
    
    if audio_duration > 600:
        pause_wait = 30
    else:
        pause_wait = 10

    time.sleep(pause_wait)
    while True:
        has_match = area_has_color_match(394, 481)   # saves into ./captures/

        print(f"[watch] match={has_match}")
        if has_match:
            time.sleep(3.0)
            continue
        break

    pyautogui.moveTo(359, 216)
    time.sleep(1.0)
    pyautogui.leftClick(359, 216)

    #Exit program without saving
    #hit file button
    pyautogui.moveTo(221, 16)
    time.sleep(0.5)
    pyautogui.leftClick(221, 16)

    #hit return home button
    pyautogui.moveTo(220, 429)
    time.sleep(0.5)
    pyautogui.leftClick(220, 429)

    #"Dont save"
    pyautogui.moveTo(921, 500)
    time.sleep(0.5)
    pyautogui.leftClick(921, 500)


    return export_title

