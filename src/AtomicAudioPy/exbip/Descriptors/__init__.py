from .Core import UntypedDescriptor, TypedDescriptor, TypedsDescriptor, TypedArrayDescriptor
from .Arrays import ArrayDescriptor, HeterogeneousArrayDescriptor
from .Object import ObjectDescriptor, ObjectsDescriptor
from .Primitives import PRIMITIVE_DESCRIPTORS, PRIMITIVE_ARRAY_DESCRIPTORS
from .StreamHandlers import AssertEOFDescriptor, AlignmentDescriptor
from .String import BytestringDescriptor, CBytestringDescriptor, StringDescriptor, CStringDescriptor
from .Union import UnionDescriptor


STANDARD_DESCRIPTORS = [
    UntypedDescriptor,
    TypedDescriptor,
    TypedsDescriptor,
    TypedArrayDescriptor,
    *PRIMITIVE_DESCRIPTORS,
    *PRIMITIVE_ARRAY_DESCRIPTORS,
    ArrayDescriptor,
    HeterogeneousArrayDescriptor,
    AssertEOFDescriptor,
    AlignmentDescriptor,
    ObjectDescriptor,
    ObjectsDescriptor,
    BytestringDescriptor,
    CBytestringDescriptor,
    StringDescriptor,
    CStringDescriptor,
    UnionDescriptor
]
