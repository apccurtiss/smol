import json
import logging
import os
import re
import time

import argparse
from httpwatcher import HttpWatcherServer
from tornado.ioloop import IOLoop
import shutil
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from lib.smol_lang import eval_smol_template, parse_smol_file

logging.basicConfig()
logging.getLogger('tornado').setLevel(logging.ERROR)


def read_headers(text):
    """Parse headers and return the index where they end."""
    headers = {}
    end = 0
    for match in re.finditer(r'\s*<!--\s*(.+?)\s*:\s*(.+?)\s*-->\s*', text):
        if not match.group(1):
            break

        headers[match.group(1)] = match.group(2)
        end = match.end()

    return headers, end

def read_content(filename):
    """Read headers and content from a file."""
    with open(filename) as f:
        content = f.read()

    headers, end = read_headers(content)

    # Separate content from headers.
    content = content[end:]

    return headers, content

def build_page(filepath, destination, global_params):
    if filepath.endswith('html'):
        headers, content = read_content(filepath)

        global_params.update(headers)
        template = parse_smol_file(content)
        output = eval_smol_template(template, filepath, global_params).value.encode()
    else:
        with open(filepath, 'rb') as f:
            output = f.read()

    os.makedirs(os.path.dirname(destination), exist_ok=True)
    with open(destination, 'wb') as f:
        f.write(output)

def build_site(target, output_path, params):
    watchpaths = []

    for (dirpath, _dirnames, filenames) in os.walk(target):
        for filename in filenames:
            source = os.path.join(dirpath, filename)
            destination = os.path.join(output_path, source)
            build_page(source, destination, params)
            watchpaths.append(source)

    return watchpaths

def main():
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
    params = {
        'root': args.root,
        'out': args.out,
        'static_dirs': args.static,
    }

    # If smol.json exists, load it.
    if os.path.isfile(os.path.join(args.root, 'smol.json')):
        with open('smol.json') as f:
            params.update(json.loads(f.read()))

    # Create output directory.
    if os.path.isdir(params['out']):
        shutil.rmtree(params['out'])

    for static_dir in params['static_dirs']:
        if not os.path.isdir(static_dir):
            raise Exception('Directory does not exist: {}'.format(static_dir))

        shutil.copytree(static_dir, params['out'])

    # Write!
    watchpaths = build_site(params['root'], params['out'], params)
    print('[*] Compilation successful')

    # Keep watching until manually cancelled.
    class Handler(FileSystemEventHandler):
        @staticmethod
        def on_any_event(event):
            if event.event_type == 'modified' and event.src_path in watchpaths:
                print(f'[*] Recompiling {event.src_path}')
                build_page(event.src_path, os.path.join(params['out'], event.src_path), params)

    # Initialize Observer
    observer = Observer()
    observer.schedule(Handler(), params['root'], recursive=True)

    # Start the observer
    try:
        observer.start()
        print('[*] Watching for changes...')

        server = None
        if args.serve:
            host = 'localhost'
            port = 8000
            server = HttpWatcherServer(
                params['out'],
                watch_paths=[params['out']],
                host=host,
                port=port,
                watcher_interval=1.0,
                recursive=True,
                open_browser=False)
            server.listen()
            print('[*] Serving from http://{}:{}'.format(host, port))

        IOLoop.current().start()
    except KeyboardInterrupt:
        observer.stop()
        if server:
            server.shutdown()

    observer.join()


if __name__ == '__main__':
    main()
