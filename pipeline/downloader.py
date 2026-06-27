import subprocess
import tempfile
from pathlib import Path
from rich.console import Console

console = Console()

def download_instagram_video(url: str, output_dir: Path | None = None) -> Path:
    """Download an Instagram video and return the path to the video file."""
    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp(prefix="sales_pro_"))
    output_dir.mkdir(parents=True, exist_ok=True)

    output_template = str(output_dir / "%(id)s.%(ext)s")

    cmd = [
        "yt-dlp",
        "--no-playlist",
        "--format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "--output", output_template,
        "--print", "after_move:filepath",
        url,
    ]

    console.print(f"[cyan]Downloading:[/cyan] {url}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed:\n{result.stderr}")

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
