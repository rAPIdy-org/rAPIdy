async def extract_body_json(request: Request, body_field_info: Body) -> Optional[DictStrAny]:
    if not request.body_exists:
        return None

    return await request.json(loads=body_field_info.json_decoder)