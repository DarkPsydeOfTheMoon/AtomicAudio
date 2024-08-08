from ...Descriptors import STANDARD_DESCRIPTORS
from .Base import CounterBase

Counter = CounterBase.extended_with(*STANDARD_DESCRIPTORS)
