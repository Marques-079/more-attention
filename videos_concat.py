#!/usr/bin/env python3
"""
Randomly trim the first N seconds from every video in a folder, normalize each
segment (stable PTS, CFR video, clean audio), then concatenate seamlessly.

Fixes:
- Single-frame flicker at joins (mismatched PTS/GOP)
- Frozen/held frames (dupes/VFR) via mpdecimate + CFR
- Audio pacing/PTS drift via aresample async

Usage:
  python videos_concat.py "/path/to/folder" [lower_sec upper_sec [output_name.mp4 [seed]]]
"""

import subprocess, sys, shlex, tempfile, re, random, math
from pathlib import Path
from datetime import datetime

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".m4v", ".avi", ".webm"}

# -------------------------
# Utilities
# -------------------------
def has_ffmpeg() -> None:
    for bin_ in ("ffmpeg", "ffprobe"):
        try:
            subprocess.run([bin_, "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except Exception:
            raise SystemExit(f"Error: `{bin_}` not found. Please install ffmpeg (e.g., `brew install ffmpeg`).")

def natural_key(s: str):
    # Sort 1,2,10 rather than 1,10,2
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]

def find_videos(input_dir: Path):
    files = [p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXTS]
    return sorted(files, key=lambda p: natural_key(p.name))

def run(cmd: str) -> int:
    print(f"$ {cmd}")
    proc = subprocess.run(shlex.split(cmd))
    return proc.returncode

def ffprobe_duration(path: Path) -> float:
    """Return duration in seconds (float)."""
    cmd = [
        "ffprobe","-v","error","-show_entries","format=duration",
        "-of","default=noprint_wrappers=1:nokey=1", str(path)
    ]
    out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
    try:
        return float(out)
    except Exception:
        return 0.0

def build_concat_list_file(paths, list_path: Path):
    with list_path.open("w", encoding="utf-8") as f:
        for p in paths:
            escaped = str(p).replace("'", "'\\''")
            f.write(f"file '{escaped}'\n")

# -------------------------
# Concat normalized segments losslessly
# -------------------------
def concat_stream_copy(paths, out_path: Path) -> int:
    with tempfile.TemporaryDirectory() as td:
        list_file = Path(td) / "inputs.txt"
        build_concat_list_file(paths, list_file)
        cmd = (
            f"ffmpeg -hide_banner -y "
            f"-f concat -safe 0 -i {shlex.quote(str(list_file))} "
            f"-fflags +genpts -avoid_negative_ts make_zero "
            f"-c copy {shlex.quote(str(out_path))}"
        )
        return run(cmd)

# -------------------------
# Main (random trims + robust normalization + concat)
# -------------------------
def concatenate_folder_random_slices_seamless(
    input_folder: str,
    lower_sec: int = 3,
    upper_sec: int = 6,
    output_name: str | None = None,
    seed: int | None = None,
    target_height: int = 1080,
    target_fps: int = 30,
    crf: int = 18,
    preset: str = "slow",
):
    """
    For each clip, pick a random integer N in [lower_sec, upper_sec],
    take the FIRST N seconds (capped by clip duration), normalize timestamps,
    enforce CFR, drop duplicate frames, fix audio pacing, then concat.
    """
    if lower_sec < 1 or upper_sec < 1 or upper_sec < lower_sec:
        raise SystemExit("Invalid bounds: ensure integers lower_sec>=1, upper_sec>=lower_sec.")

    has_ffmpeg()
    if seed is not None:
        random.seed(seed)

    in_dir = Path(input_folder).expanduser().resolve()
    if not in_dir.is_dir():
        raise SystemExit(f"Not a directory: {in_dir}")

    clips = find_videos(in_dir)
    if not clips:
        raise SystemExit(f"No videos found in: {in_dir}")

    downloads = Path.home() / "Downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = downloads / (output_name or f"mega_concat_seamless2_{stamp}.mp4")

    print(f"Found {len(clips)} videos.")
    for i, p in enumerate(clips, 1):
        print(f"  {i:02d}. {p.name}")

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        seg_dir = td / "segments_norm"
        seg_dir.mkdir(parents=True, exist_ok=True)
        segments = []

        print("\n== Trimming & NORMALIZING segments (seamless settings) ==")
        total = len(clips)
        for i, src in enumerate(clips, start=1):
            dur = ffprobe_duration(src)
            if dur <= 0:
                print(f"[{i}/{total}] ⚠️  Skipping (unknown duration): {src.name}")
                continue

            rand_n = random.randint(lower_sec, upper_sec)  # inclusive
            take_n = int(min(rand_n, math.floor(dur)))
            if take_n <= 0:
                print(f"[{i}/{total}] ⚠️  Clip too short (<1s), skipping: {src.name}")
                continue

            dst = seg_dir / f"{i:04d}_{src.stem}_first{take_n}s.mp4"

            # IMPORTANT: escape the comma in min() => min(1080\,ih)
            vf_parts = [
                "setpts=PTS-STARTPTS",
                "mpdecimate",
                f"fps={target_fps}",
                f"scale=-2:min({target_height}\\,ih)",
                "format=yuv420p",
            ]
            vf = ",".join(vf_parts)

            af = "aresample=async=1:first_pts=0"

            cmd = (
                f"ffmpeg -hide_banner -y "
                f"-analyzeduration 100M -probesize 100M "
                f"-ss 0 -t {take_n} -i {shlex.quote(str(src))} "
                f"-vf {shlex.quote(vf)} -af {shlex.quote(af)} "
                f"-sn "
                f"-fps_mode cfr "
                f"-c:v libx264 -crf {crf} -preset {preset} "
                f"-c:a aac -b:a 320k -ar 48000 -ac 2 "
                f"-movflags +faststart "
                f"-fflags +genpts -avoid_negative_ts make_zero "
                f"{shlex.quote(str(dst))}"
            )

            print(f"[{i}/{total}] Build segment: {src.name} -> first {take_n}s (N={rand_n})")
            code = run(cmd)
            if code != 0:
                # Fallback: keep dimensions, just ensure even size; still escape comma if used
                print("   ↪ retrying with simple even-dimension scale (no min()) …")
                vf_simple = ",".join([
                    "setpts=PTS-STARTPTS",
                    "mpdecimate",
                    f"fps={target_fps}",
                    "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                    "format=yuv420p",
                ])
                cmd2 = (
                    f"ffmpeg -hide_banner -y "
                    f"-analyzeduration 100M -probesize 100M "
                    f"-ss 0 -t {take_n} -i {shlex.quote(str(src))} "
                    f"-vf {shlex.quote(vf_simple)} -af {shlex.quote(af)} "
                    f"-sn -fps_mode cfr "
                    f"-c:v libx264 -crf {crf} -preset {preset} "
                    f"-c:a aac -b:a 320k -ar 48000 -ac 2 "
                    f"-movflags +faststart "
                    f"-fflags +genpts -avoid_negative_ts make_zero "
                    f"{shlex.quote(str(dst))}"
                )
                code2 = run(cmd2)
                if code2 != 0:
                    print(f"   ❌ Failed to normalize {src.name}; skipping this clip.")
                    continue

            segments.append(dst)

        if not segments:
            raise SystemExit("No segments produced; nothing to concatenate.")

        print(f"\nProduced {len(segments)} normalized segments.")
        print("\n== Concatenating normalized segments (stream copy) ==")
        code2 = concat_stream_copy(segments, out)
        if code2 == 0:
            print(f"\n✅ Done. Saved to: {out}")
        else:
            raise SystemExit("Concatenation failed (unexpected).")

# -------------------------
# CLI
# -------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python videos_concat.py /path/to/folder [lower_sec upper_sec [output_name.mp4 [seed]]]")
        print("Example:")
        print('  python videos_concat.py "~/Movies/clips" 3 6 mega_seamless.mp4 42')
        sys.exit(1)

    folder = sys.argv[1]
    lower = int(sys.argv[2]) if len(sys.argv) >= 3 else 3
    upper = int(sys.argv[3]) if len(sys.argv) >= 4 else 6
    name  = sys.argv[4] if len(sys.argv) >= 5 else None
    seed  = int(sys.argv[5]) if len(sys.argv) >= 6 else None

    concatenate_folder_random_slices_seamless(
        folder,
        lower_sec=lower,
        upper_sec=upper,
        output_name=name,
        seed=seed,
        target_height=1080,   # raise to 2160 to keep 4K height, or swap to vf_simple fallback always
        target_fps=30,        # set to 60 if your sources are 60fps
        crf=18,
        preset="slow",
    )


#python videos_concat.py "/Users/marcus/Downloads/satis3" 3 6 mega_showreel.mp4 123