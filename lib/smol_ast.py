from dataclasses import dataclass
from typing import Any, Callable, Dict, List

class SmolNode:
    pass

@dataclass
class HTML(SmolNode):
    value: str

@dataclass
class SmolStr(SmolNode):
    value: str

@dataclass
class SmolList(SmolNode):
    elements: List[SmolNode]

@dataclass
class SmolObj(SmolNode):
    fields: Dict[str, SmolNode]

@dataclass
class SmolFn(SmolNode):
    fn: Callable[[Any], Any]

@dataclass
class SmolVar(SmolNode):
    value: str

@dataclass
class FieldAccess(SmolNode):
    obj: SmolNode
    field: str

@dataclass
class IndexAccess(SmolNode):
    lst: SmolNode
    index: int

@dataclass
class Call(SmolNode):
    fn: SmolNode
    args: List[SmolNode]

@dataclass
class For(SmolNode):
    element: str
    iterator: SmolNode
    body: SmolNode

@dataclass
class Seq(SmolNode):
    first: SmolNode
    rest: SmolNode