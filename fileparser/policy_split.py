def split_all_or_expressions(expression: str):
    """Fallback helper used by policypreprocess when custom splitter is absent.

    Current implementation simply returns the original expression so that
    downstream parsing can continue without raising ImportError. Extend this
    function if more advanced OR-splitting is required.
    """
    if expression is None:
        return []
    expression = expression.strip()
    if not expression:
        return []
    return [expression]
