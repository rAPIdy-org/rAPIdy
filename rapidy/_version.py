from aiohttp import __version__


def parse_version(version: str) -> tuple[int, ...]:
    return tuple(map(int, version.partition('+')[0].split('.')))  # noqa: WPS221


AIOHTTP_VERSION_TUPLE = parse_version(__version__)
