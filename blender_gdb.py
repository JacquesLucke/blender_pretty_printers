import gdb
from pprint import pprint
import traceback
import typing as t

nullptr = 0x0

def string_from_array(value: gdb.Value):
    assert value.type.code == gdb.TYPE_CODE_ARRAY
    assert value.type.target().sizeof == 1

    str_bytes = []
    for i in range(value.type.sizeof):
        c = value[i]
        if c == nullptr:
            break
        str_bytes.append(int(c))

    return bytes(str_bytes).decode('utf8')

# Some random string.
display_string_prefix = "#?*="

def make_display_string(text: str):
    return gdb.Value(display_string_prefix + text)

def extract_display_string(value: gdb.Value):
    assert is_display_string(value)
    str_bytes = [int(value[i]) for i in range(len(display_string_prefix), value.type.sizeof)]
    return bytes(str_bytes).decode("utf8")

def is_display_string(value: gdb.Value):
    if value.type.code != gdb.TYPE_CODE_ARRAY:
        return False
    if value.type.sizeof < len(display_string_prefix):
        return False
    target = value.type.target()
    if target.sizeof != 1:
        return False
    for i in range(len(display_string_prefix)):
        if ord(display_string_prefix[i]) != int(value[i]):
            return False
    return True

def DEG_is_original_id(value: gdb.Value) -> bool:
    expr = f"DEG_is_original_id((ID *){value.address})"
    result = gdb.parse_and_eval(expr)
    return bool(result)

def make_debug_item(key: t.Union[int, str], value: t.Union[str, int, bool, float, gdb.Value]):
    key = f"[{str(key)}]"
    if isinstance(value, str):
        value = make_display_string(value)
    return key, value

def make_address_item(value: gdb.Value):
    return make_debug_item("Address", hex(value.address))

def make_raw_field_items(value: gdb.Value):
    for field in value.type.fields():
        yield field.name, value[field.name]

class IDPrinter:
    def __init__(self, value: gdb.Value):
        self.value = value

    def children(self):
        yield make_address_item(self.value)
        yield make_debug_item("Name", string_from_array(self.value["id"]["name"]))
        yield make_debug_item("Is Original", DEG_is_original_id(self.value["id"]))
        yield from make_raw_field_items(self.value)

class WmOperatorPrinter:
    def __init__(self, value):
        self.value = value

    def children(self):
        yield make_address_item(self.value)
        yield make_debug_item("Idname", string_from_array(self.value["idname"]))
        yield from make_raw_field_items(self.value)

class DisplayStringPrinter:
    def __init__(self, value):
        self.value = value

    def to_string(self):
        return extract_display_string(self.value)

def is_pointer_to_struct(value: gdb.Value, struct_name: str):
    if value.type.code == gdb.TYPE_CODE_PTR:
        if value != nullptr:
            if value.type.target().name == struct_name:
                return True
    return False

class BlenderPrettyPrinter(gdb.printing.PrettyPrinter):
    def __init__(self):
        super().__init__("blender_printer", [])

    def __call__(self, value: gdb.Value):
        ...
        if is_display_string(value):
            return DisplayStringPrinter(value)

        if is_pointer_to_struct(value, "Object"):
            return IDPrinter(value.dereference())
        if is_pointer_to_struct(value, "wmOperator"):
            return WmOperatorPrinter(value.dereference())

gdb.printing.register_pretty_printer(None, BlenderPrettyPrinter(), replace=True)
