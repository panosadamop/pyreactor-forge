"""English pluralisation for entity names, tables and route paths.

`Category` has to become `categories`, not `categorys`: the plural shows up in
the table name, the API prefix, the router module and the React route, so a
naive `name + "s"` is visible everywhere. These are the regular English rules
plus the handful of irregulars that turn up in real domain models.
"""

import re

# Same in singular and plural.
UNCOUNTABLE = {
    "data",
    "equipment",
    "fish",
    "information",
    "media",
    "money",
    "news",
    "rice",
    "series",
    "sheep",
    "software",
    "species",
    "staff",
}

IRREGULAR = {
    "person": "people",
    "child": "children",
    "man": "men",
    "woman": "women",
    "tooth": "teeth",
    "foot": "feet",
    "goose": "geese",
    "mouse": "mice",
    "louse": "lice",
    "ox": "oxen",
    "die": "dice",
    "criterion": "criteria",
    "datum": "data",
    "medium": "media",
    "index": "indices",
    "appendix": "appendices",
    "matrix": "matrices",
    "vertex": "vertices",
}

# -f / -fe words that take -ves. Everything else keeps the f (roof -> roofs).
F_TO_VES = {
    "calf",
    "elf",
    "half",
    "knife",
    "leaf",
    "life",
    "loaf",
    "self",
    "shelf",
    "thief",
    "wife",
    "wolf",
}

# -o words that take -es. Everything else takes -s (photo -> photos).
O_TO_OES = {
    "buffalo",
    "echo",
    "embargo",
    "hero",
    "potato",
    "tomato",
    "torpedo",
    "veto",
    "volcano",
}


def pluralize(word: str) -> str:
    """Pluralise a lowercase identifier ('category' -> 'categories')."""
    if not word:
        return word

    lower = word.lower()
    if lower in UNCOUNTABLE:
        return word
    if lower in IRREGULAR:
        return IRREGULAR[lower]

    # Compound identifiers pluralise on their last word: orderitem -> orderitems,
    # order_item -> order_items.
    match = re.search(r"[A-Za-z]+$", word)
    if match and match.group() != word:
        head, tail = word[: match.start()], match.group()
        return head + pluralize(tail)

    if lower in F_TO_VES:
        return word[:-1] + "ves" if lower.endswith("f") else word[:-2] + "ves"
    if lower in O_TO_OES:
        return word + "es"

    if lower.endswith("is"):
        return word[:-2] + "es"     # analysis -> analyses
    if re.search(r"[^z]z$", lower):
        return word + "zes"         # quiz -> quizzes
    if re.search(r"(s|x|z|ch|sh)$", lower):
        return word + "es"          # box -> boxes, address -> addresses
    if re.search(r"[^aeiou]y$", lower):
        return word[:-1] + "ies"    # category -> categories, city -> cities
    return word + "s"


def legacy_plural(word: str) -> str:
    """The pre-0.2 plural (`name + "s"`), kept so old projects stay editable."""
    return word + "s"


def table_name_for(entity_name: str) -> str:
    """Default table name for an entity."""
    return pluralize(entity_name.lower())
