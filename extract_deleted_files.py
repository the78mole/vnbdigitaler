#!/usr/bin/env python3
"""
Skript zum Extrahieren gelöschter Python-Dateien aus der Git-Historie
"""

import subprocess
from pathlib import Path


def run_git_command(args):
    """Führe Git-Kommando (ohne Shell) aus und gib Output zurück"""
    try:
        result = subprocess.run(  # nosec B603
            ["git", *args], capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Fehler beim Ausführen von 'git {' '.join(args)}': {e}")
        return ""


def get_deleted_files():
    """Hole alle gelöschten Python-Dateien"""
    output = run_git_command(
        ["log", "--name-only", "--pretty=format:", "--diff-filter=D"]
    )
    return sorted(
        {line.strip() for line in output.split("\n") if line.strip().endswith(".py")}
    )


def find_last_commit_for_file(filepath):
    """Finde den letzten Commit, in dem eine Datei existierte"""
    output = run_git_command(
        ["log", "--all", "--full-history", "--pretty=format:%H", "--", filepath]
    )
    return output.split("\n", 1)[0] if output else ""


def extract_file_from_commit(filepath, commit_hash):
    """Extrahiere eine Datei aus einem bestimmten Commit"""
    # Bestimme Zielverzeichnis
    dir_path = Path(filepath).parent
    target_dir = Path("archive") if dir_path.name in {"", "."} else dir_path / "archive"

    # Erstelle Zielverzeichnis
    target_dir.mkdir(parents=True, exist_ok=True)

    # Extrahiere Datei
    filename = Path(filepath).name
    target_path = target_dir / filename

    # Versuche verschiedene Commit-Varianten
    commands_to_try = [
        ["show", f"{commit_hash}:{filepath}"],
        ["show", f"{commit_hash}^:{filepath}"],
        ["show", f"{commit_hash}~1:{filepath}"],
    ]

    for cmd in commands_to_try:
        try:
            content = run_git_command(cmd)
            if content:
                target_path.write_text(content, encoding="utf-8")
                print(f"✅ Extrahiert: {filepath} -> {target_path}")
                return True
        except Exception:
            continue

    print(f"❌ Konnte nicht extrahieren: {filepath}")
    return False


def main():
    print("🔍 Suche gelöschte Python-Dateien...")
    deleted_files = get_deleted_files()

    print(f"📋 Gefunden: {len(deleted_files)} gelöschte Python-Dateien")

    success_count = 0
    for filepath in deleted_files:
        if not filepath:
            continue

        print(f"📁 Verarbeite: {filepath}")
        commit = find_last_commit_for_file(filepath)

        if commit:
            if extract_file_from_commit(filepath, commit):
                success_count += 1
        else:
            print(f"❌ Kein Commit gefunden für: {filepath}")

    print(f"\n🎉 Erfolgreich extrahiert: {success_count}/{len(deleted_files)} Dateien")


if __name__ == "__main__":
    main()
