class PseudocodeError(Exception):
    """Raised for anything wrong with pseudocode source, at parse or run time."""

    def __init__(self, message: str, lineno: int | None = None):
        self.lineno = lineno
        if lineno is not None:
            message = f"line {lineno}: {message}"
        super().__init__(message)
