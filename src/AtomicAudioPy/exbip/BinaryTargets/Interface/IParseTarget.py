from .Base import IBinaryTarget, OperatorType


class IParseTarget(IBinaryTarget):
    @property
    def operator_type(self):
        return OperatorType.PARSELIKE

    @staticmethod
    def _get_rw_method(descriptor):
        return descriptor.parse
