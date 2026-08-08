import logging

from rapidy.http import (
    HTTPException,
    HTTPInternalServerError,
    HTTPValidationFailure,
    middleware,
    Request,
    StreamResponse,
)
from rapidy.typedefs import CallNext, Middleware


def error_catch_middleware(logger: logging.Logger) -> Middleware:
    @middleware
    async def _impl(request: Request, call_next: CallNext) -> StreamResponse:
        try:
            return await call_next(request)

        except HTTPValidationFailure as validation_failure_error:
            validation_errors = validation_failure_error.validation_errors
            logger.debug(
                "Validation error while processing: `%s request: %s",
                str(request.rel_url),
                validation_errors,
            )
            raise validation_failure_error

        except HTTPInternalServerError as server_error:
            logger.info(
                "Internal error - server raise HTTPInternalServerError: %s",
                server_error,
            )
            raise server_error

        except HTTPException as unhandled_http_error:  # all other unhandled http-errors
            raise unhandled_http_error

        except Exception as unhandled_error:
            logger.exception(f"Internal error while processing `{request.rel_url!s}`")
            raise HTTPInternalServerError from unhandled_error

    return _impl
