try:
    return await handler(request)
except HTTPValidationFailure as validation_failure_error:
    errors = validation_failure_error.validation_errors
    ...