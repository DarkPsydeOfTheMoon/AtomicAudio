class Descriptor:
    def __init__(self): pass

    @staticmethod
    def construct(binary_target, value, *args, **kwargs):
        raise NotImplementedError

    @staticmethod
    def parse(binary_target, value, *args, **kwargs):
        raise NotImplementedError

