from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Type

from pydantic import BaseModel, create_model

from rapidy.constants import PYDANTIC_IS_V1
from rapidy.typedefs import DictStrAny, ErrorWrapper, LocStr, ValidationErrorList

ErrorModel: Type[BaseModel] = create_model('Model')
RequestErrorModel: Type[BaseModel] = create_model('Request')


class ClientBaseError(ABC, ValueError):
    """Base class for client errors in the Rapidy framework.

    This is the base class for all client-side errors. It includes a message template
    and an abstract method for getting error information.

    Attributes:
        type (str): The type of the error.
        msg_template (str): The message template used for error messages.
    """

    type: str
    msg_template: str

    def __init__(self, *_: Any, **error_ctx: Any) -> None:
        """Initialize a ClientBaseError instance.

        Args:
            error_ctx (Any): The context for formatting the error message.
        """
        self._err_msg = self.msg_template.format(**error_ctx)

    @abstractmethod
    def get_error_info(
        self,
        loc: LocStr,
    ) -> Dict[str, Any]:  # pragma: no cover
        """Abstract method to get detailed error information.

        Args:
            loc (LocStr): The location where the error occurred.

        Returns:
            Dict[str, Any]: A dictionary containing error information.

        Raises:
            NotImplementedError: This method must be implemented by subclasses.
        """
        raise NotImplementedError


if PYDANTIC_IS_V1:
    from pydantic.error_wrappers import ValidationError

    class ClientError(ClientBaseError, ABC):
        """Client error for handling Pydantic validation errors in the Rapidy framework.

        This error handles the error information when validation errors occur.
        """

        def get_error_info(
            self,
            loc: LocStr,
        ) -> Dict[str, Any]:
            """Get error information for this client error.

            Args:
                loc (LocStr): The location where the error occurred.

            Returns:
                Dict[str, Any]: A dictionary containing error information.
            """
            return {
                'loc': loc,
                'msg': self._err_msg,
                'type': self.type,
            }

    class RequiredFieldIsMissingError(ClientError):
        """Error raised when a required field is missing in Pydantic validation.

        Attributes:
            type (str): The error type.
            msg_template (str): The error message template.
        """

        type = 'value_error.missing'
        msg_template = 'field required'

    def regenerate_error_with_loc(
        *,
        errors: List[Any],
        loc: LocStr,
    ) -> List[Dict[str, Any]]:
        """Regenerate errors with a specified location.

        Args:
            errors (List[Any]): The list of errors to modify.
            loc (LocStr): The new location to associate with the errors.

        Returns:
            List[Dict[str, Any]]: A list of errors with updated locations.
        """
        return [{**err, 'loc': loc + err.get('loc', ())} for err in normalize_errors(errors)]

    def normalize_error_wrapper(error: ErrorWrapper) -> List[DictStrAny]:
        """Normalize a single error wrapper to a list of error information.

        Args:
            error (ErrorWrapper): The error wrapper to normalize.

        Returns:
            List[DictStrAny]: A list of dictionaries containing normalized error information.
        """
        return ValidationError(errors=[error], model=RequestErrorModel).errors()

    def normalize_list(errors: List[Any]) -> ValidationErrorList:
        """Normalize a list of errors.

        Args:
            errors (List[Any]): The list of errors to normalize.

        Returns:
            ValidationErrorList: A list of normalized errors.
        """
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

    def normalize_errors(errors: Any | List[Any]) -> ValidationErrorList:
        """Normalize a list or single error.

        Args:
            errors (Union[Any, List[Any]]): The error or list of errors to normalize.

        Returns:
            ValidationErrorList: A list of normalized errors.
        """
        if isinstance(errors, list):
            return normalize_list(errors)
        if isinstance(errors, ErrorWrapper):
            return normalize_error_wrapper(errors)
        return [errors]

else:
    from pydantic import ValidationError
    from pydantic_core import InitErrorDetails, PydanticCustomError

    class ClientError(ClientBaseError, ABC):  # type: ignore[no-redef]
        """Client error for handling Pydantic validation errors in the Rapidy framework for Pydantic V2."""

        def get_error_info(
            self,
            loc: LocStr,
        ) -> Dict[str, Any]:
            """Get error information for this client error.

            Args:
                loc (LocStr): The location where the error occurred.

            Returns:
                Dict[str, Any]: A dictionary containing error information.
            """
            err = PydanticCustomError(self.type, self._err_msg)
            err_details = InitErrorDetails(type=err, loc=loc, input=input)
            return ValidationError.from_exception_data(
                title='',
                line_errors=[err_details],
                hide_input=True,
            ).errors()[0]

    class RequiredFieldIsMissingError(ClientError):  # type: ignore[no-redef]
        """Error raised when a required field is missing in Pydantic V2 validation.

        Attributes:
            type (str): The error type.
            msg_template (str): The error message template.
        """

        type = 'missing'
        msg_template = 'Field required'

    def regenerate_error_with_loc(
        *,
        errors: List[Any],
        loc: LocStr,
    ) -> List[Dict[str, Any]]:
        """Regenerate errors with a specified location.

        Args:
            errors (List[Any]): The list of errors to modify.
            loc (LocStr): The new location to associate with the errors.

        Returns:
            List[Dict[str, Any]]: A list of errors with updated locations.
        """
        return [{**err, 'loc': loc + err.get('loc', ())} for err in errors]

    def error_dict_pop_useless_keys(error: Dict[str, Any]) -> None:
        """Remove unnecessary keys from the error dictionary.

        Args:
            error (Dict[str, Any]): The error dictionary to clean up.
        """
        # TODO: need advice - not sure about this  # noqa: FIX002
        error.pop('url', None)
        error.pop('input', None)

    def normalize_errors(errors: Any | List[Any]) -> ValidationErrorList:
        """Normalize a list or single error, removing unnecessary keys for Pydantic V2.

        Args:
            errors (Union[Any, List[Any]]): The error or list of errors to normalize.

        Returns:
            ValidationErrorList: A list of normalized errors.
        """
        if isinstance(errors, list):
            for error in errors:
                error_dict_pop_useless_keys(error)
            return errors

        error_dict_pop_useless_keys(errors)
        return [errors]
