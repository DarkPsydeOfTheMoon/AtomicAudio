import array
import struct


def define_primitive(name, typecode):
    elem_size = struct.calcsize(typecode)

    class PrimitiveDescriptor:
        FUNCTION_NAME = f"rw_{name}"

        @staticmethod
        def construct(binary_target, value, endianness=None):
            return binary_target._rw_typed(value, typecode, elem_size, endianness)

        @staticmethod
        def parse(binary_target, value, endianness=None):
            binary_target._rw_typed(value, typecode, elem_size, endianness)
            return value

    PrimitiveDescriptor.__name__ = name

    return PrimitiveDescriptor


def define_primitive_array(name, typecode):
    elem_size = struct.calcsize(typecode)

    class PrimitiveArrayDescriptor:
        FUNCTION_NAME = f"rw_{name}"

        @staticmethod
        def construct(binary_target, value, shape, endianness=None):
            return binary_target._rw_typedarray(value, typecode, elem_size, shape, endianness)

        @staticmethod
        def parse(binary_target, value, shape, endianness=None):
            binary_target._rw_typedarray(value, typecode, elem_size, shape, endianness)
            return value

    PrimitiveArrayDescriptor.__name__ = name

    return PrimitiveArrayDescriptor


int8    = define_primitive("int8", "b")
int16   = define_primitive("int16", "h")
int32   = define_primitive("int32", "i")
int64   = define_primitive("int64", "q")
uint8   = define_primitive("uint8", "B")
uint16  = define_primitive("uint16", "H")
uint32  = define_primitive("uint32", "I")
uint64  = define_primitive("uint64", "Q")
float16 = define_primitive("float16", "e")
float32 = define_primitive("float32", "f")
float64 = define_primitive("float64", "d")

PRIMITIVE_DESCRIPTORS = [int8, int16, int32, int64,
                         uint8, uint16, uint32, uint64,
                         float16, float32, float64]

int8s    = define_primitive_array("int8s", "b")
int16s   = define_primitive_array("int16s", "h")
int32s   = define_primitive_array("int32s", "i")
int64s   = define_primitive_array("int64s", "q")
uint8s   = define_primitive_array("uint8s", "B")
uint16s  = define_primitive_array("uint16s", "H")
uint32s  = define_primitive_array("uint32s", "I")
uint64s  = define_primitive_array("uint64s", "Q")
# float16 unsupported by array.array
float32s = define_primitive_array("float32s", "f")
float64s = define_primitive_array("float64s", "d")


class float16s:
    FUNCTION_NAME = "rw_float16s"

    @staticmethod
    def construct(binary_target, value, shape, endianness='<'):
        return binary_target._rw_typeds(value, 'e', 2, shape, endianness)

    @staticmethod
    def parse(binary_target, value, shape, endianness='<'):
        binary_target._rw_typeds(value, 'e', 2, shape, endianness)
        return value


PRIMITIVE_ARRAY_DESCRIPTORS = [int8s, int16s, int32s, int64s,
                               uint8s, uint16s, uint32s, uint64s,
                               float16s, float32s, float64s]
