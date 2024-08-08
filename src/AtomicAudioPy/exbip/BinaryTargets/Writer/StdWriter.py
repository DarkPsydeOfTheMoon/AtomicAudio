from ...Descriptors import STANDARD_DESCRIPTORS
from .Base import WriterBase

Writer = WriterBase.extended_with(*STANDARD_DESCRIPTORS)
