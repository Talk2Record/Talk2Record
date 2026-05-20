"""Industries shipped by default.

These are business domains, not localisations — so the list stays identical
across countries. Per-country categories/dictionaries hang off these via
``Category.industry`` and ``DomainDictionary.industry`` foreign keys.
"""

from __future__ import annotations

INDUSTRY_DEFINITIONS: tuple[dict, ...] = (
    {
        "slug": "construction",
        "name": "Construction",
        "description": (
            "Material delivery, labor payments, site progress, equipment "
            "usage and excavation notes from construction sites."
        ),
        "priority": 10,
    },
    {
        "slug": "logistics",
        "name": "Logistics",
        "description": "Deliveries, dispatches, fleet and route notes.",
        "priority": 20,
    },
    {
        "slug": "sales",
        "name": "Sales",
        "description": "Orders, quotes, customer interactions.",
        "priority": 30,
    },
    {
        "slug": "healthcare",
        "name": "Healthcare",
        "description": "Patient visits, observations and clinical notes.",
        "priority": 40,
    },
    {
        "slug": "agriculture",
        "name": "Agriculture",
        "description": "Farm operations, harvests, inputs and yields.",
        "priority": 50,
    },
    {
        "slug": "field_operations",
        "name": "Field Operations",
        "description": "Field service jobs, inspections, repairs.",
        "priority": 60,
    },
    {
        "slug": "support",
        "name": "Customer Support",
        "description": "Complaints, tickets, support call summaries.",
        "priority": 70,
    },
)
