class ArrayDescriptor:
    FUNCTION_NAME = "rw_array"

    @staticmethod
    def construct(binary_target, value, rw_func, count, *args, **kwargs):
        out = []
        for i in range(count):
            out.append(rw_func(None, *args, **kwargs))
        return out

    @staticmethod
    def parse(binary_target, value, rw_func, count, *args, **kwargs):
        if len(value) != count:
            raise IndexError(f"Length of array '{len(value)}' does not match count '{count}'")
        for i, v in enumerate(value):
            rw_func(v, *args, **kwargs)
        return value


class HeterogeneousArrayDescriptor:
    FUNCTION_NAME = "rw_heterogeneous_array"

    @staticmethod
    def construct(binary_target, value, rw_func, call_args=[]):
        out = []
        for argset in call_args:
            out.append(rw_func(None, *argset))
        return out

    @staticmethod
    def parse(binary_target, value, rw_func, call_args=[]):
        if len(value) != len(call_args):
            raise IndexError(f"Length of array '{len(value)}' does not match number of arg sets '{call_args}'")
        for i, v in enumerate(value):
            rw_func(v, *call_args[i])
        return value

