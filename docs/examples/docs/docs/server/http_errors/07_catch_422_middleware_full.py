from http import HTTPStatus
from logging import getLogger
from typing import Any
from pydantic import BaseModel
from rapidy import Rapidy, run_app
from rapidy.http import (
    get,
    middleware,
    Request,
    Response,
    StreamResponse,
    HTTPValidationFailure,
    HTTPClientError,
    HTTPInternalServerError,
    HTTPException,
)
from rapidy.typedefs import CallNext, ValidationErrorList

logger = getLogger(__name__)

class ServerResponse(BaseModel):
    message: str = 'Success'
    result: Any | None = None
    errors: ValidationErrorList | None = None

@middleware
async def error_catch_middleware(
        request: Request,
        call_next: CallNext,
        response: Response,
) -> StreamResponse | ServerResponse:
    try:
        return await call_next(request)

    except HTTPValidationFailure as validation_failure_error:
        validation_errors = validation_failure_error.validation_errors
        logger.debug('Validation error while processing: `%s request: %s', str(request.rel_url), validation_errors)
        response.set_status(validation_failure_error.status)
        return ServerResponse(message='Validation error', errors=validation_errors)

    except HTTPClientError as client_error:  # all other `4xx' errors
        logger.info('Client error while processing: %s request: %s', str(request.rel_url), client_error)
        response.set_status(client_error.status)
        return ServerResponse(message=client_error.reason)

    except HTTPInternalServerError as server_error:
        logger.info('Internal error - server raise HTTPInternalServerError: %s', server_error)
        response.set_status(server_error.status)
        return ServerResponse(message=server_error.reason)

    except HTTPException as unhandled_http_error:  # all other unhandled http-errors
        raise unhandled_http_error

    except Exception as unhandled_error:
        logger.exception('Internal error while processing `%s` error: %s', str(request.rel_url), unhandled_error)
        response.set_status(HTTPStatus.INTERNAL_SERVER_ERROR)
        return ServerResponse(message='Internal server error')

@get('/')
async def handler() -> ServerResponse:
    return ServerResponse(result={'hello': 'rapidy'})

app = Rapidy(middlewares=[error_catch_middleware], http_route_handlers=[handler])

if __name__ == '__main__':
    run_app(app)