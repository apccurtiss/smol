'''
Smol, an unopinionated static site generator.
'''
from datetime import datetime, timedelta
import json
import logging
import os
from pathlib import Path
import re
import shutil
import sys
import time
from typing import Any, Dict

import argparse
from httpwatcher import HttpWatcherServer
from tornado.ioloop import IOLoop
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from jinja2 import Template

logging.basicConfig()
logging.getLogger('tornado').setLevel(logging.ERROR)


Environment: Dict[str, Any]


def separate_headers(file_content: str):
    """Parse headers and return the index where they end."""
    headers = {}
    end = 0
    for match in re.finditer(r'\s*<!--\s*(.+?)\s*:\s*(.+?)\s*-->\s*', file_content):
        if not match.group(1):
            break

        headers[match.group(1)] = match.group(2)
        end = match.end()

    return headers, file_content[end:]


def build_page(filepath: Path, destination: Path, environment: Environment):
    '''Builds and saves a single page.

    Params:
        filepath: Source filepath
        destination: Destination filepath
        environment: Param dict
    '''
    if filepath.suffix in ['.html']:
        headers, content = separate_headers(filepath.read_text())
        
        output = Template(content).render({**environment, **headers}).encode()
    else:
        output = filepath.read_bytes()

    destination.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(output)


def build_site(target: Path, output_path: Path, environment: Environment):
    '''Recursively builds a given directory.

    Params:
        target: Source directory
        output_path: Destination directory
        environment: Param dict

    Returns:
        A list of the files built
    '''
    watchpaths = []

    for filepath in target.glob('**/*'):
        destination = output_path.joinpath(filepath)
        build_page(filepath, destination, environment)
        watchpaths.append(filepath)

    return watchpaths

def main():
    '''Parses args'''
    parser = argparse.ArgumentParser(description='Build a website!')
    parser.add_argument('-r', '--root', nargs='?', action='store', default='.',
                        help='source root directory')
    parser.add_argument('--serve', action='store_true', default=False,
                        help='serve the completed site from a local webserver')
    parser.add_argument('-o', '--out', action='store', nargs='?', default='./_site',
                        help='output folder')
    parser.add_argument('-s', '--static', action='store', nargs='*', default=[],
                        help='static directories will be copied without modification')

    args = parser.parse_args()

    # Use argument parameters.
    environment = {
        'root': Path(args.root),
        'out': Path(args.out),
        'static_dirs': map(Path, args.static),
    }

    # If smol.json exists, load it.
    config_path = args.root.joinpath('smol.json')
    if config_path.is_file():
        environment.update(json.loads(config_path.read_text()))

    # Create output directory.
    if environment['out'].is_dir():
        shutil.rmtree(environment['out'])

    for static_dir in environment['static_dirs']:
        if not static_dir.is_dir():
            raise Exception('Directory does not exist: {}'.format(static_dir))

        shutil.copytree(static_dir, environment['out'])

    # Write!
    watchpaths = build_site(environment['root'], environment['out'], environment)
    print('[*] Compilation successful')

    class WatchHandler(FileSystemEventHandler):
        '''Rebuilds pages that get modified'''
        @staticmethod
        def on_any_event(event):
            if event.event_type == 'modified' and event.src_path in watchpaths:
                # Skip duplicate events that are within a second of each other
                if datetime.now() - cache.get(event.src_path).updated < timedelta(seconds=1):
                    return

                print(f'[*] Recompiling {event.src_path}')
                build_page(event.src_path, os.path.join(environment['out'], event.src_path), environment)

    # Initialize Observer
    observer = Observer()
    observer.schedule(WatchHandler(), environment['root'], recursive=True)

    # Start the observer
    try:
        observer.start()
        print('[*] Watching for changes...')

        server = None
        if args.serve:
            host = 'localhost'
            port = 8000
            server = HttpWatcherServer(
                environment['out'],
                watch_paths=[environment['out']],
                host=host,
                port=port,
                watcher_interval=1.0,
                recursive=True,
                open_browser=False)
            server.listen()
            print('[*] Serving from http://{}:{}'.format(host, port))

            IOLoop.current().start()

        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('[*] Shutting down...')
        observer.stop()
        if server:
            server.shutdown()

    observer.join()
    sys.exit(0)


if __name__ == '__main__':
    main()
