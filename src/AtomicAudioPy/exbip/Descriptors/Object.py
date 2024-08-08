from ..Utilities.List import reshape_list, iter_flatten_list, standardize_shape, total_length


class ObjectDescriptor:
    FUNCTION_NAME = "rw_obj"

    @staticmethod
    def construct(binary_target, value,
                  constructor=None, *args, **kwargs):
        if constructor is not None:
            value = constructor()
        value.__rw_hook__(binary_target, *args, **kwargs)
        return value

    @staticmethod
    def parse(binary_target, value,
                    constructor=None, *args, **kwargs):
        value.__rw_hook__(binary_target, *args, **kwargs)
        return value


class ObjectsDescriptor:
    FUNCTION_NAME = "rw_objs"
    
    @staticmethod
    def construct(binary_target, value,
                  constructor, shape, *args, **kwargs):
        out = []
        
        shape = standardize_shape(shape)
        element_count = total_length(shape)
        
        for _ in range(element_count):
            out.append(binary_target.rw_obj(value, constructor, *args, **kwargs))
        
        return reshape_list(out, shape)

    @staticmethod
    def parse(binary_target, value,
                  constructor, shape, *args, **kwargs):
        
        shape = standardize_shape(shape)
        
        for obj in iter_flatten_list(value, shape):
            binary_target.rw_obj(obj, constructor, *args, **kwargs)
        
        return value
