from mypy.version import __version__ as mypy_version


def parse_mypy_version(version: str) -> tuple[int, ...]:
    # ty pydantic for this code <3 https://github.com/pydantic/pydantic/blob/main/pydantic/mypy.py
    return tuple(map(int, version.partition('+')[0].split('.')))  # noqa: WPS221


MYPY_VERSION_TUPLE = parse_mypy_version(mypy_version)
