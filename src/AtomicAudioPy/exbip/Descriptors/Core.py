import array
import struct
from ..Utilities.List import reshape_list, flatten_list, standardize_shape, total_length


class UntypedDescriptor:
    FUNCTION_NAME = "_rw_untyped"

    @staticmethod
    def construct(binary_target, value, length):
        return binary_target._rw_raw(value, length)

    @staticmethod
    def parse(binary_target, value, length):
        binary_target._rw_raw(value, length)
        return value


class TypedDescriptor:
    FUNCTION_NAME = "_rw_typed"

    @staticmethod
    def construct(binary_target, value, typecode, size, endianness):
        if endianness is None: endianness = binary_target.endianness

        serialized_value = binary_target._rw_raw(value, size)
        return struct.unpack(endianness + typecode, serialized_value)[0]

    @staticmethod
    def parse(binary_target, value, typecode, size, endianness):
        if endianness is None: endianness = binary_target.endianness

        serialized_value = struct.pack(endianness + typecode, value)
        binary_target._rw_raw(serialized_value, size)
        return value


class TypedsDescriptor:
    FUNCTION_NAME = "_rw_typeds"

    @staticmethod
    def construct(binary_target, value, typecode, size, shape, endianness):
        if endianness is None: endianness = binary_target.endianness

        shape = standardize_shape(shape)
        element_count = total_length(shape)

        serialized_value = binary_target._rw_raw(value, size*element_count)
        deserialized_value = struct.unpack(endianness + typecode*element_count, serialized_value)
        return reshape_list(deserialized_value, shape)

    @staticmethod
    def parse(binary_target, value, typecode, size, shape, endianness):
        if endianness is None: endianness = binary_target.endianness

        shape = standardize_shape(shape)
        deserialized_value = flatten_list(value, shape)
        element_count = len(deserialized_value)

        serialized_value = struct.pack(endianness + typecode*element_count, deserialized_value)
        binary_target._rw_raw(serialized_value, size*element_count)
        return value


class TypedArrayDescriptor:
    FUNCTION_NAME = "_rw_typedarray"

    @staticmethod
    def construct(binary_target, value, typecode, size, shape, endianness):
        if endianness is None: endianness = binary_target.endianness

        shape = standardize_shape(shape)
        element_count = total_length(shape)

        serialized_value = binary_target._rw_raw(value, size * element_count)
        deserialized_value = array.array(typecode)
        deserialized_value.frombytes(serialized_value)
        if endianness == ">":
            deserialized_value.byteswap()

        return reshape_list(deserialized_value, shape)

    @staticmethod
    def parse(binary_target, value, typecode, size, shape, endianness):
        if endianness is None: endianness = binary_target.endianness

        shape = standardize_shape(shape)
        flat_list = flatten_list(value, shape)
        element_count = len(flat_list)

        serialized_value = struct.pack(endianness + typecode * element_count, *flat_list)
        binary_target._rw_raw(serialized_value, size * element_count)
        return value
