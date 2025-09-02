#!/usr/bin/env python3
import subprocess
import time
import psutil
from pathlib import Path
import pyautogui

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
    pyautogui.moveTo(55, 52)
    time.sleep(0.5)
    pyautogui.click()
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

def make_edits():
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
    
    centre_proj()
    
