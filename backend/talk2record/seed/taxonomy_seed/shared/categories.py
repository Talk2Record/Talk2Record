"""Construction categories shared across countries.

These five sub-types are universal across Kenyan, UK and US construction
sites. Country-specific terminology lives in the domain dictionary, not in
new category slugs.
"""

from __future__ import annotations

CATEGORY_DEFINITIONS: tuple[dict, ...] = (
    {
        "industry": "construction",
        "slug": "material_delivery",
        "name": "Material delivery",
        "description": "Deliveries of cement, aggregate, rebar, mesh, lumber, blocks, …",
        "priority": 10,
    },
    {
        "industry": "construction",
        "slug": "labor_payment",
        "name": "Labor payment",
        "description": "Wages paid to skilled workers, casuals and trades.",
        "priority": 20,
    },
    {
        "industry": "construction",
        "slug": "site_progress",
        "name": "Site progress",
        "description": "Progress reports: slabs cast, floors finished, walls raised.",
        "priority": 30,
    },
    {
        "industry": "construction",
        "slug": "equipment_use",
        "name": "Equipment use",
        "description": "Use of mixers, graders, cranes and other site equipment.",
        "priority": 40,
    },
    {
        "industry": "construction",
        "slug": "excavation",
        "name": "Excavation",
        "description": "Digging, trenching, foundation and footing measurements.",
        "priority": 50,
    },
)
