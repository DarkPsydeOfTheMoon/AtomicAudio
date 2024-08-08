class BytestringDescriptor:
    FUNCTION_NAME = "rw_bytestring"

    @staticmethod
    def construct(binary_target, value, length):
        return binary_target._rw_untyped(value, length)

    @staticmethod
    def parse(binary_target, value, length):
        return binary_target._rw_untyped(value, length)


class StringDescriptor:
    FUNCTION_NAME = "rw_string"

    @staticmethod
    def construct(binary_target, value, length, encoding="ascii"):
        return binary_target._rw_untyped(value, length).decode(encoding)

    @staticmethod
    def parse(binary_target, value, length, encoding="ascii"):
        return binary_target._rw_untyped(value.encode(encoding), length)


def deserialize_cbytestring(binary_target, terminator=b'\x00'):
    out = b''
    cur_byte = b''
    while cur_byte != terminator:
        out += cur_byte
        cur_byte = binary_target._rw_untyped(None, 1)
    return out


def serialize_cbytestring(binary_target, value, terminator=b'\x00'):
    binary_target._rw_untyped(value + terminator, len(value) + len(terminator))


class CBytestringDescriptor:
    FUNCTION_NAME = "rw_cbytestring"

    @staticmethod
    def construct(binary_target, value, terminator=b'\x00'):
        return deserialize_cbytestring(binary_target, terminator)

    @staticmethod
    def parse(binary_target, value, terminator=b'\x00'):
        serialize_cbytestring(binary_target, value, terminator)
        return value


class CStringDescriptor:
    FUNCTION_NAME = "rw_cstring"
    @staticmethod
    def construct(binary_target, value, terminator=b'\x00', encoding="ascii"):
        return deserialize_cbytestring(binary_target, terminator).decode(encoding)

    @staticmethod
    def parse(binary_target, value, terminator=b'\x00', encoding="ascii"):
        serialize_cbytestring(binary_target, value.encode(encoding), terminator)
        return value
