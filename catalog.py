"""Product catalog for the dry fruit packaging business.

Structure: Category -> Variant -> list of Grades.
An empty grade list means that variant is sold without a grade tier.

Kept identical to dryfruit_orders/catalog.py so both apps behave the same.
"""

CATALOG = {
    "Badam (Almond)": {
        "Slice": [],
        "Stick": [],
        "3pcs": [],
        "2pcs": [],
        "Powder": [],
        "BB": [],
    },
    "Pista (Pistachio)": {
        "Slice": ["IR (Iranian)", "AG (Afghan/American Grade)"],
        "Stick": ["IR (Iranian)"],
    },
}


def categories():
    return list(CATALOG.keys())


def variants(category):
    return list(CATALOG.get(category, {}).keys())


def grades(category, variant):
    return list(CATALOG.get(category, {}).get(variant, []))
