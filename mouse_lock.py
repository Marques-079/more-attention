#!/usr/bin/env python3
import sys
import time
import argparse
import pyautogui

def main():
    parser = argparse.ArgumentParser(description="Live mouse coordinate reader")
    parser.add_argument("--fps", type=float, default=20, help="Updates per second (default: 20)")
    parser.add_argument("--rgb", action="store_true", help="Also show RGB under cursor (may need Screen Recording perm on macOS)")
    args = parser.parse_args()

    pyautogui.FAILSAFE = True  # move mouse to a screen corner to trigger FailSafeException
    interval = 1.0 / max(1.0, args.fps)

    print("Move the mouse. Press Ctrl-C to exit.", flush=True)
    try:
        while True:
            x, y = pyautogui.position()
            line = f"X: {x:4d}  Y: {y:4d}"

            if args.rgb:
                try:
                    r, g, b = pyautogui.pixel(x, y)  # requires Pillow; on macOS needs Screen Recording permission
                    line += f"  RGB: ({r:3d}, {g:3d}, {b:3d})"
                except Exception as e:
                    line += "  RGB: (perm needed)"
            sys.stdout.write("\r" + line + " " * 10)
            sys.stdout.flush()
            time.sleep(interval)
    except KeyboardInterrupt:
        sys.stdout.write("\nBye!\n")

if __name__ == "__main__":
    main()
