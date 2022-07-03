import gdb

class BlenderPrint(gdb.Command):
  def __init__ (self):
    super().__init__ ("bp", gdb.COMMAND_USER)

  def invoke(self, arg, from_tty):
    value = gdb.parse_and_eval(arg)
    slots = value["slots_"]["data_"]
    slots_num = int(value["slots_"]["size_"])
    for i in range(slots_num):
      slot = slots[i]
      slot_state = int(slot["state_"])
      is_occupied = slot_state == 1
      if is_occupied:
        key = slot["key_buffer_"].cast(value.type.template_argument(0))
        print(key)


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

class BlenderPrettyPrinters(gdb.printing.PrettyPrinter):
  def __init__(self):
    super().__init__("blender-printers")

  def __call__(self, value: gdb.Value):
    value_type = value.type
    if value_type is None:
      return None
    if value_type.code == gdb.TYPE_CODE_PTR:
      return None
    type_name = value_type.name
    if type_name is None:
      return None
    if type_name.startswith("blender::Vector<"):
      return VectorPrinter(value)
    if type_name.startswith("blender::Set<"):
      return SetPrinter(value)
    if type_name.startswith("blender::Map<"):
      return MapPrinter(value)
    if type_name.startswith("blender::TypedBuffer<"):
      return TypedBufferPrinter(value)
    if type_name.startswith("blender::Array<"):
      return ArrayPrinter(value)
    if type_name.startswith("blender::VectorSet<"):
      return VectorSetPrinter(value)
    return None


gdb.printing.register_pretty_printer(None, BlenderPrettyPrinters(), replace=True)
