from __future__ import annotations
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from datetime import datetime
from zoneinfo import ZoneInfo  # Python 3.9+
from pathlib import Path
import os
import sys
import time


# ---------------------------
# CONFIG (paths + OAuth)
# ---------------------------
CLIENT_SECRET_FILE = str((Path.cwd().parents[2] / "more-attention" / "yt_apis" / "whatreallyhappened.json").resolve())

# Scopes: upload + manage videos/metadata/thumbnail
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]

# Default timezone for scheduling (your NZ local)
DEFAULT_TZ = "Pacific/Auckland"

# Chunk size for resumable uploads (8 MB is a good balance)
CHUNK_SIZE = 8 * 1024 * 1024

# ---------------------------
# Auth helper
# ---------------------------
def get_youtube_service():
    """Authenticate and return an authorized YouTube API client."""
    creds = None
    if Path(TOKEN_FILE).exists():
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
        # Opens a local server to complete OAuth
        creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)

# ---------------------------
# Time helpers
# ---------------------------
def nz_local_to_rfc3339_utc(dt_local_str: str, tz_name: str = DEFAULT_TZ) -> str:
    """
    Convert a local NZ datetime string ('YYYY-MM-DD HH:MM' or 'YYYY-MM-DD HH:MM:SS')
    into RFC3339 UTC (e.g. '2025-09-03T12:00:00Z').
    """
    # Accept "YYYY-MM-DD HH:MM" or "...:SS"
    try:
        dt_local = datetime.fromisoformat(dt_local_str.strip())
    except ValueError:
        raise ValueError("Use 'YYYY-MM-DD HH:MM' (or HH:MM:SS) for schedule time.")

    # Attach timezone and convert to UTC
    dt_local = dt_local.replace(tzinfo=ZoneInfo(tz_name))
    dt_utc = dt_local.astimezone(ZoneInfo("UTC"))
    return dt_utc.replace(microsecond=0).isoformat().replace("+00:00", "Z")

# ---------------------------
# Core uploader
# ---------------------------
def upload_video_with_thumbnail(
    video_path: str | os.PathLike,
    thumbnail_path: str | os.PathLike,
    *,
    mode: str = "instant",            # "instant" | "scheduled" | "private"
    schedule_at_local: str | None = None,  # "YYYY-MM-DD HH:MM" in Pacific/Auckland
    title: str = "",
    description: str = "",
    hashtags_text: str = "",          # e.g., "#AITA #Reddit #Shorts"
    tags_list: list[str] | None = None, # non-public tags (not the #hashtags)
    category_id: str = "24",          # 24 = Entertainment
    made_for_kids: bool = False
) -> str:
    """
    Uploads a video, sets metadata & thumbnail, and returns the videoId.
    """
    yt = get_youtube_service()

    # ---------------------------
    # Build snippet & status
    # ---------------------------
    # === INSERT TITLE HERE ===
    snippet = {
        "title": title.strip() or "Untitled Upload",
        # === INSERT DESCRIPTION + HASHTAGS HERE ===
        # Hashtags belong in title or description as plain text starting with '#'
        "description": (description.strip() + ("\n\n" + hashtags_text.strip() if hashtags_text.strip() else "")),
        "categoryId": category_id,
    }
    if tags_list:
        # These are the hidden "tags" (not hashtags). Keep <= 500 chars total.
        snippet["tags"] = tags_list

    # status based on mode
    status = {}
    mode = (mode or "instant").lower()
    if mode == "instant":
        status = {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": bool(made_for_kids),
        }
    elif mode == "scheduled":
        if not schedule_at_local:
            raise ValueError("For mode='scheduled', provide schedule_at_local (e.g., '2025-09-10 18:30').")
        publish_at_utc = nz_local_to_rfc3339_utc(schedule_at_local, tz_name=DEFAULT_TZ)
        # Scheduling requires video to be private until 'publishAt'
        status = {
            "privacyStatus": "private",
            "publishAt": publish_at_utc,
            "selfDeclaredMadeForKids": bool(made_for_kids),
        }
    elif mode == "private":
        status = {
            "privacyStatus": "private",
            "selfDeclaredMadeForKids": bool(made_for_kids),
        }
    else:
        raise ValueError("mode must be one of: 'instant', 'scheduled', 'private'")

    body = {
        "snippet": snippet,
        "status": status,
    }

    # ---------------------------
    # Upload (resumable)
    # ---------------------------
    vpath = Path(video_path)
    tpath = Path(thumbnail_path)
    if not vpath.exists():
        raise FileNotFoundError(f"Video not found: {vpath}")
    if not tpath.exists():
        raise FileNotFoundError(f"Thumbnail not found: {tpath}")

    media = MediaFileUpload(str(vpath), chunksize=CHUNK_SIZE, resumable=True)
    request = yt.videos().insert(part="snippet,status", body=body, media_body=media)

    print(f"Starting upload: {vpath.name}  ({vpath.stat().st_size/1e6:.1f} MB)")
    response = None
    try:
        while response is None:
            status_chunk, response = request.next_chunk()
            if status_chunk:
                print(f"  → Upload progress: {int(status_chunk.progress() * 100)}%")
    except HttpError as e:
        print(f"Upload failed: {e}")
        raise

    if not response or "id" not in response:
        raise RuntimeError("Upload did not return a video ID.")
    video_id = response["id"]
    print(f"Upload complete. videoId = {video_id}")

    # ---------------------------
    # Set custom thumbnail
    # ---------------------------
    try:
        print(f"Setting thumbnail: {tpath.name}")
        thumb_req = yt.thumbnails().set(videoId=video_id, media_body=str(tpath))
        thumb_resp = thumb_req.execute()
        # (Optional) print(thumb_resp)
    except HttpError as e:
        print(f"Thumbnail set failed (continuing): {e}")

    # FYI: You can further edit metadata later via videos().update(part="snippet,status", body={...})
    return video_id

# ---------------------------
# Example usage
# ---------------------------
TOKEN_FILE = "token.json"

def upload_youtube(VIDEO_PATH, THUMB_PATH, TITLE, DESCRIPTION, HASHTAGS, TAGS, MODE, SCHEDULE_AT_LOCAL):

    '''
    # === INSERT YOUR PATHS HERE ===
    VIDEO_PATH = "/Users/marcus/Downloads/reddit1_filmora_captioned/exported_2025-09-03_18-18-49_My_Video.mp4"
    THUMB_PATH = "/Users/marcus/Downloads/video_thumbnails_reddit1/WRH_black_20250903_182049.png"

    # === INSERT TITLE / DESCRIPTION / HASHTAGS HERE ===
    TITLE = "What Really Happened — AITA #42"
    DESCRIPTION = (
        "In today’s episode, we break down a wild AITA post and what actually happened.\n"
        "Chapters:\n"
        "00:00 Intro\n"
        "00:25 The post\n"
        "03:10 Reactions\n"
        "04:55 Verdict"
    )
    HASHTAGS = "#AITA #Reddit #WhatReallyHappened #Shorts"  # Hashtags go in title/description text
    TAGS = ["AITA", "Reddit", "storytime", "analysis"]      # Non-public tags array

    # Choose a mode: "instant" | "scheduled" | "private"
    MODE = "private"

    # If scheduling, set your NZ local time here (24h):
    # Format: "YYYY-MM-DD HH:MM" or "YYYY-MM-DD HH:MM:SS"
    SCHEDULE_AT_LOCAL = "2025-09-04 19:30"  # Pacific/Auckland, converted to UTC automatically
    '''

    video_id = upload_video_with_thumbnail(
        video_path=VIDEO_PATH,
        thumbnail_path=THUMB_PATH,
        mode=MODE,
        schedule_at_local=SCHEDULE_AT_LOCAL if MODE == "scheduled" else None,
        title=TITLE,
        description=DESCRIPTION,
        hashtags_text=HASHTAGS,
        tags_list=TAGS,
        category_id="24",
        made_for_kids=False,
    )

    print(f"\nDone. Video published/queued: https://www.youtube.com/watch?v={video_id}")

    return


