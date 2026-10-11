"""Domain exceptions — zero imports, safe to use from any layer."""


class BusinessRuleViolation(Exception):
    """Raised when a Karis business rule is violated."""
