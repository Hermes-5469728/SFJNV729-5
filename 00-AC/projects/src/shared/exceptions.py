"""AC Platform Exception Hierarchy - 异常体系"""
from fastapi import HTTPException

class APIException(HTTPException):
    def __init__(self, status_code: int, detail: str, code: str = None):
        super().__init__(status_code=status_code, detail=detail)
        self.code = code

class ModuleNotEnabled(APIException):
    def __init__(self, module_name: str):
        super().__init__(
            status_code=403,
            detail=f"Module '{module_name}' is not enabled",
            code="MODULE_NOT_ENABLED"
        )

class CrossModuleAccessDenied(APIException):
    def __init__(self, module_name: str, resource: str):
        super().__init__(
            status_code=403,
            detail=f"Module '{module_name}' cannot access core resource: {resource}",
            code="CROSS_MODULE_ACCESS_DENIED"
        )

class InsufficientData(APIException):
    def __init__(self, missing: str):
        super().__init__(
            status_code=422,
            detail=f"Insufficient data: {missing}",
            code="INSUFFICIENT_DATA"
        )
