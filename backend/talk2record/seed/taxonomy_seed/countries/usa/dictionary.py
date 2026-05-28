"""United States construction dictionary.

Focuses on terms idiomatic to US construction sites: ASTM C150 cement
types, imperial units (cu yd, sq ft, lin ft), #-prefix rebar with imperial
diameters, nominal vs actual lumber sizes (2x4, 2x6, …), US framing
vocabulary (stud / joist / rafter / header), AIA / GC document acronyms
(RFI, ASI, CO, SOV, G702/G703), OSHA / IBC / IRC regulatory references,
brand-as-noun tool slang (Sawzall, Skil Saw, Bobcat), and US payment
rails (ACH, wire, Venmo, Zelle).

Source notes (audit trail):

* ASTM C150/C150M Portland cement types I–V (plus IA/IIA/IIIA):
  https://www.astm.org/c0150_c0150m-21.html
  https://blog.ansi.org/ansi/portland-cement-types-specifications-astm-c150
* ASTM A615 rebar grades 40/60/75/80 and bar sizes #3–#8:
  https://www.astm.org/a0615_a0615m-20.html
  https://www.portlandbolt.com/technical/specifications/astm-a615/
* Nominal vs actual softwood lumber dimensions (2x4 = 1.5" x 3.5", …):
  https://www.lowes.com/n/how-to/nominal-actual-lumber-sizes/
  https://blog.spib.org/nominal-vs-actual-lumber-sizes/
* RFI / ASI / Change-order vocabulary (AIA A201):
  https://procore.com/jobsite/the-anatomy-of-a-request-for-information-rfi
  https://nationalgeneralcontractorauthority.com/change-order-process-for-general-contractors
"""

from __future__ import annotations

_INDUSTRY = "construction"

DICTIONARY_DEFINITIONS: tuple[dict, ...] = (
    # --- ASTM C150 Portland cement types ---
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "Type I",
        "normalized_term": "ASTM C150 Type I general-purpose Portland cement",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "Type II",
        "normalized_term": "ASTM C150 Type II moderate-sulfate-resistance Portland cement",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "Type III",
        "normalized_term": "ASTM C150 Type III high-early-strength Portland cement",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "Type IV",
        "normalized_term": "ASTM C150 Type IV low-heat-of-hydration Portland cement",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "Type V",
        "normalized_term": "ASTM C150 Type V high-sulfate-resistance Portland cement",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "Type I/II",
        "normalized_term": "ASTM C150 Type I/II Portland cement",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "Type IA",
        "normalized_term": "ASTM C150 Type IA air-entraining Portland cement",
    },
    # --- ASTM A615 rebar (#-prefix, 1/8-inch diameter increments) ---
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "#3",
        "normalized_term": '#3 rebar (3/8" diameter, ASTM A615)',
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "#4",
        "normalized_term": '#4 rebar (1/2" diameter, ASTM A615)',
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "#5",
        "normalized_term": '#5 rebar (5/8" diameter, ASTM A615)',
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "#6",
        "normalized_term": '#6 rebar (3/4" diameter, ASTM A615)',
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "#7",
        "normalized_term": '#7 rebar (7/8" diameter, ASTM A615)',
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "#8",
        "normalized_term": '#8 rebar (1" diameter, ASTM A615)',
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "#9",
        "normalized_term": '#9 rebar (1-1/8" diameter, ASTM A615)',
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "#10",
        "normalized_term": '#10 rebar (1-1/4" diameter, ASTM A615)',
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "#11",
        "normalized_term": '#11 rebar (1-3/8" diameter, ASTM A615)',
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "Grade 40",
        "normalized_term": "ASTM A615 Grade 40 rebar (40 ksi yield)",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "Grade 60",
        "normalized_term": "ASTM A615 Grade 60 rebar (60 ksi yield)",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "Grade 75",
        "normalized_term": "ASTM A615 Grade 75 rebar (75 ksi yield)",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "Grade 80",
        "normalized_term": "ASTM A615 Grade 80 rebar (80 ksi yield)",
    },
    # --- Imperial units of measure ---
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "cu yd",
        "normalized_term": "cubic yards",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "cy",
        "normalized_term": "cubic yards",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "sq ft",
        "normalized_term": "square feet",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "sf",
        "normalized_term": "square feet",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "lin ft",
        "normalized_term": "linear feet",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "lf",
        "normalized_term": "linear feet",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "psi",
        "normalized_term": "pounds per square inch",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "ksi",
        "normalized_term": "kilopounds per square inch",
    },
    # --- US framing lumber (nominal -> actual S4S dimensions) ---
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "2x4",
        "normalized_term": '2x4 nominal lumber (1.5" x 3.5" actual)',
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "2x6",
        "normalized_term": '2x6 nominal lumber (1.5" x 5.5" actual)',
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "2x8",
        "normalized_term": '2x8 nominal lumber (1.5" x 7.25" actual)',
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "2x10",
        "normalized_term": '2x10 nominal lumber (1.5" x 9.25" actual)',
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "2x12",
        "normalized_term": '2x12 nominal lumber (1.5" x 11.25" actual)',
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "4x4",
        "normalized_term": '4x4 nominal lumber (3.5" x 3.5" actual)',
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "6x6",
        "normalized_term": '6x6 nominal lumber (5.5" x 5.5" actual)',
    },
    # --- US framing vocabulary ---
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "stud",
        "normalized_term": "wall stud",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "joist",
        "normalized_term": "floor or ceiling joist",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "rafter",
        "normalized_term": "roof rafter",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "top plate",
        "normalized_term": "top plate",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "bottom plate",
        "normalized_term": "bottom (sole) plate",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "sole plate",
        "normalized_term": "sole plate",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "sheathing",
        "normalized_term": "wall/roof sheathing",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "blocking",
        "normalized_term": "wood blocking",
    },
    # --- US sheet goods & finishes ---
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "OSB",
        "normalized_term": "oriented strand board",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "CDX",
        "normalized_term": "CDX exterior-grade plywood",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "drywall",
        "normalized_term": "drywall (gypsum board)",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "sheetrock",
        "normalized_term": "drywall (Sheetrock brand)",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "gypsum",
        "normalized_term": "gypsum wallboard",
    },
    # --- US trade roles ---
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "GC",
        "normalized_term": "general contractor",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "sub",
        "normalized_term": "subcontractor",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "subs",
        "normalized_term": "subcontractors",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "PM",
        "normalized_term": "project manager",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "super",
        "normalized_term": "site superintendent",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "journeyman",
        "normalized_term": "journeyman tradesperson",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "apprentice",
        "normalized_term": "trade apprentice",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "drywaller",
        "normalized_term": "drywall installer",
    },
    # --- US equipment / tool slang ---
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "Sawzall",
        "normalized_term": "reciprocating saw",
        "description": "Sawzall is a registered Milwaukee trademark used as a generic noun.",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "Skil saw",
        "normalized_term": "circular saw",
        "description": "Brand-as-noun for a handheld circular saw.",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "Skilsaw",
        "normalized_term": "circular saw",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "chop saw",
        "normalized_term": "miter saw",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "Bobcat",
        "normalized_term": "skid-steer loader",
        "description": "Bobcat is a registered trademark used as a generic noun in the US.",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "skid steer",
        "normalized_term": "skid-steer loader",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "mini-ex",
        "normalized_term": "compact (mini) excavator",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "lull",
        "normalized_term": "telescopic handler (Lull)",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "scissor lift",
        "normalized_term": "scissor lift",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "boom lift",
        "normalized_term": "boom lift",
    },
    # --- US contract administration documents ---
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "RFI",
        "normalized_term": "Request for Information",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "ASI",
        "normalized_term": "Architect's Supplemental Instruction",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "CO",
        "normalized_term": "Change Order",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "COR",
        "normalized_term": "Change Order Request",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "change order",
        "normalized_term": "Change Order",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "SOV",
        "normalized_term": "Schedule of Values",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "G702",
        "normalized_term": "AIA G702 Application for Payment",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "G703",
        "normalized_term": "AIA G703 Continuation Sheet",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "AIA A201",
        "normalized_term": "AIA A201 General Conditions of the Contract",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "punch list",
        "normalized_term": "punch list (US snag list)",
    },
    # --- US regulatory references ---
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "OSHA",
        "normalized_term": "Occupational Safety and Health Administration",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "AHJ",
        "normalized_term": "Authority Having Jurisdiction",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "IBC",
        "normalized_term": "International Building Code",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "IRC",
        "normalized_term": "International Residential Code",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "NEC code",
        "normalized_term": "National Electrical Code",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "ADA",
        "normalized_term": "Americans with Disabilities Act",
    },
    # --- US payment rails (scoped to labor payments) ---
    {
        "industry": _INDUSTRY,
        "category": "labor_payment",
        "term": "ACH",
        "normalized_term": "ACH bank transfer",
    },
    {
        "industry": _INDUSTRY,
        "category": "labor_payment",
        "term": "wire",
        "normalized_term": "wire transfer",
    },
    {
        "industry": _INDUSTRY,
        "category": "labor_payment",
        "term": "wire transfer",
        "normalized_term": "wire transfer",
    },
    {
        "industry": _INDUSTRY,
        "category": "labor_payment",
        "term": "Venmo",
        "normalized_term": "Venmo peer-to-peer payment",
    },
    {
        "industry": _INDUSTRY,
        "category": "labor_payment",
        "term": "Zelle",
        "normalized_term": "Zelle bank-to-bank payment",
    },
    {
        "industry": _INDUSTRY,
        "category": "labor_payment",
        "term": "Cash App",
        "normalized_term": "Cash App peer-to-peer payment",
    },
    {
        "industry": _INDUSTRY,
        "category": "labor_payment",
        "term": "1099",
        "normalized_term": "IRS 1099 contractor payment",
    },
    {
        "industry": _INDUSTRY,
        "category": "labor_payment",
        "term": "W-2",
        "normalized_term": "IRS W-2 employee wages",
    },
    # --- US framing terminology (detail) ---
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "cripple stud",
        "normalized_term": "cripple stud (short stud above/below opening)",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "jack stud",
        "normalized_term": "jack stud (header support)",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "king stud",
        "normalized_term": "king stud (full-height stud at opening)",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "trimmer",
        "normalized_term": "trimmer stud (alt. name for jack stud)",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "joist hanger",
        "normalized_term": "joist hanger bracket",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "ledger board",
        "normalized_term": "ledger board",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "girder",
        "normalized_term": "girder beam",
    },
    # --- US concrete / foundation systems ---
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "SOG",
        "normalized_term": "slab on grade",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "slab on grade",
        "normalized_term": "slab on grade",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "PT slab",
        "normalized_term": "post-tensioned concrete slab",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "post-tension",
        "normalized_term": "post-tensioned concrete",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "monolithic slab",
        "normalized_term": "monolithic slab and footing pour",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "turn-down slab",
        "normalized_term": "turn-down slab (thickened edge)",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "stem wall",
        "normalized_term": "stem wall foundation",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "footer",
        "normalized_term": "concrete footer (US term for footing)",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "grade beam",
        "normalized_term": "grade beam",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "pier",
        "normalized_term": "foundation pier",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "caisson",
        "normalized_term": "drilled caisson (deep foundation)",
    },
    # --- US aggregate / gravel grades ---
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "#57 stone",
        "normalized_term": '#57 aggregate stone (3/4" nominal)',
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "#89 stone",
        "normalized_term": '#89 aggregate stone (3/8" nominal)',
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "ABC stone",
        "normalized_term": "aggregate base course",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "pea gravel",
        "normalized_term": "pea gravel",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "riprap",
        "normalized_term": "riprap stone armouring",
    },
    # --- US electrical ---
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "Romex",
        "normalized_term": "Romex NM-B non-metallic cable (brand)",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "NM-B",
        "normalized_term": "non-metallic sheathed cable (NM-B)",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "EMT",
        "normalized_term": "electrical metallic tubing",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "IMC",
        "normalized_term": "intermediate metal conduit",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "RMC",
        "normalized_term": "rigid metal conduit",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "GFCI",
        "normalized_term": "ground-fault circuit interrupter",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "AFCI",
        "normalized_term": "arc-fault circuit interrupter",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "120V",
        "normalized_term": "120-volt branch circuit",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "240V",
        "normalized_term": "240-volt circuit",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "200A panel",
        "normalized_term": "200-amp main service panel",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "sub-panel",
        "normalized_term": "electrical sub-panel",
    },
    # --- US plumbing ---
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "PEX",
        "normalized_term": "PEX cross-linked polyethylene pipe",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "ABS",
        "normalized_term": "ABS drain/waste pipe",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "CPVC",
        "normalized_term": "CPVC hot-water pipe",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "type L copper",
        "normalized_term": "Type L copper water pipe",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "type M copper",
        "normalized_term": "Type M copper water pipe",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "Schedule 40",
        "normalized_term": "PVC Schedule 40 pipe",
    },
    # --- US HVAC ---
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "HVAC",
        "normalized_term": "heating, ventilation and air conditioning",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "RTU",
        "normalized_term": "rooftop HVAC unit",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "DX",
        "normalized_term": "direct-expansion HVAC system",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "VAV",
        "normalized_term": "variable-air-volume box",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "CFM",
        "normalized_term": "cubic feet per minute (airflow)",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "MERV",
        "normalized_term": "MERV filter rating",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "SEER",
        "normalized_term": "Seasonal Energy Efficiency Ratio",
    },
    # --- US roofing ---
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "3-tab",
        "normalized_term": "3-tab asphalt shingle",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "architectural shingle",
        "normalized_term": "architectural (dimensional) asphalt shingle",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "TPO",
        "normalized_term": "TPO thermoplastic single-ply roofing",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "GAF",
        "normalized_term": "GAF roofing (brand)",
    },
    # --- US insulation ---
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "R-value",
        "normalized_term": "insulation R-value",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "batt insulation",
        "normalized_term": "fiberglass batt insulation",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "blown insulation",
        "normalized_term": "blown-in insulation",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "spray foam",
        "normalized_term": "spray-foam insulation",
    },
    # --- US fasteners ---
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "8d",
        "normalized_term": "8-penny nail (2.5 inch)",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "10d",
        "normalized_term": "10-penny nail (3 inch)",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "16d",
        "normalized_term": "16-penny nail (3.5 inch)",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "lag bolt",
        "normalized_term": "lag bolt",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "Tapcon",
        "normalized_term": "Tapcon masonry screw (brand)",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "sleeve anchor",
        "normalized_term": "sleeve anchor",
    },
    # --- US tool brands & power tools ---
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "DeWalt",
        "normalized_term": "DeWalt power tool (brand)",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "Makita",
        "normalized_term": "Makita power tool (brand)",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "Milwaukee",
        "normalized_term": "Milwaukee power tool (brand)",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "framing nailer",
        "normalized_term": "pneumatic framing nailer",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "finish nailer",
        "normalized_term": "pneumatic finish nailer",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "brad nailer",
        "normalized_term": "pneumatic brad nailer",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "palm sander",
        "normalized_term": "palm orbital sander",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "belt sander",
        "normalized_term": "belt sander",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "angle grinder",
        "normalized_term": "angle grinder",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "jackhammer",
        "normalized_term": "electric jackhammer",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "impact driver",
        "normalized_term": "cordless impact driver",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "hammer drill",
        "normalized_term": "hammer drill",
    },
    # --- US documents / submittals ---
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "COI",
        "normalized_term": "Certificate of Insurance",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "additional insured",
        "normalized_term": "additional insured endorsement",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "certificate of occupancy",
        "normalized_term": "Certificate of Occupancy",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "submittal",
        "normalized_term": "submittal package",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "shop drawing",
        "normalized_term": "shop drawing",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "daily report",
        "normalized_term": "daily field report",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "as-built",
        "normalized_term": "as-built drawings",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "rough-in",
        "normalized_term": "rough-in inspection milestone",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "dry-in",
        "normalized_term": "building dry-in milestone",
    },
    # --- US lien / bonding / insurance ---
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "mechanic's lien",
        "normalized_term": "mechanic's lien",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "lien waiver",
        "normalized_term": "lien waiver",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "performance bond",
        "normalized_term": "performance surety bond",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "payment bond",
        "normalized_term": "payment surety bond",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "surety",
        "normalized_term": "surety bond",
    },
    # --- US trade associations ---
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "AGC",
        "normalized_term": "Associated General Contractors of America",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "NECA",
        "normalized_term": "National Electrical Contractors Association",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "SMACNA",
        "normalized_term": "Sheet Metal and Air Conditioning Contractors National Association",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "IBEW",
        "normalized_term": "International Brotherhood of Electrical Workers",
    },
    # --- US weather barriers / siding (brand-as-noun) ---
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "Tyvek",
        "normalized_term": "Tyvek house wrap (brand)",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "Typar",
        "normalized_term": "Typar house wrap (brand)",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "Zip System",
        "normalized_term": "Zip System integrated sheathing (Huber)",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "Hardie board",
        "normalized_term": "Hardie fiber-cement siding (James Hardie)",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "Trex",
        "normalized_term": "Trex composite decking (brand)",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "house wrap",
        "normalized_term": "exterior house wrap",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "vapor barrier",
        "normalized_term": "vapor barrier (US spelling)",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "building paper",
        "normalized_term": "building paper",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "felt paper",
        "normalized_term": "asphalt-saturated felt paper",
    },
)
