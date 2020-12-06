'''
Smol, an unopinionated static site generator.
'''
from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
import shutil
import time
from typing import Any, Dict

import argparse
from httpwatcher import HttpWatcherServer
import jinja2
from jinja2.exceptions import TemplateError
from tornado.ioloop import IOLoop
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from lib.smol_cache import cache
from lib.smol_runtime import build_runtime

logging.basicConfig()
logging.getLogger('tornado').setLevel(logging.ERROR)


class FileLoader(jinja2.BaseLoader):
    def __init__(self, root):
        self.root = Path(root)

    def get_source(self, environment, template):
        path = self.root.joinpath(template)
        file_obj = cache.get(path)

        return file_obj.content, str(path), lambda: file_obj.updated == cache.get(path).updated


class Environment:
    params: Dict[str, Any] = {}

    def __init__(self, input_root, output_root, static_dirs):
        self.input_root = input_root
        self.output_root = output_root
        self.static_dirs = static_dirs

        self._jinja_env = jinja2.Environment(loader=FileLoader(input_root))

    def get_template(self, path: Path):
        return self._jinja_env.get_template(path)
    
    def update(self, new_params):
        self.params.update(new_params)


def build_page(filepath: Path, destination: Path, env: Environment):
    '''Builds and saves a single page.

    Params:
        filepath: Source filepath
        destination: Destination filepath
        env: Environment dictionary
    '''
    if filepath.suffix in ['.html']:
        try:
            output = env.get_template(filepath).render({
                **env.params,
                **cache.get(filepath).headers,
                **build_runtime(filepath, env.input_root)
            }).encode()
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
    '''
    for filepath in target.rglob('*'):
        if filepath.is_file() and output_path not in filepath.parents:
            destination = output_path.joinpath(filepath)
            build_page(filepath, destination, environment)


def build_observer(environment: Environment):
    class WatchHandler(FileSystemEventHandler):
        '''Rebuilds pages that get modified'''

        @staticmethod
        def _rebuild(filepath: Path):
            '''Rebuild the given path and everything that it depends on.'''
            cache.update(filepath)

            build_page(
                filepath,
                Path(environment.output_root).joinpath(filepath),
                environment)

            for dependancy in cache.get(filepath).dependancies:
                print('[*] Updating dependancy: {}'.format(dependancy))
                WatchHandler._rebuild(dependancy)


        @staticmethod
        def on_any_event(event):
            filepath = Path(event.src_path)
            if event.event_type == 'modified' and filepath in cache:
                # Skip duplicate events that are within a second of each other
                if datetime.now() - cache.get(filepath).updated > timedelta(seconds=1):
                    print(f'[*] Recompiling {filepath}')
                    WatchHandler._rebuild(filepath)


    observer = Observer()
    observer.schedule(WatchHandler(), str(environment.input_root), recursive=True)
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


def main():
    '''Parses args'''
    common = argparse.ArgumentParser()
    common.add_argument('root', nargs='?', action='store', default='.',
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
    environment = Environment(
        input_root=Path(args.root),
        output_root=Path(args.out),
        static_dirs=map(Path, args.static)
    )

    # If smol.json exists, load it.
    config_path = environment.input_root.joinpath('smol.json')
    if config_path.is_file():
        environment.update(json.loads(config_path.read_text()))

    # Create output directory.
    if environment.output_root.is_dir():
        shutil.rmtree(environment.output_root)

    for static_dir in environment.static_dirs:
        if not static_dir.is_dir():
            raise Exception('Directory does not exist: {}'.format(static_dir))

        shutil.copytree(static_dir, environment.output_root)

    # Write!
    build_site(environment.input_root, environment.output_root, environment)
    print('[*] Compilation successful')

    if args.action == 'build':
        return

    try:
        observer = build_observer(environment)
        observer.start()
        print('[*] Watching for changes...')

        if args.action == 'serve':
            server = build_server(environment.output_root, args.port, args.open_browser)
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
