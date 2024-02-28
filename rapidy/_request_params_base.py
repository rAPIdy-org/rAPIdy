from enum import Enum


class ValidateType(str, Enum):
    no_validate = 'no_validate'
    schema = 'schema'
    param = 'param'

    def is_no_validate(self) -> bool:
        return self == self.no_validate

    def is_schema(self) -> bool:
        return self == self.schema

    def is_param(self) -> bool:
        return self == self.param


class ParamType(str, Enum):
    path = 'path'
    query = 'query'
    header = 'header'
    cookie = 'cookie'
    body = 'body'
