"""United Kingdom construction dictionary.

Focuses on terms idiomatic to UK building sites: trade slang (chippy,
sparky, brickie, navvy), the current BS 4449:2005+A3:2016 H-prefix /
B500 rebar grades, NRM / JCT / NEC contract vocabulary, branded
insulation (PIR, Celotex, Kingspan), MOT Type 1 granular sub-base, brick
bonds, and BACS payment rails.

Universal English/BS terms (units, OPC/PPC/CEM I, Y-rebar, BRC mesh,
lintel/parapet/soffit/DPC/DPM) live in
:mod:`talk2record.seed.taxonomy_seed.shared.dictionary`.

Source notes (audit trail):

* BS 4449:2005+A3:2016 grades B500A/B/C and H-prefix bar sizes:
  https://concretemath.co.uk/uk-concrete-guide/bs-standards/bs-4449-reinforcement/
  https://nextdaysteel.co.uk/pages/rebar-options-grades-uk
* UK trade slang ("chippy", "sparky", "brickie", "navvy", "banksman"):
  https://ukconstructiondirectory.co.uk/project-management/brickie-and-other-construction-nicknames-how-tradespeople-get-their-colloquial-names/
  https://absp.org.uk/words/occupconstruction.shtml
* RICS New Rules of Measurement (NRM1/2/3):
  https://www.rics.org/profession-standards/rics-standards-and-guidance/sector-standards/construction-standards/nrm
* JCT 2024 / NEC contract preliminaries:
  https://newmanor.com/a-guide-to-understanding-preliminaries-in-construction-contracts/
* BS-classified DPC/DPM, plasterboard, PIR insulation:
  https://concretecalculate.co.uk/building-regulations-guide/dpc-dpm-requirements/
  https://timberdevelopment.uk/products-database/constructional-wood-based-panels/
"""

from __future__ import annotations

_INDUSTRY = "construction"

DICTIONARY_DEFINITIONS: tuple[dict, ...] = (
    # --- BS 4449:2005+A3:2016 rebar (H-prefix, current UK notation) ---
    {"industry": _INDUSTRY, "category": None, "term": "H8", "normalized_term": "8mm BS 4449 ribbed bar"},
    {"industry": _INDUSTRY, "category": None, "term": "H10", "normalized_term": "10mm BS 4449 ribbed bar"},
    {"industry": _INDUSTRY, "category": None, "term": "H12", "normalized_term": "12mm BS 4449 ribbed bar"},
    {"industry": _INDUSTRY, "category": None, "term": "H16", "normalized_term": "16mm BS 4449 ribbed bar"},
    {"industry": _INDUSTRY, "category": None, "term": "H20", "normalized_term": "20mm BS 4449 ribbed bar"},
    {"industry": _INDUSTRY, "category": None, "term": "H25", "normalized_term": "25mm BS 4449 ribbed bar"},
    {"industry": _INDUSTRY, "category": None, "term": "H32", "normalized_term": "32mm BS 4449 ribbed bar"},
    {"industry": _INDUSTRY, "category": None, "term": "H40", "normalized_term": "40mm BS 4449 ribbed bar"},
    {"industry": _INDUSTRY, "category": None, "term": "T10", "normalized_term": "10mm tor steel bar (legacy)"},
    {"industry": _INDUSTRY, "category": None, "term": "T12", "normalized_term": "12mm tor steel bar (legacy)"},
    {"industry": _INDUSTRY, "category": None, "term": "T16", "normalized_term": "16mm tor steel bar (legacy)"},
    {"industry": _INDUSTRY, "category": None, "term": "T20", "normalized_term": "20mm tor steel bar (legacy)"},
    {"industry": _INDUSTRY, "category": None, "term": "T25", "normalized_term": "25mm tor steel bar (legacy)"},
    {"industry": _INDUSTRY, "category": None, "term": "B500A", "normalized_term": "BS 4449 Class A low-ductility rebar (500 MPa)"},
    {"industry": _INDUSTRY, "category": None, "term": "B500B", "normalized_term": "BS 4449 Class B normal-ductility rebar (500 MPa)"},
    {"industry": _INDUSTRY, "category": None, "term": "B500C", "normalized_term": "BS 4449 Class C high-ductility rebar (500 MPa)"},

    # --- UK trade slang ---
    {"industry": _INDUSTRY, "category": None, "term": "chippy", "normalized_term": "carpenter"},
    {"industry": _INDUSTRY, "category": None, "term": "sparky", "normalized_term": "electrician"},
    {"industry": _INDUSTRY, "category": None, "term": "sparks", "normalized_term": "electrician"},
    {"industry": _INDUSTRY, "category": None, "term": "brickie", "normalized_term": "bricklayer"},
    {"industry": _INDUSTRY, "category": None, "term": "navvy", "normalized_term": "construction labourer"},
    {"industry": _INDUSTRY, "category": None, "term": "navvies", "normalized_term": "construction labourers"},
    {"industry": _INDUSTRY, "category": None, "term": "groundworker", "normalized_term": "groundworker"},
    {"industry": _INDUSTRY, "category": None, "term": "banksman", "normalized_term": "vehicle-movements banksman"},
    {"industry": _INDUSTRY, "category": None, "term": "ganger", "normalized_term": "ganger (works supervisor)"},
    {"industry": _INDUSTRY, "category": None, "term": "gaffer", "normalized_term": "site gaffer (foreman)"},
    {"industry": _INDUSTRY, "category": None, "term": "plumbie", "normalized_term": "plumber"},
    {"industry": _INDUSTRY, "category": None, "term": "tradie", "normalized_term": "tradesperson"},
    {"industry": _INDUSTRY, "category": None, "term": "site agent", "normalized_term": "site agent"},

    # --- UK brick bonds & masonry vocabulary ---
    {"industry": _INDUSTRY, "category": None, "term": "stretcher bond", "normalized_term": "stretcher (running) bond"},
    {"industry": _INDUSTRY, "category": None, "term": "Flemish bond", "normalized_term": "Flemish bond brickwork"},
    {"industry": _INDUSTRY, "category": None, "term": "English bond", "normalized_term": "English bond brickwork"},
    {"industry": _INDUSTRY, "category": None, "term": "header bond", "normalized_term": "header bond brickwork"},
    {"industry": _INDUSTRY, "category": None, "term": "soldier course", "normalized_term": "soldier course"},

    # --- UK materials (branded + standardised) ---
    {"industry": _INDUSTRY, "category": None, "term": "MOT Type 1", "normalized_term": "MOT Type 1 granular sub-base"},
    {"industry": _INDUSTRY, "category": None, "term": "Type 1", "normalized_term": "MOT Type 1 granular sub-base"},
    {"industry": _INDUSTRY, "category": None, "term": "PIR", "normalized_term": "polyisocyanurate (PIR) insulation"},
    {"industry": _INDUSTRY, "category": None, "term": "Celotex", "normalized_term": "PIR insulation (Celotex)", "description": "Common brand-as-noun for PIR rigid insulation."},
    {"industry": _INDUSTRY, "category": None, "term": "Kingspan", "normalized_term": "PIR insulation (Kingspan)", "description": "Common brand-as-noun for PIR rigid insulation."},
    {"industry": _INDUSTRY, "category": None, "term": "plasterboard", "normalized_term": "plasterboard"},
    {"industry": _INDUSTRY, "category": None, "term": "OSB3", "normalized_term": "OSB Grade 3 (humid-use oriented strand board)"},
    {"industry": _INDUSTRY, "category": None, "term": "MR MDF", "normalized_term": "moisture-resistant medium-density fibreboard"},
    {"industry": _INDUSTRY, "category": None, "term": "SBR", "normalized_term": "styrene-butadiene rubber bonding agent"},

    # --- UK QS / contract administration ---
    {"industry": _INDUSTRY, "category": None, "term": "BOQ", "normalized_term": "Bill of Quantities"},
    {"industry": _INDUSTRY, "category": None, "term": "BQ", "normalized_term": "Bill of Quantities"},
    {"industry": _INDUSTRY, "category": None, "term": "prelims", "normalized_term": "preliminaries"},
    {"industry": _INDUSTRY, "category": None, "term": "P&G", "normalized_term": "preliminaries and general items"},
    {"industry": _INDUSTRY, "category": None, "term": "VO", "normalized_term": "variation order"},
    {"industry": _INDUSTRY, "category": None, "term": "IPC", "normalized_term": "interim payment certificate"},
    {"industry": _INDUSTRY, "category": None, "term": "PC sum", "normalized_term": "prime cost sum"},
    {"industry": _INDUSTRY, "category": None, "term": "provisional sum", "normalized_term": "provisional sum"},
    {"industry": _INDUSTRY, "category": None, "term": "dayworks", "normalized_term": "dayworks rate"},
    {"industry": _INDUSTRY, "category": None, "term": "retention", "normalized_term": "retention money"},
    {"industry": _INDUSTRY, "category": None, "term": "DLP", "normalized_term": "defects liability period"},
    {"industry": _INDUSTRY, "category": None, "term": "snag list", "normalized_term": "snag list"},
    {"industry": _INDUSTRY, "category": None, "term": "snagging", "normalized_term": "snagging inspection"},
    {"industry": _INDUSTRY, "category": None, "term": "NRM", "normalized_term": "RICS New Rules of Measurement"},
    {"industry": _INDUSTRY, "category": None, "term": "NRM1", "normalized_term": "NRM1 (order of cost estimating)"},
    {"industry": _INDUSTRY, "category": None, "term": "NRM2", "normalized_term": "NRM2 (detailed measurement for building works)"},
    {"industry": _INDUSTRY, "category": None, "term": "NRM3", "normalized_term": "NRM3 (building maintenance cost planning)"},
    {"industry": _INDUSTRY, "category": None, "term": "SMM7", "normalized_term": "Standard Method of Measurement 7 (legacy)"},
    {"industry": _INDUSTRY, "category": None, "term": "JCT", "normalized_term": "JCT standard form of contract"},
    {"industry": _INDUSTRY, "category": None, "term": "NEC", "normalized_term": "NEC standard form of contract"},
    {"industry": _INDUSTRY, "category": None, "term": "RIBA", "normalized_term": "Royal Institute of British Architects work-stages"},
    {"industry": _INDUSTRY, "category": None, "term": "RICS", "normalized_term": "Royal Institution of Chartered Surveyors"},

    # --- UK building regs ---
    {"industry": _INDUSTRY, "category": None, "term": "Part L", "normalized_term": "Building Regs Part L (conservation of fuel and power)"},
    {"industry": _INDUSTRY, "category": None, "term": "Part E", "normalized_term": "Building Regs Part E (sound insulation)"},
    {"industry": _INDUSTRY, "category": None, "term": "Part M", "normalized_term": "Building Regs Part M (access to buildings)"},
    {"industry": _INDUSTRY, "category": None, "term": "NHBC", "normalized_term": "National House Building Council standards"},
    {"industry": _INDUSTRY, "category": None, "term": "CDM", "normalized_term": "Construction Design and Management regulations"},

    # --- UK equipment / plant slang ---
    {"industry": _INDUSTRY, "category": None, "term": "digger", "normalized_term": "excavator"},
    {"industry": _INDUSTRY, "category": None, "term": "telehandler", "normalized_term": "telescopic handler"},
    {"industry": _INDUSTRY, "category": None, "term": "whacker plate", "normalized_term": "vibratory plate compactor"},
    {"industry": _INDUSTRY, "category": None, "term": "vibrating plate", "normalized_term": "vibratory plate compactor"},
    {"industry": _INDUSTRY, "category": None, "term": "breaker", "normalized_term": "hydraulic breaker"},
    {"industry": _INDUSTRY, "category": None, "term": "transit", "normalized_term": "transit (panel/box) van"},

    # --- UK payment rails (scoped to labor payments) ---
    {"industry": _INDUSTRY, "category": "labor_payment", "term": "BACS", "normalized_term": "BACS bank transfer"},
    {"industry": _INDUSTRY, "category": "labor_payment", "term": "CHAPS", "normalized_term": "CHAPS same-day transfer"},
    {"industry": _INDUSTRY, "category": "labor_payment", "term": "faster payment", "normalized_term": "UK Faster Payment"},
    {"industry": _INDUSTRY, "category": "labor_payment", "term": "CIS", "normalized_term": "Construction Industry Scheme deduction"},

    # --- Structural steel sections (BS 4-1 / BS EN 10365) ---
    {"industry": _INDUSTRY, "category": None, "term": "UB", "normalized_term": "Universal Beam (UB)"},
    {"industry": _INDUSTRY, "category": None, "term": "UC", "normalized_term": "Universal Column (UC)"},
    {"industry": _INDUSTRY, "category": None, "term": "SHS", "normalized_term": "Square Hollow Section"},
    {"industry": _INDUSTRY, "category": None, "term": "CHS", "normalized_term": "Circular Hollow Section"},
    {"industry": _INDUSTRY, "category": None, "term": "RHS", "normalized_term": "Rectangular Hollow Section"},
    {"industry": _INDUSTRY, "category": None, "term": "PFC", "normalized_term": "Parallel Flange Channel"},
    {"industry": _INDUSTRY, "category": None, "term": "RSJ", "normalized_term": "Rolled Steel Joist (legacy)"},
    {"industry": _INDUSTRY, "category": None, "term": "flitch beam", "normalized_term": "flitch beam (timber-steel composite)"},
    {"industry": _INDUSTRY, "category": None, "term": "lattice girder", "normalized_term": "lattice girder"},

    # --- UK health & safety acronyms ---
    {"industry": _INDUSTRY, "category": None, "term": "COSHH", "normalized_term": "Control of Substances Hazardous to Health"},
    {"industry": _INDUSTRY, "category": None, "term": "RAMS", "normalized_term": "Risk Assessment and Method Statement"},
    {"industry": _INDUSTRY, "category": None, "term": "RA", "normalized_term": "Risk Assessment"},
    {"industry": _INDUSTRY, "category": None, "term": "MS", "normalized_term": "Method Statement"},
    {"industry": _INDUSTRY, "category": None, "term": "PTW", "normalized_term": "Permit to Work"},
    {"industry": _INDUSTRY, "category": None, "term": "SSOW", "normalized_term": "Safe System of Work"},
    {"industry": _INDUSTRY, "category": None, "term": "TBT", "normalized_term": "toolbox talk"},
    {"industry": _INDUSTRY, "category": None, "term": "RIDDOR", "normalized_term": "Reporting of Injuries, Diseases and Dangerous Occurrences Regulations"},
    {"industry": _INDUSTRY, "category": None, "term": "HSE", "normalized_term": "Health and Safety Executive"},
    {"industry": _INDUSTRY, "category": None, "term": "RPE", "normalized_term": "Respiratory Protective Equipment"},

    # --- UK trades & site roles ---
    {"industry": _INDUSTRY, "category": None, "term": "joiner", "normalized_term": "joiner (UK carpenter, often shop-based)"},
    {"industry": _INDUSTRY, "category": None, "term": "roofer", "normalized_term": "roofer"},
    {"industry": _INDUSTRY, "category": None, "term": "glazier", "normalized_term": "glazier"},
    {"industry": _INDUSTRY, "category": None, "term": "dryliner", "normalized_term": "dry-lining installer"},
    {"industry": _INDUSTRY, "category": None, "term": "plant operator", "normalized_term": "plant operator"},

    # --- UK hand tools / site slang ---
    {"industry": _INDUSTRY, "category": None, "term": "muck", "normalized_term": "mortar (site slang)"},
    {"industry": _INDUSTRY, "category": None, "term": "lump hammer", "normalized_term": "lump (club) hammer"},
    {"industry": _INDUSTRY, "category": None, "term": "club hammer", "normalized_term": "club hammer"},
    {"industry": _INDUSTRY, "category": None, "term": "spirit level", "normalized_term": "spirit level"},
    {"industry": _INDUSTRY, "category": None, "term": "plumb line", "normalized_term": "plumb line"},
    {"industry": _INDUSTRY, "category": None, "term": "Stanley knife", "normalized_term": "utility (Stanley) knife"},

    # --- Concrete admixtures (BS spelling) ---
    {"industry": _INDUSTRY, "category": None, "term": "superplasticiser", "normalized_term": "concrete superplasticiser"},
    {"industry": _INDUSTRY, "category": None, "term": "plasticiser", "normalized_term": "concrete plasticiser"},
    {"industry": _INDUSTRY, "category": None, "term": "retarder", "normalized_term": "concrete set-retarder"},
    {"industry": _INDUSTRY, "category": None, "term": "accelerator", "normalized_term": "concrete set-accelerator"},
    {"industry": _INDUSTRY, "category": None, "term": "air-entraining", "normalized_term": "air-entraining concrete admixture"},

    # --- UK MEP (mechanical, electrical, plumbing) ---
    {"industry": _INDUSTRY, "category": None, "term": "combi boiler", "normalized_term": "combination gas boiler"},
    {"industry": _INDUSTRY, "category": None, "term": "system boiler", "normalized_term": "system gas boiler"},
    {"industry": _INDUSTRY, "category": None, "term": "condensing boiler", "normalized_term": "condensing gas boiler"},
    {"industry": _INDUSTRY, "category": None, "term": "MVHR", "normalized_term": "mechanical ventilation with heat recovery"},
    {"industry": _INDUSTRY, "category": None, "term": "ASHP", "normalized_term": "air-source heat pump"},
    {"industry": _INDUSTRY, "category": None, "term": "GSHP", "normalized_term": "ground-source heat pump"},
    {"industry": _INDUSTRY, "category": None, "term": "RCBO", "normalized_term": "residual current breaker with overcurrent"},
    {"industry": _INDUSTRY, "category": None, "term": "MCB", "normalized_term": "miniature circuit breaker"},
    {"industry": _INDUSTRY, "category": None, "term": "RCD", "normalized_term": "residual current device"},
    {"industry": _INDUSTRY, "category": None, "term": "CU", "normalized_term": "consumer unit (electrical)"},
    {"industry": _INDUSTRY, "category": None, "term": "18th Edition", "normalized_term": "BS 7671 18th Edition Wiring Regulations"},
    {"industry": _INDUSTRY, "category": None, "term": "soil stack", "normalized_term": "soil and vent stack"},
    {"industry": _INDUSTRY, "category": None, "term": "IC", "normalized_term": "drainage inspection chamber"},
    {"industry": _INDUSTRY, "category": None, "term": "15mm pipe", "normalized_term": "15mm copper pipe"},
    {"industry": _INDUSTRY, "category": None, "term": "22mm pipe", "normalized_term": "22mm copper pipe"},
    {"industry": _INDUSTRY, "category": None, "term": "28mm pipe", "normalized_term": "28mm copper pipe"},

    # --- UK doors / windows ---
    {"industry": _INDUSTRY, "category": None, "term": "PVCu", "normalized_term": "unplasticised polyvinyl chloride (uPVC)"},
    {"industry": _INDUSTRY, "category": None, "term": "casement", "normalized_term": "casement window"},
    {"industry": _INDUSTRY, "category": None, "term": "sash window", "normalized_term": "sliding-sash window"},
    {"industry": _INDUSTRY, "category": None, "term": "mullion", "normalized_term": "window mullion"},
    {"industry": _INDUSTRY, "category": None, "term": "transom", "normalized_term": "window transom"},
    {"industry": _INDUSTRY, "category": None, "term": "cill", "normalized_term": "window sill (UK spelling)"},

    # --- UK roofing ---
    {"industry": _INDUSTRY, "category": None, "term": "ridge tile", "normalized_term": "ridge tile"},
    {"industry": _INDUSTRY, "category": None, "term": "hip tile", "normalized_term": "hip tile"},
    {"industry": _INDUSTRY, "category": None, "term": "valley", "normalized_term": "roof valley"},
    {"industry": _INDUSTRY, "category": None, "term": "verge", "normalized_term": "roof verge"},
    {"industry": _INDUSTRY, "category": None, "term": "soaker", "normalized_term": "lead soaker flashing"},
    {"industry": _INDUSTRY, "category": None, "term": "lead flashing", "normalized_term": "lead flashing"},
    {"industry": _INDUSTRY, "category": None, "term": "EPDM", "normalized_term": "EPDM single-ply rubber roofing"},
    {"industry": _INDUSTRY, "category": None, "term": "single-ply", "normalized_term": "single-ply roofing membrane"},

    # --- UK render / finishes ---
    {"industry": _INDUSTRY, "category": None, "term": "K-Rend", "normalized_term": "K-Rend silicone render (brand)"},
    {"industry": _INDUSTRY, "category": None, "term": "monocouche", "normalized_term": "monocouche through-coloured render"},
    {"industry": _INDUSTRY, "category": None, "term": "lime render", "normalized_term": "lime render"},
    {"industry": _INDUSTRY, "category": None, "term": "scratch coat", "normalized_term": "render scratch coat"},

    # --- UK QS / commercial extras ---
    {"industry": _INDUSTRY, "category": None, "term": "tender", "normalized_term": "construction tender"},
    {"industry": _INDUSTRY, "category": None, "term": "cost plan", "normalized_term": "cost plan"},
    {"industry": _INDUSTRY, "category": None, "term": "cost report", "normalized_term": "monthly cost report"},
    {"industry": _INDUSTRY, "category": None, "term": "schedule of rates", "normalized_term": "schedule of rates"},
    {"industry": _INDUSTRY, "category": None, "term": "target cost", "normalized_term": "target-cost contract (NEC Option C)"},

    # --- UK quality / certification ---
    {"industry": _INDUSTRY, "category": None, "term": "BBA", "normalized_term": "BBA (British Board of Agrément) certification"},
    {"industry": _INDUSTRY, "category": None, "term": "CE mark", "normalized_term": "CE marking"},
    {"industry": _INDUSTRY, "category": None, "term": "UKCA", "normalized_term": "UKCA conformity marking"},

    # --- UK drainage ---
    {"industry": _INDUSTRY, "category": None, "term": "SuDS", "normalized_term": "Sustainable Drainage Systems"},
    {"industry": _INDUSTRY, "category": None, "term": "soakaway", "normalized_term": "soakaway"},
    {"industry": _INDUSTRY, "category": None, "term": "attenuation", "normalized_term": "stormwater attenuation tank"},
    {"industry": _INDUSTRY, "category": None, "term": "foul drain", "normalized_term": "foul-water drainage"},
    {"industry": _INDUSTRY, "category": None, "term": "surface water", "normalized_term": "surface-water drainage"},
    {"industry": _INDUSTRY, "category": None, "term": "manhole", "normalized_term": "drainage manhole"},
    {"industry": _INDUSTRY, "category": None, "term": "gully", "normalized_term": "drainage gully"},

    # --- UK foundations ---
    {"industry": _INDUSTRY, "category": None, "term": "pad foundation", "normalized_term": "pad foundation"},
    {"industry": _INDUSTRY, "category": None, "term": "piled foundation", "normalized_term": "piled foundation"},
    {"industry": _INDUSTRY, "category": None, "term": "strip foundation", "normalized_term": "strip foundation"},
    {"industry": _INDUSTRY, "category": None, "term": "underpinning", "normalized_term": "underpinning works"},
    {"industry": _INDUSTRY, "category": None, "term": "mass concrete", "normalized_term": "mass concrete fill"},

    # --- UK Building Regs (Approved Documents) ---
    {"industry": _INDUSTRY, "category": None, "term": "Part B", "normalized_term": "Building Regs Part B (fire safety)"},
    {"industry": _INDUSTRY, "category": None, "term": "Part F", "normalized_term": "Building Regs Part F (ventilation)"},
    {"industry": _INDUSTRY, "category": None, "term": "Part G", "normalized_term": "Building Regs Part G (sanitation, hot water and water efficiency)"},
    {"industry": _INDUSTRY, "category": None, "term": "Part P", "normalized_term": "Building Regs Part P (electrical safety)"},
    {"industry": _INDUSTRY, "category": None, "term": "Part Q", "normalized_term": "Building Regs Part Q (security)"},
    {"industry": _INDUSTRY, "category": None, "term": "Part S", "normalized_term": "Building Regs Part S (electric vehicle charging)"},

    # --- UK cavity / wall ---
    {"industry": _INDUSTRY, "category": None, "term": "cavity wall", "normalized_term": "cavity wall construction"},
    {"industry": _INDUSTRY, "category": None, "term": "wall tie", "normalized_term": "cavity wall tie"},
    {"industry": _INDUSTRY, "category": None, "term": "AVCL", "normalized_term": "air and vapour control layer"},
    {"industry": _INDUSTRY, "category": None, "term": "VCL", "normalized_term": "vapour control layer"},
    {"industry": _INDUSTRY, "category": None, "term": "breather membrane", "normalized_term": "breather membrane"},
)
