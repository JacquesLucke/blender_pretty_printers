import gdb
from pprint import pprint
import traceback
import typing as t
import functools
from dataclasses import dataclass

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

    try:
        return bytes(str_bytes).decode('utf8')
    except UnicodeDecodeError:
        return "<utf8 decode error>"

# Some random string.
dummy_type_prefix = "=*?="

def print_traceback(value):
    '''Print the traceback to stdout. Otherwise it might not be printed in some cases in vscode.'''
    print(traceback.format_exc())

@dataclass
class DummyValue:
    pass

@dataclass
class JustText(DummyValue):
    text: str

    def to_string(self):
        return self.text

def make_dummy_value_printer(value):
    value_str = repr(value)
    return gdb.Value(dummy_type_prefix + value_str)

def extract_dummy_value_printer(value: gdb.Value):
    if value.type.code != gdb.TYPE_CODE_ARRAY:
        return None
    if value.type.sizeof < len(dummy_type_prefix):
        return None
    if value.type.target().sizeof != 1:
        # Expected char type.
        return None

    try:
        for i in range(len(dummy_type_prefix)):
            if ord(dummy_type_prefix[i]) != value[i]:
                # Prefix did not match.
                return None
    except gdb.MemoryError:
        return None

    try:
        str_bytes = []
        for i in range(len(dummy_type_prefix), value.type.sizeof):
            str_bytes.append(int(value[i]))
    except gdb.MemoryError:
        return None

    try:
        value_str = bytes(str_bytes).decode("utf8")
    except UnicodeDecodeError:
        # Most likely the memory is corrupted.
        return None

    try:
        dummy_value = eval(value_str)
    except:
        print_traceback()
        return None

    return dummy_value

def make_debug_item(key: t.Union[int, str], value: t.Union[str, int, bool, float, gdb.Value, DummyValue]):
    key = f"[{str(key)}]"
    if isinstance(value, str):
        value = JustText(value)
    if isinstance(value, DummyValue):
        value = make_dummy_value_printer(value)
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

@functools.lru_cache
def lookup_enum_value(name: str):
    return int(gdb.lookup_global_symbol(name).value())

@functools.lru_cache
def lookup_type(name: str):
    base_name = name.replace("*", "").strip()
    base_type = gdb.lookup_global_symbol(base_name).type
    for _ in range(name.count("*")):
        base_type = base_type.pointer()
    return base_type

def cast(value: gdb.Value, type_name: str) -> gdb.Value:
    return value.cast(lookup_type(type_name))

def reinterpret_cast(value: gdb.Value, type_name: str) -> gdb.Value:
    return value.reinterpret_cast(lookup_type(type_name))

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
            yield f"{type_name} Data", cast(value["data"], type_name + "*")
            break
    else:
        yield "Data", value["data"]

@struct_printer
def print_wmOperator(value: gdb.Value):
    yield "Idname", string_from_array(value["idname"])

def get_pointer_chain(first: gdb.Value, pointer_name: str):
    elements = []
    elements_set = set()
    element = first
    while True:
        if element == nullptr:
            break
        if element in elements_set:
            break
        elements.append(element)
        elements_set.add(element)
        element = element[pointer_name]
    return elements

def get_full_double_linked_list(any_link: gdb.Value):
    previous_elements = get_pointer_chain(any_link, "prev")
    next_elements = get_pointer_chain(any_link, "next")
    return previous_elements[::-1] + next_elements[1:]

def get_listbase_elements(listbase: gdb.Value):
    first = cast(listbase["first"], "LinkData *")
    return get_pointer_chain(first, "next")

@dataclass
class TypedListBase(DummyValue):
    any_link_address: int
    data_type: str

    def children(self):
        try:
            any_link = reinterpret_cast(gdb.Value(self.any_link_address), self.data_type + "*")
            all_links = get_full_double_linked_list(any_link)
            yield from (make_debug_item(i, link) for i, link in enumerate(all_links))
        except Exception as e:
            if isinstance(e, GeneratorExit):
                raise
            print(traceback.format_exc())

@struct_printer
def print_ListBase(listbase: gdb.Value):
    try:
        links = get_listbase_elements(listbase)
    except gdb.MemoryError:
        yield "Length", "<memory error>"
        return

    yield "Length", len(links)
    for i, link in enumerate(links):
        yield i, str(link)

@struct_printer
def print_ModifierData(modifier: gdb.Value):
    yield "Name", string_from_array(modifier["name"])
    # Seems to lead to infinite loops currently.
    # yield "Modifier List", TypedListBase(int(modifier.address), "ModifierData")

@struct_printer
def print_bConstraint(constraint: gdb.Value):
    yield "Name", string_from_array(constraint["name"])

class SimpleStructPrinter:
    def __init__(self, value: gdb.Value, printer):
        self.value = value
        self.printer = printer

    def children(self):
        try:
            yield make_address_item(self.value)
            for key, value in self.printer(self.value):
                yield make_debug_item(key, value)
            yield from make_raw_field_items(self.value)
        except Exception as e:
            if isinstance(e, GeneratorExit):
                raise
            print(traceback.format_exc())

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
        if value.type.code == gdb.TYPE_CODE_PTR:
            return None
        dummy_value_printer = extract_dummy_value_printer(value)
        if dummy_value_printer is not None:
            return dummy_value_printer
        if value.type.code == gdb.TYPE_CODE_TYPEDEF:
            if value.type.name is not None:
                if value.type.name in registered_struct_printers:
                    return SimpleStructPrinter(value, registered_struct_printers[value.type.name])
                try: fields = value.type.fields()
                except: fields = []
                if len(fields) >= 1 and fields[0].name == "id" and fields[0].type.name == "ID":
                    return GenericIDPrinter(value)
        if value.type.name in registered_struct_printers:
            return SimpleStructPrinter(value, registered_struct_printers[value.type.name])

    def __call__(self, value: gdb.Value):
        try:
            return self.lookup_printer(value)
        except:
            print(traceback.format_exc())
            return None

gdb.printing.register_pretty_printer(None, BlenderPrettyPrinter(), replace=True)
