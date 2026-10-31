from argparse import ArgumentParser, Namespace, _SubParsersAction


class Command:
    name: str
    help: str

    def init_parser(self, subp: _SubParsersAction) -> None:
        parser: ArgumentParser = subp.add_parser(self.name, help=self.help)
        parser.set_defaults(func=self.execute)
        self._init_parser(parser)

    def _init_parser(self, parser: ArgumentParser) -> None:
        pass

    def execute(self, args: Namespace) -> None:
        pass


def command(name: str, help_: str):
    """Adds an __init__ setting self.name to the provided name."""

    def wrap[T: Command](cls: type[T]) -> type[T]:
        if not issubclass(cls, Command):
            raise TypeError(f"{cls.__name__} must be a subclass of {Command.__name__}")

        def __init__(self: T) -> None:
            self.name = name
            self.help = help_

        cls.__init__ = __init__  # type: ignore
        return cls

    return wrap
