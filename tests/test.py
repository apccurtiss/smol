import unittest

from lib.smol_ast import (
    Call,
    FieldAccess,
    For,
    HTML,
    IndexAccess,
    Seq,
    SmolList,
    SmolObj,
    SmolStr,
    SmolVar
)
from lib.smol_lang import (
    parse_smol_expr,
    parse_smol_file,
    eval_smol_template
)

class TestParseExpr(unittest.TestCase):
    def test_parse_var(self):
        self.assertEqual(parse_smol_expr(' foo '), SmolVar('foo'))
        self.assertEqual(parse_smol_expr(' Foo '), SmolVar('Foo'))
        self.assertEqual(parse_smol_expr(' FOO '), SmolVar('FOO'))

    def test_parse_str(self):
        self.assertEqual(parse_smol_expr(' " foo " '), SmolStr(' foo '))
        self.assertEqual(parse_smol_expr(' \' foo \' '), SmolStr(' foo '))
        self.assertEqual(parse_smol_expr(' " foo " ').value, ' foo ')

    def test_parse_field_access(self):
        field_access = parse_smol_expr(' foo . bar ')
        self.assertEqual(field_access, FieldAccess(SmolVar('foo'), 'bar'))
        self.assertRaises(Exception, parse_smol_expr, ' foo . ')
        self.assertRaises(Exception, parse_smol_expr, ' . foo')

    def test_parse_index_access(self):
        index_access = parse_smol_expr(' foo [ 1 ] ')
        self.assertEqual(index_access, IndexAccess(SmolVar('foo'), 1))
        self.assertRaises(Exception, parse_smol_expr, ' foo [ ] ')
        self.assertRaises(Exception, parse_smol_expr, ' foo [ ')
        self.assertRaises(Exception, parse_smol_expr, ' foo ] ')

    def test_parse_call(self):
        files = parse_smol_expr(' files ( foo ) ')
        self.assertEqual(files, Call(SmolVar('files'), [SmolVar('foo')]))

class TestParseFile(unittest.TestCase):
    def test_pure_html(self):
        html = (
            '<html>'
            '   <div>foo</div>'
            '</html>'
        )
        self.assertEqual(parse_smol_file(html), HTML(html))
    
    def test_substitite_html(self):
        html = (
            '<html>'
            '   <div>{{ foo }}</div>'
            '</html>'
        )
        self.assertEqual(parse_smol_file(html), HTML(html))

    def test_for_loop(self):
        html = (
            '<html>'
            '{% for link in links %}'
            '  <a href={{ link }}></a>'
            '{% endfor %}'
            '</html>'
        )
        self.assertEqual(parse_smol_file(html),
            Seq(HTML('<html>'),
            Seq(For('link', SmolVar('links'), HTML('  <a href={{ link }}></a>')),
                HTML('</html>'))))

    def test_unclosed_loop(self):
        html = (
            '<html>'
            '{% for link in links %}'
            '  <a href={{ link }}></a>'
            '</html>'
        )
        self.assertRaises(Exception, parse_smol_file, html)

    def test_unopened_loop(self):
        html = (
            '<html>'
            '  <a href={{ link }}></a>'
            '{% endfor %}'
            '</html>'
        )
        self.assertRaises(Exception, parse_smol_file, html)

    def test_malformed_loop(self):
        html = (
            '<html>'
            '{% for ??? %}'
            '  <a href={{ link }}></a>'
            '{% endfor %}'
            '</html>'
        )
        self.assertRaises(Exception, parse_smol_file, html)

    def test_nested_loops(self):
        html = (
            '<html>'
            '{% for link in links %}'
            '{% for link in links %}'
            '  <a href={{ link }}></a>'
            '{% endfor %}'
            '{% endfor %}'
            '</html>'
        )
        inner_loop = For('link', SmolVar('links'), HTML('  <a href={{ link }}></a>'))
        outer_loop = For('link', SmolVar('links'), 
            Seq(HTML(''),
            Seq(inner_loop,
                HTML(''))))
        self.assertEqual(parse_smol_file(html),
            Seq(HTML('<html>'),
            Seq(outer_loop,
                HTML('</html>'))))

class TestEval(unittest.TestCase):
    def eval(self, ast, params={}):
        # A short wrapper over eval so we don't keep passing in the same filename + parameters
        return eval_smol_template(ast, 'test_filename', params)

    def test_primatives(self):
        self.assertEqual(self.eval(SmolStr('foo')), SmolStr('foo'))
        self.assertEqual(self.eval(SmolList([SmolStr('foo'), SmolStr('bar')])), SmolList([SmolStr('foo'), SmolStr('bar')]))
        self.assertEqual(self.eval(SmolObj({'foo': SmolStr('bar')})), SmolObj({'foo': SmolStr('bar')}))
        self.assertEqual(self.eval(SmolVar('foo'), params={'foo': SmolStr('bar')}), SmolStr('bar'))
        self.assertRaises(Exception, self.eval, SmolVar('foo'))
    
    def test_HTML(self):
        test_list = SmolList([SmolStr('foo'), SmolStr('bar'), SmolStr('baz')])
        test_obj = SmolObj({ 'a': SmolStr('foo'), 'b': SmolStr('bar'), 'c': SmolStr('baz') })

        self.assertEqual(self.eval(HTML('<html></html>')), SmolStr('<html></html>'))
        self.assertEqual(self.eval(HTML('{{ x }}'), params={ 'x': SmolStr('y') }), SmolStr('y'))
        self.assertEqual(self.eval(HTML('{{ x }}'), params={ 'x': test_list }),
            SmolStr("['foo', 'bar', 'baz']"))
        self.assertEqual(self.eval(HTML('{{ x }}'), params={ 'x': test_obj }),
            SmolStr("{'a': 'foo', 'b': 'bar', 'c': 'baz'}"))
        
        self.assertRaises(Exception, self.eval, HTML('{{ x }}'), params={})

    def test_accesses(self):
        test_list = SmolList([SmolStr('foo'), SmolStr('bar'), SmolStr('baz')])
        test_obj = SmolObj({ 'a': SmolStr('foo'), 'b': SmolStr('bar'), 'c': SmolStr('baz') })

        self.assertEqual(self.eval(IndexAccess(test_list, 1)), SmolStr('bar'))
        self.assertEqual(self.eval(FieldAccess(test_obj, 'b')), SmolStr('bar'))

        self.assertRaises(Exception, self.eval, IndexAccess(test_obj, 1))
        self.assertRaises(Exception, self.eval, FieldAccess(test_list, 'b'))

    def test_seq(self):
        self.assertEqual(self.eval(Seq(SmolStr('x'), SmolStr('y'))), SmolStr('xy'))

        self.assertRaises(Exception, self.eval, Seq(SmolStr('x'), SmolList([])))
        self.assertRaises(Exception, self.eval, Seq(SmolList([]), SmolStr('x')))

    def test_for(self):
        test_list = SmolList([SmolStr('foo'), SmolStr('bar'), SmolStr('baz')])
        self.assertEqual(self.eval(For('x', test_list, SmolStr('A'))), SmolStr('AAA'))
        self.assertEqual(self.eval(For('x', test_list, HTML('{{ x }}'))), SmolStr('foobarbaz'))
        self.assertEqual(self.eval(
            For('x', test_list, For('y', test_list, HTML('{{ x }}{{ y }}')))),
            SmolStr('foofoofoobarfoobazbarfoobarbarbarbazbazfoobazbarbazbaz'))

        self.assertRaises(Exception, self.eval, For('x', SmolStr('not a list'), SmolStr('A')))

    def test_builtin_list_files(self):
        self.assertIsInstance(self.eval(Call(SmolVar('list_files'), [SmolStr('.')])), SmolList)

        self.assertRaises(Exception, self.eval, Call(SmolVar('list_files'), []))
        self.assertRaises(Exception, self.eval, Call(SmolVar('list_files'), [SmolList([])]))