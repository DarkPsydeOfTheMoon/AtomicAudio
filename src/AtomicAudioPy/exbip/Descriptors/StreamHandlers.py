class AssertEOFDescriptor:
    FUNCTION_NAME = "assert_eof"

    class NotAtEOFError(Exception):
        def __init__(self):
            super().__init__("Finished reading the stream before EOF was reached")

    @classmethod
    #def construct(cls, binary_target):
    #    if binary_target.peek_bytestream(1) != b'':
    #        raise binary_target.NotAtEOFError
    def construct(cls):
        if cls.peek_bytestream(1) != b'':
            raise Exception("Finished reading the stream before EOF was reached")

    @classmethod
    #def parse(cls, binary_target):
    def parse(cls):
        pass


class AlignmentDescriptor:
    FUNCTION_NAME = "align"

    class UnexpectedPaddingError(Exception):
        def __init__(self, expected, received):
            super().__init__(f"Expected padding with a value of '{expected}', received '{received}'")

    @staticmethod
    def _alignment_size(position, alignment):
        return (alignment - (position % alignment)) % alignment

    @classmethod
    def construct(cls, binary_target, position, alignment, pad_value=b'\x00'):
        size = cls._alignment_size(position, alignment)
        align_data = binary_target._rw_untyped(None, size)
        expected_pad = pad_value*(size//len(pad_value))
        if align_data != expected_pad:
            raise cls.UnexpectedPaddingError(expected_pad, align_data)

    @classmethod
    def parse(cls, binary_target, position, alignment, pad_value=b'\x00'):
        size = cls._alignment_size(position, alignment)
        if not (size/len(pad_value)).is_integer():
            raise ValueError(f"Alignment requires an offset increment of {size} bytes, "
                             f"but the padding value '{pad_value}' is {len(pad_value)} bytes in size, "
                             f"which would require a non-integer number of pad values")
        binary_target._rw_untyped(pad_value * (size // len(pad_value)), size)
