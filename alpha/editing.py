#!/usr/bin/env python3
import subprocess
import time
import psutil
from pathlib import Path
import pyautogui
import platform
import math

media_options = [(459, 238), (255,358), (453, 357), (253, 478), (453, 475)]

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

import subprocess
from pathlib import Path

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

    pyautogui.moveTo(media_x, media_y, duration=0.15)  # hover to start
    time.sleep(0.05)
    pyautogui.mouseDown(button="left")                 # press & hold
    pyautogui.moveTo(end_x1, end_y1, duration=0.25)      # drag while holding
    pyautogui.mouseUp(button="left")                   # release

    """Adjust duration to fit audio clip"""

    #Move to extra options above timeline
    pyautogui.moveTo(520,600)
    pyautogui.leftClick()

    #Click into duration editor
    pyautogui.moveTo(520,633)
    pyautogui.leftClick()

    #Enter time adjustment window
    pyautogui.moveTo(764, 439)
    pyautogui.leftClick()

    #Adjust clip duration to audio length
    adjust_clip_duration(audio_duration)

    #Import audio clip

    #Move mouse to prject relevant area zone
    pyautogui.moveTo(73, 154)
    pyautogui.leftClick()

    print('Working on importing audio')
    import_audio_clip(target_dir_audio, target_name_audio)
    time.sleep(0.3)
    pyautogui.leftClick(1096, 702)

    #Add audio clip to timeline
    end_x2, end_y2 = 84, 847

    pyautogui.moveTo(450, 265, duration=0.2)  # hover to start
    time.sleep(0.05)
    pyautogui.mouseDown(button="left")                 # press & hold
    pyautogui.moveTo(end_x2, end_y2, duration=0.25)      # drag while holding
    pyautogui.mouseUp(button="left")                   # release
    #Add subtitles

    

    #Edit and finalise subtitles

    #Share and save

    #Exit program
    
