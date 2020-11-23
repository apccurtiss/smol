from pathlib import Path
import unittest

from lib.smol_runtime import build_runtime
from lib.smol_cache import SmolFileCache


class TestRuntime(unittest.TestCase):
    runtime = build_runtime(Path('tests/test_files/index.html'), Path('tests/'))

    def test_split(self):
        split_fn = self.runtime['split']

        self.assertListEqual(split_fn('foo,bar,', ','), ['foo', 'bar', ''])
        self.assertListEqual(split_fn('foo', 'bar'), ['foo'])
    
    def test_list_files_uses_relative_path(self):
        list_files_fn = self.runtime['list_files']

        # We set the root path to be tests/ on creation, so it should list from there
        self.assertListEqual(list_files_fn('.'), [{'url': Path('test_files/index.html')}])
        self.assertListEqual(list_files_fn('posts'), [
            {
                'url': Path('test_files/posts/post_1.html'),
                'title': 'My first blog post',
                'date': '11-21-2020' },
            {
                'url': Path('test_files/posts/post_2.html'),
                'title': 'My second blog post',
                'date': '11-22-2020'
            }])
        self.assertListEqual(list_files_fn('../test_files/posts'), [
            {
                'url': Path('test_files/posts/post_1.html'),
                'title': 'My first blog post',
                'date': '11-21-2020' },
            {
                'url': Path('test_files/posts/post_2.html'),
                'title': 'My second blog post',
                'date': '11-22-2020'
            }])
    
    def test_list_files_cannot_escape_project_root(self):
        list_files_fn = self.runtime['list_files']

        self.assertRaises(Exception, list_files_fn, '../..')