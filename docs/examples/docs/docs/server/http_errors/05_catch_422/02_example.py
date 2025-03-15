try:
    return await handler(request)
except HTTPUnprocessableEntity:
    ...