#!/usr/bin/env python

import datetime
import functools
import json
import logging
import os
import re
import sys

import argparse
import shutil

from smol_lang import eval_smol_template, parse_smol_file

logging.basicConfig()

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
    print('Building {} -> {}'.format(filepath, destination))


    if filepath.endswith('html'):
        headers, content = read_content(filepath)
        print('Parsed headers: {}'.format(headers))

        global_params.update(headers)
        template = parse_smol_file(content)
        output = eval_smol_template(template, global_params).encode()
    else:
        with open(filepath, 'rb') as f:
            output = f.read()

    os.makedirs(os.path.dirname(destination), exist_ok=True)
    with open(destination, 'wb') as f:
        f.write(output)

def build_site(target, output_path, params):
    print('Building site from {} into {}'.format(target, output_path))
    for (dirpath, _dirnames, filenames) in os.walk(target):
        for filename in filenames:
            source = os.path.join(dirpath, filename)
            destination = os.path.join(output_path, source)
            build_page(source, destination, params)

def main():
    parser = argparse.ArgumentParser(description='Build a website!')
    parser.add_argument('target', action='store', help='target folder', default='.')

    args = parser.parse_args()

    # Default parameters.
    params = {
        'target': args.target,
        'out': './_site',
        'static_dir': './static',
    }

    # If smol.json exists, load it first.
    if os.path.isfile('smol.json'):
        with open('smol.json') as f:
            params.update(json.loads(f.read()))

    # Create output directory.
    if os.path.isdir(params['out']):
        shutil.rmtree(params['out'])

    if os.path.isdir(params['static_dir']):
        shutil.copytree(params['static_dir'], params['out'])

    # Write!
    build_site(params['target'], params['out'], params)


if __name__ == '__main__':
    main()
