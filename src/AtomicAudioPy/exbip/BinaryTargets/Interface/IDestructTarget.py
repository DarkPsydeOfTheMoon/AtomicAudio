from .Base import IBinaryTarget, OperatorType


class IDestructTarget(IBinaryTarget):
    @property
    def operator_type(self):
        return OperatorType.DESTRUCTLIKE
