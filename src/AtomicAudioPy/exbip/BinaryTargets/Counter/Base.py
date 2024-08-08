from ..Interface import IParseTarget
from ..Interface import ISequentialStreamTarget


class CounterBase(IParseTarget, ISequentialStreamTarget):
    def __init__(self):
        super().__init__()
        self.offset = 0

    def _raw_untyped(self, value, length):
        self.offset += length
