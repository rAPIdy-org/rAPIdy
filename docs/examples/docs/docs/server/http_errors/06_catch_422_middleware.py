from logging import getLogger
from rapidy.http import (
    middleware, Request, StreamResponse, HTTPValidationFailure, HTTPInternalServerError, HTTPException,
)
from rapidy.typedefs import CallNext

logger = getLogger(__name__)


@middleware
async def error_catch_middleware(
        request: Request,
        call_next: CallNext,
) -> StreamResponse:
    try:
        return await call_next(request)

    except HTTPValidationFailure as validation_failure_error:
        validation_errors = validation_failure_error.validation_errors
        logger.debug('Ошибка валидации: `%s request: %s`', str(request.rel_url), validation_errors)
        raise validation_failure_error

    except HTTPInternalServerError as server_error:
        logger.info('Внутренняя ошибка сервера: %s', server_error)
        raise server_error

    except HTTPException as unhandled_http_error:
        raise unhandled_http_error

    except Exception as unhandled_error:
        logger.exception('Ошибка при обработке `%s`: %s', str(request.rel_url), unhandled_error)
        raise HTTPInternalServerError