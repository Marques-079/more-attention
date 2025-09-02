import pyautogui
import time
import platform
import math

media_options = [(459, 238), (255,358), (453, 357), (253, 478), (453, 475)]
#Minecraft1, Minecraft2, Ai fruits, Subway Surfers, Minecraft Parkour

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

    pyautogui.press("enter", presses = 1) #Complete cropping to audio length
    return

def make_edits2(media_to_use, audio_duration):
    audio_duration = math.ceil(audio_duration)

    """entering global media and adding background to timeline"""
    pyautogui.moveTo(48, 240)   
    pyautogui.leftClick()

    media_x, media_y = media_options[media_to_use]
    pyautogui.moveTo(media_x, media_y)

    #Location to drop into time
    end_x, end_y     = 225, 785  

    pyautogui.moveTo(media_x, media_y, duration=0.15)  # hover to start
    time.sleep(0.05)
    pyautogui.mouseDown(button="left")                 # press & hold
    pyautogui.moveTo(end_x, end_y, duration=0.25)      # drag while holding
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

    #Import audio clio

    #Add audio clip to timeline

    #Add subtitles

    #Edit and finalise subtitles

    #Share and save

    #Exit program
