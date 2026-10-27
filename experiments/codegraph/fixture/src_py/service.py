from src_py.core import normalize_intent

def plan_idea(value: str) -> dict:
    return {'intent': normalize_intent(value), 'stage': 0}
