from pathlib import Path
from rich.console import Console
import config

console = Console()

def transcribe(audio_path: Path) -> str:
    """Transcribe audio to text using OpenAI Whisper (local, free)."""
    import whisper  # lazy import so startup is fast when not transcribing

    console.print(f"[cyan]Transcribing with Whisper ({config.WHISPER_MODEL})…[/cyan]")
    model = whisper.load_model(config.WHISPER_MODEL)
    result = model.transcribe(str(audio_path), fp16=False, language="en")
    text = result["text"].strip()
    console.print(f"[green]Transcript ready[/green] ({len(text.split())} words)")
    return text
