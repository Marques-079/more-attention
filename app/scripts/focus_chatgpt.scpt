-- Focus an existing ChatGPT tab in Google Chrome across all windows.
-- If none found, open a new tab to chatgpt.com.
set targetHosts to {"chatgpt.com", "chat.openai.com"}

tell application "Google Chrome"
  activate
  set found to false
  set theWindow to missing value
  set theTabIndex to 0

  repeat with w in windows
    -- un-minimize, in case
    try
      set minimized of w to false
    end try

    set i to 0
    repeat with t in tabs of w
      set i to i + 1
      set u to URL of t as text
      repeat with h in targetHosts
        if u contains h then
          set theWindow to w
          set theTabIndex to i
          set found to true
          exit repeat
        end if
      end repeat
      if found then exit repeat
    end repeat
    if found then exit repeat
  end repeat

  if found then
    set active tab index of theWindow to theTabIndex
    set index of theWindow to 1
  else
    if (count of windows) is 0 then
      make new window
      set theWindow to front window
    else
      set theWindow to front window
      tell theWindow to make new tab
    end if
    set URL of active tab of theWindow to "https://chatgpt.com/"
    set index of theWindow to 1
  end if
end tell

-- Extra nudge (helps if Chrome is full-screen/on another Space)
try
  tell application "System Events" to tell process "Google Chrome" to set frontmost to true
end try
