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

# ---------------------------
# CONFIG (paths + OAuth)
# ---------------------------

# Folder that contains your different channel OAuth JSON files
# (same place where "whatreallyhappened.json" already lives)
YT_API_DIR = (Path.cwd().parents[2] /
              "Documents" / "Github" / "more-attention" / "yt_apis")

# Where to store OAuth tokens (one per channel)
TOKEN_DIR = Path.cwd() / "tokens"
TOKEN_DIR.mkdir(parents=True, exist_ok=True)

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
# Helpers to resolve creds
# ---------------------------
def resolve_channel_credentials(channel_api_json: str) -> tuple[str, str]:
    """
    Resolve the client_secret_file and a per-channel token file.

    channel_api_json can be 'whatreallyhappened.json' or just 'whatreallyhappened'.
    """
    fname = channel_api_json if channel_api_json.endswith(".json") else f"{channel_api_json}.json"

    # Allow absolute paths too
    candidate = Path(fname)
    if not candidate.is_absolute():
        candidate = (YT_API_DIR / fname).resolve()

    if not candidate.exists():
        raise FileNotFoundError(f"Client secret file not found: {candidate}")

    token_file = (TOKEN_DIR / f"token_{candidate.stem}.json").resolve()
    return str(candidate), str(token_file)


# ---------------------------
# Auth helper (parameterized)
# ---------------------------
def get_youtube_service(client_secret_file: str, token_file: str):
    """Authenticate and return an authorized YouTube API client for the given channel."""
    creds = None
    if Path(token_file).exists():
        try:
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, SCOPES)
        # Opens a local server to complete OAuth
        creds = flow.run_local_server(port=0)
        with open(token_file, "w", encoding="utf-8") as f:
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
    try:
        dt_local = datetime.fromisoformat(dt_local_str.strip())
    except ValueError:
        raise ValueError("Use 'YYYY-MM-DD HH:MM' (or HH:MM:SS) for schedule time.")

    dt_local = dt_local.replace(tzinfo=ZoneInfo(tz_name))
    dt_utc = dt_local.astimezone(ZoneInfo("UTC"))
    return dt_utc.replace(microsecond=0).isoformat().replace("+00:00", "Z")


# ---------------------------
# Core uploader
# ---------------------------
def upload_video_with_thumbnail(
    video_path: str | os.PathLike,
    thumbnail_path: str | os.PathLike | None = None,   # <— changed
    *,
    mode: str = "instant",
    schedule_at_local: str | None = None,
    title: str = "",
    description: str = "",
    hashtags_text: str = "",
    tags_list: list[str] | None = None,
    category_id: str = "24",
    made_for_kids: bool = False,
    client_secret_file: str = "",
    token_file: str = "",
) -> str:
    """
    Uploads a video, sets metadata & thumbnail, and returns the videoId.
    """
    if not client_secret_file or not token_file:
        raise ValueError("client_secret_file and token_file are required (per-channel auth).")

    yt = get_youtube_service(client_secret_file, token_file)

    snippet = {
        "title": title.strip() or "Untitled Upload",
        # Hashtags belong in title or description as plain text starting with '#'
        "description": (description.strip() + ("\n\n" + hashtags_text.strip() if hashtags_text.strip() else "")),
        "categoryId": category_id,
    }
    if tags_list:
        # Hidden "tags" (<= 500 chars total)
        snippet["tags"] = tags_list

    mode = (mode or "instant").lower()
    if mode == "instant":
        status = {"privacyStatus": "public", "selfDeclaredMadeForKids": bool(made_for_kids)}
    elif mode == "scheduled":
        if not schedule_at_local:
            raise ValueError("For mode='scheduled', provide schedule_at_local (e.g., '2025-09-10 18:30').")
        publish_at_utc = nz_local_to_rfc3339_utc(schedule_at_local, tz_name=DEFAULT_TZ)
        status = {"privacyStatus": "private", "publishAt": publish_at_utc, "selfDeclaredMadeForKids": bool(made_for_kids)}
    elif mode == "private":
        status = {"privacyStatus": "private", "selfDeclaredMadeForKids": bool(made_for_kids)}
    else:
        raise ValueError("mode must be one of: 'instant', 'scheduled', 'private'")

    body = {"snippet": snippet, "status": status}

    vpath = Path(video_path)
    tpath = Path(thumbnail_path) if thumbnail_path else None
    if not vpath.exists():
        raise FileNotFoundError(f"Video not found: {vpath}")

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

    # --- only set a thumbnail if one was provided ---
    if tpath and tpath.exists():
        try:
            print(f"Setting thumbnail: {tpath.name}")
            yt.thumbnails().set(videoId=video_id, media_body=str(tpath)).execute()
        except HttpError as e:
            print(f"Thumbnail set failed (continuing): {e}")
    else:
        print("No thumbnail provided; skipping thumbnails.set for this upload.")

    return video_id


# ---------------------------
# Public wrapper you call
# ---------------------------
def upload_youtube2(
    VIDEO_PATH,
    THUMB_PATH,
    TITLE,
    DESCRIPTION,
    HASHTAGS,
    TAGS,
    MODE,
    SCHEDULE_AT_LOCAL,
    channel_api_json: str = "whatreallyhappened.json",  # <-- pick channel here
):
    # Resolve which channel to use
    client_secret_file, token_file = resolve_channel_credentials(channel_api_json)

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
        client_secret_file=client_secret_file,  # per-channel
        token_file=token_file,                  # per-channel
    )

    print(f"\nDone. Video published/queued: https://www.youtube.com/watch?v={video_id}")
    return video_id
