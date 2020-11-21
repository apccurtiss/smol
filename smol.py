'''
Smol, an unopinionated static site generator.
'''
from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
import re
import shutil
import time
from typing import Any, Dict

import argparse
from httpwatcher import HttpWatcherServer
from jinja2 import Template
from jinja2.exceptions import TemplateError
from tornado.ioloop import IOLoop
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from lib.smol_cache import cache

logging.basicConfig()
logging.getLogger('tornado').setLevel(logging.ERROR)

Environment = Dict[str, Any]

# def separate_headers(file_content: str):
#     """Parse headers and return the index where they end."""
#     headers = {}
#     end = 0
#     for match in re.finditer(r'\s*<!--\s*(.+?)\s*:\s*(.+?)\s*-->\s*', file_content):
#         if not match.group(1):
#             break

#         headers[match.group(1)] = match.group(2)
#         end = match.end()

#     return headers, file_content[end:]


def build_page(filepath: Path, destination: Path, env: Environment, invalidate_cache=False):
    '''Builds and saves a single page.

    Params:
        filepath: Source filepath
        destination: Destination filepath
        env: Environment dictionary
        invalidate_cache: Use cached version of the file
    '''
    if filepath.suffix in ['.html']:
        cached_file = cache.get(filepath, invalidate_cache)
        # headers, content = separate_headers(filepath.read_text())

        try:
            output = Template(cached_file.content).render(
                {**env, **cached_file.headers}).encode()
        except TemplateError as err:
            print('[!] Unable to compile {}: {}'.format(filepath, err))
            return
    else:
        output = filepath.read_bytes()

    destination.parent.mkdir(parents=True, exist_ok=True)
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
    watchpaths = {}

    for filepath in target.rglob('*'):
        if filepath.is_file() and output_path not in filepath.parents:
            destination = output_path.joinpath(filepath)
            build_page(filepath, destination, environment)
            watchpaths[filepath] = datetime.now()

    return watchpaths


def build_observer(watchpaths: Dict[str, datetime], environment: Environment):
    class WatchHandler(FileSystemEventHandler):
        '''Rebuilds pages that get modified'''
        @staticmethod
        def on_any_event(event):
            filepath = Path(event.src_path)
            if event.event_type == 'modified' and filepath in watchpaths:
                # Skip duplicate events that are within a second of each other
                if datetime.now() - watchpaths.get(filepath) < timedelta(seconds=1):
                    return

                print(f'[*] Recompiling {filepath}')
                build_page(
                    filepath,
                    Path(environment['out']).joinpath(filepath),
                    environment,
                    invalidate_cache=True)
                watchpaths[filepath] = datetime.now()

    observer = Observer()
    observer.schedule(WatchHandler(), str(environment['root']), recursive=True)
    return observer


def build_server(path, port, open_browser):
    server = HttpWatcherServer(
        path,
        watch_paths=[path],
        host='localhost',
        port=port,
        watcher_interval=1.0,
        recursive=True,
        open_browser=open_browser)

    return server


def list_files(filepath: str):
    def parse_file(filepath):
        print({
            'url': str(filepath),
            **cache.get(filepath).headers
        })
        return {
            'url': str(filepath),
            **cache.get(filepath).headers
        }

    return [parse_file(f) for f in Path(filepath).glob('*') if f.is_file()]


def main():
    '''Parses args'''
    common = argparse.ArgumentParser()
    common.add_argument('-r', '--root', nargs='?', action='store', default='.',
                        help='source root directory')
    common.add_argument('-o', '--out', action='store', nargs='?', default='./_site',
                        help='output folder')
    common.add_argument('-s', '--static', action='store', nargs='*', default=[],
                        help='static directories that will be copied without modification')

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(title='commands', dest='action')

    _build = subparsers.add_parser('build', add_help=False, parents=[common])
    _watch = subparsers.add_parser('watch', add_help=False, parents=[common])
    serve = subparsers.add_parser('serve', add_help=False, parents=[common])

    serve.add_argument('--open-browser', action='store_true', default=False,
                       help='automatically open a browser tab')
    serve.add_argument('-p', '--port', action='store', type=int, default=8000,
                       help='custom port number')

    args = parser.parse_args()

    # Use argument parameters.
    environment = {
        'root': Path(args.root),
        'out': Path(args.out),
        'static_dirs': map(Path, args.static),
        'list_files': list_files
    }

    # If smol.json exists, load it.
    config_path = environment['root'].joinpath('smol.json')
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

    if args.action == 'build':
        return

    try:
        observer = build_observer(watchpaths, environment)
        observer.start()
        print('[*] Watching for changes...')

        if args.action == 'serve':
            server = build_server(environment['out'], args.port, args.open_browser)
            server.listen()
            print('[*] Serving from http://localhost:{}'.format(args.port))

            IOLoop.current().start()

        else:
            server = None
            while True:
                time.sleep(1)

    except KeyboardInterrupt:
        print('[*] Shutting down...')
        observer.stop()
        if server:
            server.shutdown()

    observer.join()


if __name__ == '__main__':
    main()
