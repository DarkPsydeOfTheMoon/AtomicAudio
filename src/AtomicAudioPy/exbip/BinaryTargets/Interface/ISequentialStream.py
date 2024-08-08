from .Base import IBinaryTarget


class ISequentialStreamTarget(IBinaryTarget):
    # Pointer calc interface
    def _act_on_offset_impl(self, actual_offset, expected_offset, msg=None, formatter=None):
        if actual_offset != expected_offset:
            if formatter is not None:
                actual_offset   = formatter(actual_offset)
                expected_offset = formatter(expected_offset)
            prefix = msg + ': ' if msg is not None else ''
            raise ValueError(f"{prefix}Stream position is at {actual_offset}, but was expected to be {expected_offset}")

    def act_on_relative_offset(self, expected_offset, base_position, msg=None, formatter=None):
        actual_offset = self.relative_tell(base_position)
        if actual_offset != expected_offset:
            if formatter is not None:
                base_position   = formatter(base_position)
                actual_offset   = formatter(actual_offset)
                expected_offset = formatter(expected_offset)
            prefix = msg + ': ' if msg is not None else ''
            raise ValueError(f"{prefix}Stream position is at {actual_offset}, but was expected to be {expected_offset} (relative to stream offset {base_position})")
