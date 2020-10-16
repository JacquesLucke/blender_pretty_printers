from __future__ import annotations
import enum
import typing as t

# Does not actually exist.
class TypeCode:
    pass

TYPE_CODE_PTR: TypeCode
TYPE_CODE_ARRAY: TypeCode
TYPE_CODE_STRUCT: TypeCode
TYPE_CODE_UNION: TypeCode
TYPE_CODE_ENUM: TypeCode
TYPE_CODE_FLAGS: TypeCode
TYPE_CODE_FUNC: TypeCode
TYPE_CODE_INT: TypeCode
TYPE_CODE_FLT: TypeCode
TYPE_CODE_VOID: TypeCode
TYPE_CODE_SET: TypeCode
TYPE_CODE_RANGE: TypeCode
TYPE_CODE_STRING: TypeCode
TYPE_CODE_BITSTRING: TypeCode
TYPE_CODE_ERROR: TypeCode
TYPE_CODE_METHOD: TypeCode
TYPE_CODE_METHODPTR: TypeCode
TYPE_CODE_MEMBERPTR: TypeCode
TYPE_CODE_REF: TypeCode
TYPE_CODE_RVALUE_REF: TypeCode
TYPE_CODE_CHAR: TypeCode
TYPE_CODE_BOOL: TypeCode
TYPE_CODE_COMPLEX: TypeCode
TYPE_CODE_TYPEDEF: TypeCode
TYPE_CODE_NAMESPACE: TypeCode
TYPE_CODE_DECFLOAT: TypeCode
TYPE_CODE_INTERNAL_FUNCTION: TypeCode

class Objfile:
    pass

class Type:
    alignof: int
    sizeof: int
    code: TypeCode
    dynamic: bool
    name: t.Optional[str]
    tag: t.Optional[str]
    objfile: t.Optional[Objfile]

    def fields(self) -> t.List[Field] :
        pass

    def array(self, n1, n2=None) -> Type:
        pass

    def vector(self, n1, n2=None) -> Type:
        pass

    def const(self) -> Type:
        pass

    def volatile(self) -> Type:
        pass

    def unqualified(self) -> Type:
        pass

    def range(self):
        pass

    def reference(self) -> Type:
        pass

    def pointer(self) -> Type:
        pass

    def strip_typedefs(self) -> Type:
        pass

    def target(self) -> Type:
        pass

    def template_argument(self, n, block=None) -> t.Union[Type, Value]:
        pass

    def optimized_out(self) -> Value:
        pass

class Field:
    bitpos: int
    enumval: int
    name: t.Optional[str]
    artificial: bool
    is_base_class: bool
    bitsize: int
    type: Type
    parent_type: Type

class Value:
    type: Type
    address: t.Optional[Value]
    is_optimized_out: bool
    dynamic_type: Type
    is_lazy: bool

    def dereference(self) -> Value:
        pass

    def referenced_value(self) -> Value:
        pass

    def reference_value(self) -> Value:
        pass

    def const_value(self) -> Value:
        pass

    def format_string(self, *args, **kwargs) -> str:
        pass

    def string(self, encoding=None, errors=None, length=None) -> str:
        pass

    def lazy_string(self, encoding=None, length=None) -> str:
        pass

    def fetch_lazy(self):
        pass

    def cast(self, type: Type) -> Value:
        pass

    def reinterpret_cast(self, type: Type) -> Value:
        pass


def lookup_type(name: str, block=None) -> Type:
    pass

def lookup_global_symbol(name: str):
    pass

def execute(command: str, from_tty=None, to_string=None):
    pass

def parse_and_eval(expression: str) -> gdb.Value:
    pass

class MemoryError(Exception):
    pass
