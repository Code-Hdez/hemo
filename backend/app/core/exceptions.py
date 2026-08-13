from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class ApplicationError(Exception):
    def __init__(self, detail: object, status_code: int = 400) -> None:
        super().__init__(str(detail))
        self.detail = detail
        self.status_code = status_code


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApplicationError)
    async def handle_application_error(
        _request: Request, exc: ApplicationError
    ) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
