import enum
import functools
import os


class OperatorType(enum.Enum):
    CONSTRUCTLIKE = 0
    PARSELIKE     = 1
    DESTRUCTLIKE  = 2


class OffsetManager:
    def __init__(self, rw):
        self._rw = rw

    def __enter__(self):
        self._rw.push_origin()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._rw.pop_origin()


class EndiannessManager:
    def __init__(self, rw, new_endianness):
        self._rw = rw
        self._prev_endianness = rw.endianness
        self.new_endianness = new_endianness

    def __enter__(self):
        self._rw.endianness = self.new_endianness

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._rw.endianness = self._prev_endianness


class IBinaryTarget:
    __slots__ = ("_reference_offset_stack", "endianness")

    def __init__(self, endianness="<"):
        self._reference_offset_stack = [0]
        self.endianness = endianness
    
    #########################
    # CLASS EXTENSION FUNCS #
    #########################
    @classmethod
    def extended_with(cls, *bit_descriptors, **kw_bit_descriptors):
        class DerivedClass(cls):
            pass

        for desc in bit_descriptors:
            setattr(cls, desc.FUNCTION_NAME, functools.partialmethod(cls._get_rw_method(desc)))
        for nm, desc in kw_bit_descriptors:
            setattr(cls, nm,                 functools.partialmethod(cls._get_rw_method(desc)))

        return DerivedClass

    #######################
    # TYPE-CHECKING FUNCS #
    #######################
    @property
    def operator_type(self):
        raise NotImplementedError

    @property
    def is_constructlike(self):
        return self.operator_type == OperatorType.CONSTRUCTLIKE

    @property
    def is_parselike(self):
        return self.operator_type == OperatorType.PARSELIKE

    @property
    def is_destructlike(self):
        return self.operator_type == OperatorType.DESTRUCTLIKE

    ######################
    # ABSTRACT INTERFACE #
    ######################
    # Read/Write interface
    @staticmethod
    def _get_rw_method(descriptor):
        """Retrieves the appropriate read/write method from a descriptor."""
        raise NotImplementedError

    def _rw_raw(self, value, length):
        """
        Performs a target-defined action on an iterable object of bytes, and a length.
        Depending on the target, some or all of the arguments may be unused.
        """
        return NotImplementedError

    ####################
    # STREAM INTERFACE #
    ####################
    # Seeks - separate to a 'Seekable' interface?
    def global_seek(self, offset, whence=os.SEEK_SET):
        raise NotImplementedError
    
    def relative_global_seek(self, offset, base_position, whence=os.SEEK_SET):
        if whence==os.SEEK_SET:
            return self.global_seek(offset + base_position, whence)
        else:
            return self.global_seek(offset, whence)
    
    def seek(self, offset, whence=os.SEEK_SET):
        return self.relative_global_seek(offset, self.current_origin(), whence)
    
    def relative_seek(self, offset, base_position, whence=os.SEEK_SET):
        return self.seek(offset, base_position, whence)
    
    # Tells - separate to a 'Tellable' interface?
    def global_tell(self):
        raise NotImplementedError

    def relative_global_tell(self, base_position):
        return self.global_tell() - base_position

    def tell(self):
        return self.relative_global_tell(self.current_origin())

    def relative_tell(self, base_position):
        return self.tell() - base_position

    # Offset calculation interface
    def _act_on_offset_impl(self, actual_offset, expected_offset, formatter):
        raise NotImplementedError

    def act_on_offset(self, value, msg=None, formatter=None):
        return self._act_on_offset(self.tell(), value, msg, formatter)

    def act_on_relative_offset(self, value, base_position, msg=None, formatter=None):
        return self._act_on_offset(self.relative_tell(base_position), value, msg, formatter)

    # Stream origin manipulation
    def current_origin(self):
        return self._reference_offset_stack[-1]

    def push_origin(self):
        self._reference_offset_stack.append(self.global_tell())
        
    def pop_origin(self):
        self._reference_offset_stack.pop()

    def relative_origin(self):
        return OffsetManager(self)

    # Stream endianness
    def as_littleendian(self):
        return EndiannessManager(self, "<")
    
    def as_bigendian(self):
        return EndiannessManager(self, ">")

    ########################
    # VALIDATION UTILITIES #
    ########################
    def assert_equal(self, input_value, reference_value, value_name=None, formatter=None):
        if input_value != reference_value:
            if formatter is not None:
                input_value = formatter(input_value)
                reference_value = formatter(reference_value)

            if value_name is None:
                msg = f"Expected input to be '{reference_value}', but it was '{input_value}'"
            else:
                msg = f"Expected input '{value_name}' to be '{reference_value}', but it was '{input_value}'"
            raise ValueError(msg)
