class UnionDescriptor:
    FUNCTION_NAME = "rw_union"

    @staticmethod
    def construct(binary_target, value, union_id, union_map, *args, **kwargs):
        new_obj = union_map[union_id]()
        binary_target.rw_obj(new_obj, *args, **kwargs)
        return new_obj

    @staticmethod
    def parse(binary_target, value, union_id, union_map, *args, **kwargs):
        binary_target.rw_obj(value, *args, **kwargs)
        return value
