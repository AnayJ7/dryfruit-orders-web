"""Product catalog for the dry fruit packaging business.

Structure: Category -> Variant -> list of Grades.
An empty grade list means that variant is sold without a grade tier.

Kept identical to dryfruit_orders/catalog.py so both apps behave the same.
"""

CATALOG = {
    "Almonds (Badam)": {
        "California": [],
        "Mamra": [],
        "Gurbandi": [],
    },
    "Cashews (Kaju)": {
        "W180": [],
        "W240": [],
        "W320": [],
    },
    "Pistachios (Pista)": {
        "Iranian": ["Grade A", "Grade B", "Grade C"],
        "American": ["Grade A", "Grade B"],
    },
    "Walnuts (Akhrot)": {
        "Kashmiri": [],
        "Chandler": [],
    },
    "Raisins (Kishmish)": {
        "Green": ["Premium", "Standard"],
        "Black": [],
    },
    "Dates (Khajur)": {
        "Medjool": ["Grade A", "Grade B"],
        "Kimia": [],
    },
}


def categories():
    return list(CATALOG.keys())


def variants(category):
    return list(CATALOG.get(category, {}).keys())


def grades(category, variant):
    return list(CATALOG.get(category, {}).get(variant, []))
