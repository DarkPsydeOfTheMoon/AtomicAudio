from .Base import IBinaryTarget, OperatorType


class IConstructTarget(IBinaryTarget):
    @property
    def operator_type(self):
        return OperatorType.CONSTRUCTLIKE

    @staticmethod
    def _get_rw_method(descriptor):
        return descriptor.construct
