from typing import Any, Dict, List, Union

from multidict import MultiMapping


def parse_multi_params(
    data: Union[MultiMapping[Any], Dict[str, Any]],
) -> Dict[str, Union[Any, List[Any]]]:
    parsed_result: Dict[str, Any] = {}

    for name, value in data.items():
        if name in parsed_result:
            if isinstance(parsed_result[name], list):
                parsed_result[name].append(value)
            else:
                parsed_result[name] = [parsed_result[name], value]
        else:
            parsed_result[name] = value

    return parsed_result
