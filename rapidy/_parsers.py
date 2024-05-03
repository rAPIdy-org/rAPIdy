from typing import Any, Dict, List, Union

from multidict import MultiMapping


def parse_multi_params(
        data: Union[MultiMapping[Any], Dict[str, Any]],
        *,
        parse_as_array: bool = False,
) -> Dict[str, Union[Any, List[Any]]]:
    if parse_as_array:
        parsed_result: Dict[str, list[Any]] = {}

        for name, value in data.items():
            if name in parsed_result:
                parsed_result[name].append(value)
            else:
                parsed_result[name] = [value]

        return parsed_result

    if isinstance(data, MultiMapping):
        return dict(data)

    return data
