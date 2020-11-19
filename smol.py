'''
Smol, an unopinionated static site generator.
'''
from datetime import datetime, timedelta
import json
import logging
import os
import shutil
import sys
import time

import argparse
from httpwatcher import HttpWatcherServer
from tornado.ioloop import IOLoop
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from lib.smol_cache import cache
from lib.smol_lang import eval_smol_template, parse_smol_file

logging.basicConfig()
logging.getLogger('tornado').setLevel(logging.ERROR)


def build_page(filepath, destination, global_params):
    '''Builds and saves a single page.

    Params:
        filepath: Source filepath
        destination: Destination filepath
        global_params: Param dict
    '''
    file_obj = cache.get(filepath, invalidate=True)

    if file_obj.is_html:
        global_params.update(file_obj.headers)
        template = parse_smol_file(file_obj.content)
        output = eval_smol_template(template, filepath, global_params).value.encode()
    else:
        output = file_obj.content

    os.makedirs(os.path.dirname(destination), exist_ok=True)
    with open(destination, 'wb') as outfile:
        outfile.write(output)

def build_site(target, output_path, params):
    '''Recursively builds a given directory.

    Params:
        target: Source directory
        output_path: Destination directory
        params: Param dict

    Returns:
        A list of the files built
    '''
    watchpaths = []

    for (dirpath, _dirnames, filenames) in os.walk(target):
        for filename in filenames:
            source = os.path.join(dirpath, filename)
            destination = os.path.join(output_path, source)
            build_page(source, destination, params)
            watchpaths.append(source)

    return watchpaths

def main():
    '''Parses args and runs accordingly'''
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
        with open('smol.json') as infile:
            params.update(json.loads(infile.read()))

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

    class WatchHandler(FileSystemEventHandler):
        '''Rebuilds pages that get modified'''
        @staticmethod
        def on_any_event(event):
            if event.event_type == 'modified' and event.src_path in watchpaths:
                # Skip duplicate events that are within a second of each other
                if datetime.now() - cache.get(event.src_path).updated < timedelta(seconds=1):
                    return

                print(f'[*] Recompiling {event.src_path}')
                build_page(event.src_path, os.path.join(params['out'], event.src_path), params)

    # Initialize Observer
    observer = Observer()
    observer.schedule(WatchHandler(), params['root'], recursive=True)

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
