"""Custom exception hierarchy so callers can handle simulator errors cleanly."""


class OSSimError(Exception):
    """Base class for every error raised intentionally by the simulator."""


class ValidationError(OSSimError):
    """Input data is malformed, out of range, or inconsistent."""


class SimulationError(OSSimError):
    """A simulation could not be carried out (e.g. impossible state)."""


class BashToolError(OSSimError):
    """A Bash helper script failed or is unavailable on this host."""
