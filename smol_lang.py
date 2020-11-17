import copy
from dataclasses import dataclass
import re
from typing import Any, List, Dict

class SmolNode:
    pass

@dataclass
class HTML(SmolNode):
    value: str

@dataclass
class SmolVar(SmolNode):
    value: str

@dataclass
class For(SmolNode):
    element: str
    iterator: SmolNode
    body: SmolNode

@dataclass
class Seq(SmolNode):
    first: SmolNode
    rest: SmolNode

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
    for statement, next_html in zip(*[iter(statements)]*2):
        if statement.trim().startsWith('for'):
            # Parse out the parts of the loop. Explode if we can't.
            match = re.split(r'for (.+?) in (.+?)', code)
            if not match:
                raise ValueError('Malformed for loop!')
            
            # The expression needs additional parsing.
            iter_expr = SmolVar(value=match.group(2).trim())

            # Add the loop (minus a body, we'll add that later) to the stack, then the HTML.
            stack.append(For(match.group(1), iter_expr, None))
            stack.append(HTML(value=next_html))
            
        elif statement.trim() == 'endfor':
            # The loop body will be the latest thing on the stack, while the beginning of the loop
            # will be the thing just before that.
            loop_body = stack.pop()
            loop = stack.pop()

            # Let's just check to make sure we're actually ending a for loop...
            if not isinstance(loop, For):
                raise ValueError('Cannot endfor if you never started the for in the first place!')

            # Take the body node and shove it into the loop node.
            loop.body = loop_body

            # Now that it's done, we can add the loop into a sequence with whatever came before it.
            whatever_came_before_the_loop = stack.pop()
            stack.append(Seq(first=whatever_came_before_the_loop, rest=loop))

        else:
            raise ValueError('Unknown statement {{%{}%}}'.format(statement))
    
    if len(stack) > 1:
        raise Exception('Unclosed for statement!')
    
    return stack[0]

def eval_smol_template(ast: SmolNode, params: Dict[str, Any]):
    if isinstance(ast, HTML):

        return re.sub(r'{{\s*([^}\s]+)\s*}}', lambda match: str(params.get(match.group(1), match.group(0))), ast.value)

    if isinstance(ast, SmolVar):
        if ast.value not in params:
            raise Exception('{} does not exist!'.format(ast.value))
        return params[ast.value]

    if isinstance(ast, For):
        iterator = eval_smol_template(ast.iterator, params)

        if not isinstance(iterator, list):
            raise Exception('{} is not a list!'.format(ast.iterator))

        result = ''
        params = copy.copy(params)
        for value in iterator:
            params[ast.element] = value
            result += eval_smol_template(ast.body, params)
        
        return result
            

    