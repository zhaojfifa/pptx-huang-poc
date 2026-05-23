import hashlib
import logging
import os
import subprocess
from pathlib import Path

from config.settings import PREVIEW_DIR

logger = logging.getLogger(__name__)


def _find_mmdc():
    import shutil
    path = shutil.which("mmdc")
    if path:
        return path
    # Common npm global paths on Windows
    for candidate in [
        Path("C:/Program Files/nodejs/mmdc.cmd"),
        Path("C:/Users/xazx-01/AppData/Roaming/npm/mmdc.cmd"),
        Path("C:/Users/xazx-01/AppData/Roaming/npm/mmdc"),
    ]:
        if candidate.exists():
            return str(candidate)
    return None


def _get_mermaid_env():
    """Build environment dict with Node.js and npm paths injected."""
    env = os.environ.copy()
    extra_paths = []

    # Common Node.js installation paths on Windows
    node_paths = [
        Path("C:/Program Files/nodejs"),
        Path("C:/Program Files (x86)/nodejs"),
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/nodejs",
    ]
    for p in node_paths:
        if p.exists():
            extra_paths.append(str(p))

    # Common npm global paths
    npm_paths = [
        Path("C:/Users/xazx-01/AppData/Roaming/npm"),
        Path("C:/Program Files/nodejs"),
    ]
    for p in npm_paths:
        if p.exists():
            extra_paths.append(str(p))

    if extra_paths:
        path_sep = os.pathsep  # ; on Windows, : on Unix
        env["PATH"] = path_sep.join(extra_paths + [env.get("PATH", "")])

    return env


_MMDC_PATH = _find_mmdc()


class MermaidSkill:
    """Wrapper for mermaid-cli (mmdc). Falls back to placeholder if unavailable."""

    def __init__(self):
        self.available = _MMDC_PATH is not None
        if not self.available:
            logger.warning("mmdc not found. Mermaid diagrams will be rendered as placeholders.")

    def render(self, mermaid_text: str, output_filename: str = None, scale: int = 2) -> str:
        if not output_filename:
            hash_val = hashlib.md5(mermaid_text.encode()).hexdigest()[:8]
            output_filename = f"mermaid_{hash_val}.png"

        output_path = PREVIEW_DIR / output_filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.available:
            logger.warning("mmdc unavailable, skipping mermaid render")
            raise RuntimeError("mermaid-cli (mmdc) not available")

        temp_dir = Path(".temp_mermaid")
        temp_dir.mkdir(exist_ok=True)
        hash_val = hashlib.md5(mermaid_text.encode()).hexdigest()[:8]
        temp_file = temp_dir / f"{hash_val}.mmd"
        temp_file.write_text(mermaid_text, encoding="utf-8")

        logger.info(f"Rendering mermaid diagram to {output_path}...")
        env = _get_mermaid_env()
        try:
            result = subprocess.run(
                [_MMDC_PATH, "-i", str(temp_file), "-o", str(output_path), "-s", str(scale)],
                check=True,
                capture_output=True,
                text=True,
                errors="replace",
                env=env,
            )
            logger.info(f"Mermaid diagram saved to {output_path}")
            return str(output_path)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            stderr = getattr(e, 'stderr', '') or str(e)
            logger.error(f"mmdc failed: {stderr}")
            raise RuntimeError(f"mmdc failed: {stderr}")
