from abc import ABC, abstractmethod
from typing import Any, Dict, List, Type, Union

from pydantic import BaseModel, create_model

from rapidy.constants import PYDANTIC_IS_V1
from rapidy.typedefs import DictStrAny, ErrorWrapper, LocStr, ValidationErrorList

ErrorModel: Type[BaseModel] = create_model('Model')
RequestErrorModel: Type[BaseModel] = create_model('Request')


class ClientBaseError(ABC, ValueError):
    type: str
    msg_template: str

    def __init__(self, *_: Any, **error_ctx: Any) -> None:
        self._err_msg = self.msg_template.format(**error_ctx)

    @abstractmethod
    def get_error_info(
            self,
            loc: LocStr,
    ) -> Dict[str, Any]:  # pragma: no cover
        raise NotImplementedError


if PYDANTIC_IS_V1:
    from pydantic.error_wrappers import ValidationError

    class ClientError(ClientBaseError, ABC):
        def get_error_info(
                self,
                loc: LocStr,
        ) -> Dict[str, Any]:
            return {
                'loc': loc,
                'msg': self._err_msg,
                'type': self.type,
            }

    class RequiredFieldIsMissing(ClientError):
        type = 'value_error.missing'
        msg_template = 'field required'

    def regenerate_error_with_loc(
            *,
            errors: List[Any],
            loc: LocStr,
    ) -> List[Dict[str, Any]]:
        return [
            {**err, 'loc': loc + err.get('loc', ())}
            for err in normalize_errors(errors)
        ]

    def normalize_error_wrapper(error: ErrorWrapper) -> List[DictStrAny]:
        return ValidationError(errors=[error], model=RequestErrorModel).errors()

    def normalize_list(errors: List[Any]) -> ValidationErrorList:
        use_errors: ValidationErrorList = []
        for error in errors:
            if isinstance(error, ErrorWrapper):
                new_errors = normalize_error_wrapper(error)
                use_errors.extend(new_errors)
            elif isinstance(error, list):
                use_errors.extend(normalize_errors(error))
            else:
                use_errors.append(error)
        return use_errors

    def normalize_errors(errors: Union[Any, List[Any]]) -> ValidationErrorList:
        if isinstance(errors, list):
            return normalize_list(errors)
        elif isinstance(errors, ErrorWrapper):
            return normalize_error_wrapper(errors)
        return [errors]

else:
    from pydantic import ValidationError
    from pydantic_core import InitErrorDetails, PydanticCustomError

    class ClientError(ClientBaseError, ABC):  # type: ignore[no-redef]
        def get_error_info(
                self,
                loc: LocStr,
        ) -> Dict[str, Any]:
            err = PydanticCustomError(self.type, self._err_msg)
            err_details = InitErrorDetails(type=err, loc=loc, input=input)
            return ValidationError.from_exception_data(
                title='',
                line_errors=[err_details],
                hide_input=True,
            ).errors()[0]

    class RequiredFieldIsMissing(ClientError):  # type: ignore[no-redef]
        type = 'missing'
        msg_template = 'Field required'

    def regenerate_error_with_loc(
            *,
            errors: List[Any],
            loc: LocStr,
    ) -> List[Dict[str, Any]]:
        return [
            {**err, 'loc': loc + err.get('loc', ())}
            for err in errors
        ]

    def error_dict_pop_useless_keys(error: Dict[str, Any]) -> None:  # TODO: need advice - not sure about this
        error.pop('url', None)
        error.pop('input', None)

    def normalize_errors(errors: Union[Any, List[Any]]) -> ValidationErrorList:
        if isinstance(errors, list):
            for error in errors:
                error_dict_pop_useless_keys(error)
            return errors

        error_dict_pop_useless_keys(errors)
        return [errors]
