def check(cond: bool, message: str, *args) -> None:
    if not cond:
        raise AssertionError(str.format(message, *args))
