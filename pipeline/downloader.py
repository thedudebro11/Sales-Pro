import subprocess
import tempfile
from pathlib import Path
from rich.console import Console

console = Console()

_YOUTUBE_HOSTS = ("youtube.com", "youtu.be", "www.youtube.com", "m.youtube.com")

# Drop yt-cookies.txt in the project root to authenticate YouTube downloads.
_COOKIES_FILE = Path(__file__).parent.parent / "yt-cookies.txt"


def _is_youtube(url: str) -> bool:
    return any(h in url for h in _YOUTUBE_HOSTS)


def _yt_auth_args() -> list[str]:
    """Return the best available YouTube auth args."""
    if _COOKIES_FILE.exists():
        console.print(f"[dim]Using cookies file: {_COOKIES_FILE.name}[/dim]")
        return ["--cookies", str(_COOKIES_FILE)]
    # Fall back to live browser extraction (requires browser to be closed)
    return ["--cookies-from-browser", "chrome"]


def download_instagram_video(url: str, output_dir: Path | None = None) -> Path:
    """Download a video (Instagram or YouTube) and return the path to the file."""
    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp(prefix="sales_pro_"))
    output_dir.mkdir(parents=True, exist_ok=True)

    output_template = str(output_dir / "%(id)s.%(ext)s")
    console.print(f"[cyan]Downloading:[/cyan] {url}")

    base = [
        "yt-dlp",
        "--no-playlist",
        "--format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "--output", output_template,
        "--print", "after_move:filepath",
    ]

    if _is_youtube(url):
        # iOS client supports cookies (android skips them); node runtime + remote solver scripts handle signatures
        yt_flags = [
            "--js-runtimes", "node",
            "--remote-components", "ejs:github",
        ]
        yt_extra = ["--extractor-args", "youtube:player_client=ios,web"] + yt_flags + _yt_auth_args()
        yt_fallback = ["--extractor-args", "youtube:player_client=web"] + yt_flags + _yt_auth_args()
        attempts = [base + yt_extra + [url], base + yt_fallback + [url]]
    else:
        attempts = [base + [url]]

    last_error = ""
    result = None
    for cmd in attempts:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            break
        last_error = result.stderr.strip()

    if result is None or result.returncode != 0:
        # Surface the most actionable part of the error
        hint = ""
        if "Sign in" in last_error or "bot" in last_error:
            hint = (
                "\n\nFix: close Chrome, then run once in PowerShell:\n"
                f'  yt-dlp --cookies-from-browser chrome --cookies yt-cookies.txt "https://www.youtube.com"\n'
                "Then retry — the app will use yt-cookies.txt automatically."
            )
        raise RuntimeError(f"yt-dlp failed: {last_error}{hint}")

    filepath = result.stdout.strip().splitlines()[-1]
    video_path = Path(filepath)
    console.print(f"[green]Downloaded:[/green] {video_path.name}")
    return video_path


def extract_audio(video_path: Path) -> Path:
    """Extract mono 16kHz WAV from video — the format Whisper wants."""
    audio_path = video_path.with_suffix(".wav")
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
        str(audio_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{result.stderr}")
    return audio_path
