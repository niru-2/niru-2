from __future__ import annotations

import argparse
import sys
from typing import Optional

from . import __version__
from .actions import ActionResult, download_song, open_folder
from .intents import Intent, detect_intent


def _handle_intent(intent: Intent, dry_run: bool = False) -> ActionResult:
    if intent.name == "open_folder":
        return open_folder(intent.params.get("path", ""), dry_run=dry_run)
    if intent.name == "download_song":
        return download_song(
            query=intent.params.get("query", ""),
            dest_dir=intent.params.get("dest", None),
            dry_run=dry_run,
        )
    return ActionResult(False, "Sorry, I didn't understand that.")


def _run_text_command(text: str, dry_run: bool = False) -> int:
    intent = detect_intent(text)
    result = _handle_intent(intent, dry_run=dry_run)
    print(result.message)
    return 0 if result.ok else 1


def main(argv: Optional[list[str]] = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="niru",
        description="Niru - your local CLI assistant",
    )
    parser.add_argument("text", nargs=argparse.REMAINDER, help="Natural-language command, e.g. 'open folder ~/Downloads'")
    parser.add_argument("--open", dest="open_path", help="Explicitly open a folder path")
    parser.add_argument("--download", dest="download_query", help="Explicitly download a song by query or URL")
    parser.add_argument("--dest", dest="dest", help="Destination folder for downloads")
    parser.add_argument("--dry-run", action="store_true", help="Print what would happen without doing it")
    parser.add_argument("--version", action="version", version=f"niru {__version__}")

    args = parser.parse_args(argv)

    # Explicit flags take precedence
    if args.open_path:
        result = open_folder(args.open_path, dry_run=args.dry_run)
        print(result.message)
        return 0 if result.ok else 1

    if args.download_query:
        result = download_song(args.download_query, dest_dir=args.dest, dry_run=args.dry_run)
        print(result.message)
        return 0 if result.ok else 1

    # Fallback to natural-language text
    if args.text:
        text = " ".join(args.text).strip()
        if text:
            return _run_text_command(text, dry_run=args.dry_run)

    # If no input given, start a simple REPL
    print("Niru ready. Type 'exit' or Ctrl-D to quit.")
    try:
        while True:
            try:
                line = input("niru> ").strip()
            except EOFError:
                print()
                break
            if not line:
                continue
            if line.lower() in {"exit", "quit", ":q"}:
                break
            code = _run_text_command(line, dry_run=args.dry_run)
            if code != 0:
                # do not exit REPL on failure; continue
                pass
    except KeyboardInterrupt:
        print()
        return 0

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
