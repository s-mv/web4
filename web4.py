#!/usr/bin/env python

"""
pip install -r requirements.txt # DO NOT FORGET TO DO THIS
"""

import shutil
import textwrap
import toml
import sys
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, HTTPServer
import argparse
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time

"""
license 2025 (c)

you shall not steal blah blah

usage: just do `python web4.py --man`

~smv
"""


class TomlChangeHandler(FileSystemEventHandler):
    def __init__(self, toml_path: Path):
        self.toml_path = toml_path.resolve()

    def on_modified(self, event):
        if Path(event.src_path).resolve() == self.toml_path:
            print(f"[watch] Change detected in {self.toml_path.name}, regenerating...")
            try:
                write_html(self.toml_path)
            except Exception as e:
                print(f"[watch] Error: {e}")

def watch_file(toml_path: Path):
    event_handler = TomlChangeHandler(toml_path)
    observer = Observer()
    observer.schedule(event_handler, toml_path.parent, recursive=False)
    observer.start()
    print(f"[watch] Watching {toml_path.name} for changes.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[watch] Stopping.")
        observer.stop()
    observer.join()

class CustomHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

def start_server(port=8080):
    httpd = HTTPServer(("", port), CustomHandler)
    print(f"Serving! At http://localhost:{port}")
    httpd.serve_forever()

def serve_file(file: Path, port=8080):
    from threading import Thread
    import webbrowser
    import time

    server_thread = Thread(target=start_server)
    server_thread.start()

    webbrowser.open(f"http://localhost:{port}/{file.name}")

    try:
        server_thread.join()  # wait forever
    except KeyboardInterrupt:
        print("\nShutting down server.")


def parse_element(name, data, tree):
    attrs = ""
    children_html = ""

    for key, value in data.items():
        if key != "children":
            attrs += f' {key}="{value}"'

    children = data.get("children", [])
    if isinstance(children, str):
        # children CAN be fallback strings
        children = [c.strip() for c in children.split(",")]

    for child in children:
        if child in tree:
            children_html += parse_element(child, tree[child], tree)
        else:
            children_html += str(child)  # treat as plain text

    return f"<{name}{attrs}>{children_html}</{name}>"


def toml_to_html(toml_file: Path) -> str:
    tree = toml.load(toml_file)

    root_section = tree.get("root")
    if not root_section or "children" not in root_section:
        raise ValueError("Missing [root] with a `children = [...]` key")

    children = root_section["children"]
    if isinstance(children, str):
        children = [c.strip() for c in children.split(",")]

    html = ""
    for child in children:
        if child in tree:
            html += parse_element(child, tree[child], tree)
        else:
            html += str(child)
    return html


def write_html(toml_path: Path):
    html = toml_to_html(toml_path)
    output_file = toml_path.with_suffix(".html")
    output_file.write_text(html)
    print(f"Generated: {output_file}")




# cookie points to myself for this


def manpage():
    content = """
WEB4(1)                 General Commands Manual                WEB4(1)

NAME
    web4 -  The future of the internet.

            Just kidding. This revolutionary software enables you to
            transpile TOML to HTML. Yep, it's Web4.

SYNOPSIS
    web4 FILE.toml [--serve] [--watch]
    web4 --man

DESCRIPTION
    This utility parses a structured TOML file describing an HTML
    hierarchy and outputs valid HTML.

    It supports children nesting, tag attributes like id/class, and
    falls back to text when no tag is defined.

OPTIONS
    --serve
        Serve the resulting HTML using Python's HTTP server on port 8080.

    --watch
        Watch the TOML file for changes. Automatically regenerates
        HTML on save.

    --man
        Show this manpage and exit.

SYNTAX
    - The [root] section is required and defines the top node.
    - Each section with a name (e.g., [body], [div.2]) becomes an HTML tag.
    - The "children" key defines nested content.
    - Use arrays like children = ["p", "div#main"]
    - If a string has no matching section, it's rendered as raw text.
    - Sections named like div#id or div.class are translated to <div id="...">.

EXAMPLES
    A minimal TOML input:

        [root]
        children = ["html"]

        [html]
        children = "head, body"

        [head]
        children = ["title"]

        [title]
        children = ["Hello"]

        [body]
        children = ["p"]

        [p]
        children = ["Welcome ", "strong", "!"]

        [strong]
        children = ["friend"]

    Produces:

        <html>
          <head>
            <title>Hello</title>
          </head>
          <body>
            <p>Welcome <strong>friend</strong>!</p>
          </body>
        </html>

AUTHOR
    Written for fun by smv. Don't ask me who fun is.
""".strip()

    lines = textwrap.dedent(content).splitlines()
    term_height = shutil.get_terminal_size((80, 24)).lines - 2
    i = 0

    while i < len(lines):
        for _ in range(term_height):
            if i >= len(lines):
                break
            print(lines[i])
            i += 1
        if i < len(lines):
            try:
                input("\n--More-- (Press Enter to continue, Ctrl+C to exit)")
                print()
            except KeyboardInterrupt:
                break


parser = argparse.ArgumentParser(description="Convert TOML layout to HTML.")
if len(sys.argv) == 1 or "--man" in sys.argv or "--help" in sys.argv:
    manpage()
    sys.exit(0)
parser.add_argument("files", nargs="+", help="Input TOML file(s)")
parser.add_argument("--serve", action="store_true", help="Serve the resulting HTML")
parser.add_argument(
    "--watch",
    action="store_true",
    help="Watch TOML file for changes and rebuild on change",
)

args = parser.parse_args()

for f in args.files:
    path = Path(f)
    write_html(path)

    if args.serve and args.watch:
        # Watch and serve
        from threading import Thread

        Thread(target=serve_file, args=(path.with_suffix(".html"),), daemon=True).start()
        watch_file(path)
    elif args.serve:
        serve_file(path.with_suffix(".html"))
    elif args.watch:
        watch_file(path)

