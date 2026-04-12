"""Decision tree evaluator for email routing.

A tree is a nested dict loaded from YAML. Each node is either:
  - A leaf:   {"email_id": <int | None>}
  - A branch: {"condition": {"field": str, "op": str, "value": any},
               "yes": <node>, "no": <node>}

evaluate() walks the tree and returns the email_id at the matching leaf,
or None if the leaf has a null email_id.
"""


def _normalize(v):
    """Lowercase strings for case-insensitive comparison; pass numbers through."""
    return v.lower() if isinstance(v, str) else v


_OPS = {
    "lt":  lambda a, b: a < b,
    "lte": lambda a, b: a <= b,
    "gt":  lambda a, b: a > b,
    "gte": lambda a, b: a >= b,
    "eq":  lambda a, b: _normalize(a) == _normalize(b),
    "ne":  lambda a, b: _normalize(a) != _normalize(b),
    "in":  lambda a, b: _normalize(a) in [_normalize(x) for x in b],
}


def evaluate(node: dict, context: dict) -> int | None:
    """
    Walk the decision tree, evaluating conditions against context.

    Args:
        node: A branch or leaf dict (see module docstring for schema).
        context: A flat dict with keys like distance_miles, driver_state,
                 charger_state, charger_city.

    Returns:
        The integer email_id at the matching leaf, or None for a null leaf.

    Raises:
        KeyError: If a required context field is missing.
        ValueError: If an operator name is unrecognised.
    """
    if "email_id" in node:
        return node["email_id"]

    cond = node["condition"]
    field = cond["field"]
    op = cond["op"]
    value = cond["value"]

    if op not in _OPS:
        raise ValueError(f"Unknown operator: {op!r}. Valid ops: {sorted(_OPS)}")

    actual = context[field]  # raises KeyError if field is absent
    branch = "yes" if _OPS[op](actual, value) else "no"
    return evaluate(node[branch], context)
