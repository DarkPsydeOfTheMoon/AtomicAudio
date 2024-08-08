from .Traits import ReadableTrait
from .Traits import WriteableTrait
from ..BinaryTargets.Reader import Reader
from ..BinaryTargets.Writer import Writer


class Serializable(ReadableTrait(Reader),
                   WriteableTrait(Writer)):
    pass
