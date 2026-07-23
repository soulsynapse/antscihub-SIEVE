from __future__ import annotations


class SieveError(Exception):
    def __init__(self, code: str, message: str, **context: object) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.context = {k: v for k, v in context.items() if v is not None}

    def as_dict(self) -> dict[str, object]:
        return {"code": self.code, "message": self.message, "context": self.context}
