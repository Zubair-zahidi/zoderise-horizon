"""Build a clean distributable without accounts, uploads, secrets, or environments."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "Zoderise_Horizon_Customizable.zip"


def main():
    names = {"Dockerfile", "Modelfile", "Modelfile-vision", "ZoderiseDesktop.spec", ".env.example", ".gitignore", ".dockerignore"}
    files = [p for p in ROOT.iterdir() if p.is_file() and (p.suffix.lower() in {".py", ".md", ".txt", ".bat", ".yaml"} or p.name in names)]
    for folder, extensions in [("zoderise", {".py"}), ("tests", {".py"}), ("assets", {".png", ".jpg", ".webp", ".css", ".md", ".ico", ".svg"}), ("static", {".json"})]:
        files.extend(p for p in (ROOT / folder).rglob("*") if p.is_file() and p.suffix.lower() in extensions and "__pycache__" not in p.parts)
    files.append(ROOT / ".streamlit" / "config.toml")
    with ZipFile(OUTPUT, "w", ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(set(files)):
            archive.write(path, "Zoderise_Horizon/" + path.relative_to(ROOT).as_posix())
    with ZipFile(OUTPUT) as archive:
        assert archive.testzip() is None
        assert not any("/data/" in n or "/.venv/" in n or n.endswith("/.env") or n.endswith("/secrets.toml") for n in archive.namelist())
        print(f"Verified {len(archive.namelist())} files")
    print(f"{OUTPUT} ({OUTPUT.stat().st_size / 1024 / 1024:.2f} MB)")


if __name__ == "__main__":
    main()
