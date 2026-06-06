class MonCashError(Exception):
    """Raised for all MonCashConnect API errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 0,
        context: dict | None = None,
        *,
        code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.context = context
        self.code = code
