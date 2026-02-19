from backend.schemas import ErrorCode


class AppError(Exception):
    def __init__(
        self,
        error_code: ErrorCode,
        user_message: str,
        developer_message: str,
        status_code: int = 400,
    ) -> None:
        super().__init__(developer_message)
        self.error_code = error_code
        self.user_message = user_message
        self.developer_message = developer_message
        self.status_code = status_code

