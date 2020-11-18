import copy
import os
import re

from lib.smol_ast import *
from lib.smol_runtime import runtime

var_re = re.compile(r'\w+?$')
string_re = re.compile(r'[\'"](.*?)[\'"]$')
call_re = re.compile(r'(.+)\s*\(\s*(.+?)\s*\)\s*$')
field_access_re = re.compile(r'(.+)\.\s*(.\w+)$')
index_access_re = re.compile(r'(.+)\[\s*(.\d+)\s*]$')
def parse_smol_expr(code: str):
    code = code.strip()

    # Check if it's just a variable
    match = var_re.match(code)
    if match is not None:
        return SmolVar(value=code)
    
    # Check if it's a string literal
    match = string_re.match(code)
    if match is not None:
        return SmolStr(value=match.group(1))

    # Check if it's a field access
    match = field_access_re.match(code)
    if match is not None:
        return FieldAccess(obj=parse_smol_expr(match.group(1)), field=match.group(2))

    # Check if it's a index access
    match = index_access_re.match(code)
    if match is not None:
        return IndexAccess(lst=parse_smol_expr(match.group(1)), index=int(match.group(2)))

    # Check if it's a function call
    match = call_re.match(code)
    if match is not None:
        args = [parse_smol_expr(arg) for arg in match.group(2).split(',')]
        return Call(fn=parse_smol_expr(match.group(1)), args=args)

    raise Exception('Unknown expression: {}'.format(code))

def parse_smol_file(code: str):
    statements = re.split(r'{%(.*?)%}', code)

    # Because of how we split it, the statements will be in the form of:
    # 1. <regular HTML>
    # 2. {{ statement }}
    # 3. <regular HTML>
    # 4. {{ statement }}
    # 5. <regular HTML>
    # ...with alternating HTML blocks and Smol statements.
    
    # We'll start our stack off with the first HTML block...
    stack = [HTML(value=statements[0])]

    # ...then go over the rest of the list in pairs of (statement, html), if you'll pardon the
    # operator soup needed to make that happen.
    for statement, next_html in zip(*[iter(statements[1:])]*2):
        statement = statement.strip()
        if statement.startswith('for'):
            # Parse out the parts of the loop. Explode if we can't.
            match = re.match(r'for (.+?) in (.+?)$', statement)
            if not match:
                raise ValueError('Malformed for loop!')

            # The expression needs additional parsing.
            iter_expr = parse_smol_expr(match.group(2))

            # Add the loop (minus a body, we'll add that later) to the stack, then the HTML.
            stack.append(For(match.group(1), iter_expr, None))
            stack.append(HTML(value=next_html))
            
        elif statement.strip() == 'endfor':
            # The loop body will be the latest thing on the stack, while the beginning of the loop
            # will be the thing just before that.
            loop_body = stack.pop()
            loop = stack.pop()

            # Let's just check to make sure we're actually ending a for loop...
            if not isinstance(loop, For):
                raise ValueError('endfor used without a for loop.')

            # Take the body node and shove it into the loop node.
            loop.body = loop_body

            # Now that it's done, we can add the loop into a sequence with whatever came before it,
            # plus another sequence consisting of the loop and whatever HTML follows it.
            whatever_came_before_the_loop = stack.pop()
            stack.append(Seq(
                first=whatever_came_before_the_loop,
                rest=Seq(
                    first=loop,
                    rest=HTML(value=next_html))))

        else:
            raise ValueError('Unknown statement {{%{}%}}'.format(statement))
    
    if len(stack) > 1:
        raise Exception('Unclosed for statement!')
    
    return stack[0]

def to_str(node):
    if isinstance(node, SmolStr):
        return node.value
    elif isinstance(node, SmolList):
        return str([to_str(element) for element in node.elements])
    elif isinstance(node, SmolObj):
        return str({key: to_str(value) for key, value in node.fields.items()})
    else:
        raise Exception('Internal error - tried to stringify {}'.format(node))

def eval_smol_template(ast: SmolNode, filepath: str, params: Dict[str, Any]):
    if isinstance(ast, SmolStr):
        return ast
    
    if isinstance(ast, SmolList):
        return SmolList([eval_smol_template(element, filepath, params)
            for element in ast.elements])

    if isinstance(ast, SmolObj):
        return SmolObj({key: eval_smol_template(value, filepath, params)
            for key, value in ast.fields.items()})

    if isinstance(ast, Seq):
        first = eval_smol_template(ast.first, filepath, params)
        second = eval_smol_template(ast.rest, filepath, params)

        if not isinstance(first, SmolStr) or not isinstance(second, SmolStr):
            raise Exception('Internal error - this should never happen.')
        
        return SmolStr(first.value + second.value)

    if isinstance(ast, HTML):
        def parse_and_eval(match):
            expr = parse_smol_expr(match.group(1))
            replacement = eval_smol_template(expr, filepath, params)

            return to_str(replacement)

        return SmolStr(re.sub(r'{{\s*?(.+?)\s*?}}', parse_and_eval, ast.value))

    if isinstance(ast, SmolVar):
        if ast.value in runtime:
            return runtime[ast.value]

        if ast.value not in params:
            raise Exception('{} does not exist in params: {}'.format(ast.value, params))
        return params[ast.value]

    if isinstance(ast, IndexAccess):
        lst = eval_smol_template(ast.lst, filepath, params)
        if not isinstance(lst, SmolList):
            raise Exception('{} must be a list to access index {}!'.format(lst, ast.field))
        if ast.index > len(lst.elements):
            raise Exception('Index {} out of range!'.format(ast.index))
        return lst.elements[ast.index]

    if isinstance(ast, FieldAccess):
        obj = eval_smol_template(ast.obj, filepath, params)
        if not isinstance(obj, SmolObj):
            raise Exception('{} must be an object to access field {}!'.format(obj, ast.field))
        if ast.field not in obj.fields:
            raise Exception('Field {} does not exist!'.format(ast.field))
        return obj.fields[ast.field]

    if isinstance(ast, Call):
        fn = eval_smol_template(ast.fn, filepath, params)
        if not isinstance(fn, SmolFn):
            raise Exception('{} is not a function, and cannot be called!'.format(fn))
        args = [eval_smol_template(arg, filepath, params) for arg in ast.args]
        return fn.fn(*args)

    if isinstance(ast, For):
        iterator = eval_smol_template(ast.iterator, filepath, params)

        if not isinstance(iterator, SmolList):
            raise Exception('{} is not a list!'.format(ast.iterator))

        result = ''
        params = copy.copy(params)
        for element in iterator.elements:
            params[ast.element] = element
            result += eval_smol_template(ast.body, filepath, params).value
        
        return SmolStr(result)
    
    raise Exception('Internal error on AST node: {}'.format(ast))