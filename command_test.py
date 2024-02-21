import gdb

class BlenderPrint(gdb.Command):
  def __init__ (self):
    super().__init__ ("bp", gdb.COMMAND_USER)

  def invoke(self, arg, from_tty):
    value = gdb.parse_and_eval(arg)
    impl = value["impl_"]
    size = int(impl["size_"])
    for i in range(size):
      gdb.set_convenience_variable("a", impl)
      sub_value = gdb.parse_and_eval(f"$a->get({i})")
      print(sub_value)
      gdb.set_convenience_variable("a", None)


BlenderPrint()

class VectorPrinter:
  def __init__(self, value: gdb.Value):
    self.value = value

  def to_string(self):
    vec_begin = self.value["begin_"]
    vec_end = self.value["end_"]
    vec_capacity_end = self.value["end_"]
    vec_size = vec_end - vec_begin
    vec_capacity = vec_capacity_end - vec_begin
    return f"length: {vec_size}, capacity: {vec_capacity}"

  def children(self):
    begin = self.value["begin_"]
    end = self.value["end_"]
    size = end - begin
    for i in range(size):
      yield str(i), begin[i]

  def display_hint(self):
    return "array"

class SetPrinter:
  def __init__(self, value: gdb.Value):
    self.value = value
    self.key_type = value.type.template_argument(0)

  def to_string(self):
    size = int(self.value["occupied_and_removed_slots_"] - self.value["removed_slots_"])
    return f"Size: {size}"

  def children(self):
    slots = self.value["slots_"]["data_"]
    slots_num = int(self.value["slots_"]["size_"])
    for i in range(slots_num):
      slot = slots[i]
      slot_state = int(slot["state_"])
      is_occupied = slot_state == 1
      if is_occupied:
        key = slot["key_buffer_"].cast(self.key_type)
        yield str(i), key

  def display_hint(self):
    return "array"

class MapPrinter:
  def __init__(self, value: gdb.Value):
    self.value = value
    self.key_type = value.type.template_argument(0)
    self.value_type = value.type.template_argument(1)

  def to_string(self):
    size = int(self.value["occupied_and_removed_slots_"] - self.value["removed_slots_"])
    return f"Size: {size}"

  def children(self):
    slots = self.value["slots_"]["data_"]
    slots_num = int(self.value["slots_"]["size_"])
    for i in range(slots_num):
      slot = slots[i]
      if self.key_type.code == gdb.TYPE_CODE_PTR:
        key = slot["key_"]
        key_int = int(key)
        # The key has two special values for an empty and removed slot.
        is_occupied = key_int < 2**64 - 2
        if is_occupied:
          value = slot["value_buffer_"].cast(self.value_type)
          yield "Key", key
          yield "Value", value
      else:
        slot_state = int(slot["state_"])
        is_occupied = slot_state == 1
        if is_occupied:
          key = slot["key_buffer_"].cast(self.key_type)
          value = slot["value_buffer_"].cast(self.value_type)
          yield "Key", key
          yield "Value", value

  def display_hint(self):
    return "map"

class TypedBufferPrinter:
  def __init__(self, value: gdb.Value):
    self.value = value
    self.type = value.type.template_argument(0)
    self.size = value.type.template_argument(1)

  def children(self):
    data = self.value.cast(self.type).address
    for i in range(self.size):
      yield str(i), data[i]

  def display_hint(self):
    return "array"

class ArrayPrinter:
  def __init__(self, value: gdb.Value):
    self.value = value

  def to_string(self):
    size = self.value["size_"]
    return f"Size: {size}"

  def children(self):
    data = self.value["data_"]
    size = self.value["size_"]
    for i in range(size):
      yield str(i), data[i]

  def display_hint(self):
    return "array"

class VectorSetPrinter:
  def __init__(self, value: gdb.Value):
    self.value = value

  def get_size(self):
    return int(self.value["occupied_and_removed_slots_"] - self.value["removed_slots_"])

  def to_string(self):
    size = self.get_size()
    return f"Size: {size}"

  def children(self):
    data = self.value["keys_"]
    size = self.get_size()
    for i in range(size):
      yield str(i), data[i]

  def display_hint(self):
    return "array"

class VArrayPrinter:
  def __init__(self, value: gdb.Value):
    self.value = value

  def get_size(self):
    impl = self.value["impl_"]
    size = int(impl["size_"])
    return size

  def to_string(self):
    size = self.get_size()
    return f"Size: {size}"

  def children(self):
    size = self.get_size()
    impl = self.value["impl_"]
    for i in range(size):
      gdb.set_convenience_variable("varray_impl", impl)
      value_at_index = gdb.parse_and_eval(f"$varray_impl->get({i})")
      gdb.set_convenience_variable("varray_impl", None)
      yield str(i), value_at_index

  def display_hint(self):
    return "array"

class MathVectorPrinter:
  def __init__(self, value: gdb.Value):
    self.value = value
    self.base_type = value.type.template_argument(0)
    self.size = value.type.template_argument(1)

  def to_string(self):
    values = [str(self.get(i)) for i in range(self.size)]
    return "(" + ", ".join(values) + ")"

  def children(self):
      for i in range(self.size):
        yield str(i), self.get(i)

  def get(self, i):
    # Avoid taking pointer of value in case the pointer is not available.
    if 2 <= self.size <= 4:
      if i == 0: return self.value["x"]
      if i == 1: return self.value["y"]
      if i == 2: return self.value["z"]
      if i == 3: return self.value["w"]
    return self.value["values"][i]

  def display_hint(self):
    return "array"


class SpanPrinter:
  def __init__(self, value: gdb.Value):
    self.value = value

  def to_string(self):
    size = self.value["size_"]
    return f"Size: {size}"

  def children(self):
    data = self.value["data_"]
    size = self.value["size_"]
    for i in range(size):
      yield str(i), data[i]

  def display_hint(self):
    return "array"


class BlenderPrettyPrinters(gdb.printing.PrettyPrinter):
  def __init__(self):
    super().__init__("blender-printers")

  def __call__(self, value: gdb.Value):
    value_type = value.type
    if value_type is None:
      return None
    if value_type.code == gdb.TYPE_CODE_PTR:
      return None
    type_name = value_type.strip_typedefs().name
    if type_name is None:
      return None
    if type_name.startswith("blender::Vector<"):
      return VectorPrinter(value)
    if type_name.startswith("blender::Set<"):
      return SetPrinter(value)
    if type_name.startswith("blender::Map<"):
      return MapPrinter(value)
    if type_name.startswith("blender::MultiValueMap<"):
      return MapPrinter(value["map_"])
    if type_name.startswith("blender::TypedBuffer<"):
      return TypedBufferPrinter(value)
    if type_name.startswith("blender::Array<"):
      return ArrayPrinter(value)
    if type_name.startswith("blender::VectorSet<"):
      return VectorSetPrinter(value)
    if type_name.startswith("blender::VArray<"):
      return VArrayPrinter(value)
    if type_name.startswith("blender::VMutableArray<"):
      return VArrayPrinter(value)
    if type_name.startswith("blender::vec_struct_base<"):
      return MathVectorPrinter(value)
    if type_name.startswith("blender::Span<"):
      return SpanPrinter(value)
    if type_name.startswith("blender::MutableSpan<"):
      return SpanPrinter(value)
    return None


gdb.printing.register_pretty_printer(None, BlenderPrettyPrinters(), replace=True)
