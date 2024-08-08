from ...Descriptors import STANDARD_DESCRIPTORS
from .Base import ReaderBase

Reader = ReaderBase.extended_with(*STANDARD_DESCRIPTORS)
