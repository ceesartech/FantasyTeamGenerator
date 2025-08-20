def name_contains(name: str, needles: list[str]) -> bool:
    low = name.lower()
    return any(n.lower() in low for n in (needles or []))