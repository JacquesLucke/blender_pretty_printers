import gdb
from pprint import pprint
import traceback
import typing as t
import functools

nullptr = 0x0

def string_from_array(value: gdb.Value):
    assert value.type.code == gdb.TYPE_CODE_ARRAY
    assert value.type.target().sizeof == 1

    try:
        str_bytes = []
        for i in range(value.type.sizeof):
            c = value[i]
            if c == nullptr:
                break
            str_bytes.append(int(c))
    except gdb.MemoryError:
        return ""

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
    try:
        for i in range(len(display_string_prefix)):
            if ord(display_string_prefix[i]) != int(value[i]):
                return False
    except gdb.MemoryError:
        return False
    return True

def eval_function(function_name, *args: t.List[gdb.Value]):
    arg_list = []
    for arg in args:
        arg_list.append(f"({arg.type.name} *){hex(int(arg.address))}")

    arg_list_str = ", ".join(arg_list)
    expr = f"{function_name}({arg_list_str})"
    result = gdb.parse_and_eval(expr)
    return result

def DEG_is_original_id(value: gdb.Value) -> bool:
    return bool(eval_function("DEG_is_original_id", value))

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

registered_struct_printers = {}

def struct_printer(function):
    prefix = "print_"
    function_name = function.__name__
    if not function_name.startswith(prefix):
        raise Exception()
    struct_name = function_name[len(prefix):]
    registered_struct_printers[struct_name] = function
    return function

@struct_printer
def print_ID(value: gdb.Value):
    yield "Name", string_from_array(value["name"])

def lookup_enum_value(name: str):
    return int(gdb.lookup_global_symbol(name).value())

def lookup_type(name: str):
    return gdb.lookup_global_symbol(name).type

object_types = [
    ("OB_MESH", "Mesh"),
    ("OB_LAMP", "Light"),
    ("OB_CAMERA", "Camera"),
]

@struct_printer
def print_Object(value: gdb.Value):
    yield from print_ID(value["id"])
    object_type = int(value["type"])

    for enum_name, type_name in object_types:
        if object_type == lookup_enum_value(enum_name):
            yield f"{type_name} Data", value["data"].cast(lookup_type(type_name).pointer())
            break
    else:
        yield "Data", value["data"]

@struct_printer
def print_wmOperator(value: gdb.Value):
    yield "Idname", string_from_array(value["idname"])

def listbase_len(listbase: gdb.Value):
    link = listbase["first"].cast(lookup_type("LinkData").pointer())
    count = 0
    while link != nullptr:
        count += 1
        link = link["next"]
    return count

@struct_printer
def print_ListBase(value: gdb.Value):
    yield "Length", listbase_len(value)

class DisplayStringPrinter:
    def __init__(self, value):
        self.value = value

    def to_string(self):
        return extract_display_string(self.value)

class SimpleStructPrinter:
    def __init__(self, value: gdb.Value, printer):
        self.value = value
        self.printer = printer

    def children(self):
        yield make_address_item(self.value)
        for key, value in self.printer(self.value):
            yield make_debug_item(key, value)
        yield from make_raw_field_items(self.value)

class GenericIDPrinter:
    def __init__(self, value: gdb.Value):
        self.value = value

    def children(self):
        try:
            yield make_address_item(self.value)
            for key, value in print_ID(self.value["id"]):
                yield make_debug_item(key, value)
            yield from make_raw_field_items(self.value)
        except Exception as e:
            if isinstance(e, GeneratorExit):
                raise
            print(traceback.format_exc())


class BlenderPrettyPrinter(gdb.printing.PrettyPrinter):
    def __init__(self):
        super().__init__("blender_printer", [])

    def lookup_printer(self, value: gdb.Value):
        if value.type is None:
            return None
        if value.type.code == gdb.TYPE_CODE_PTR and value == nullptr:
            return None
        if is_display_string(value):
            return DisplayStringPrinter(value)
        if value.type.code == gdb.TYPE_CODE_PTR:
            target_type = value.type.target()
            if target_type is not None and target_type.name is not None:
                if target_type.name in registered_struct_printers:
                    return SimpleStructPrinter(value.dereference(), registered_struct_printers[target_type.name])
                try: fields = target_type.fields()
                except: fields = []
                if len(fields) >= 1 and fields[0].name == "id" and fields[0].type.name == "ID":
                    return GenericIDPrinter(value.dereference())
        if value.type.name in registered_struct_printers:
            return SimpleStructPrinter(value, registered_struct_printers[value.type.name])

    def __call__(self, value: gdb.Value):
        try:
            return self.lookup_printer(value)
        except:
            print(traceback.format_exc())
            return None

gdb.printing.register_pretty_printer(None, BlenderPrettyPrinter(), replace=True)
