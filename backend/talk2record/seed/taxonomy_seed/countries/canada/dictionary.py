"""Canadian construction dictionary (English Canada + Québécois French).

Focuses on terms idiomatic to Canadian voice notes: CSA G30.18 metric
rebar (10M / 15M / 20M …), CSA A3001 cement types (GU / MH / HE / LH /
HS), SPF dimensional lumber, NBC / OBC / BCBC / CEC regulatory
references, CCDC contract documents, workers'-compensation boards
(WSIB / WCB / CNESST), HST/GST/PST sales tax, Interac payment rails,
and Québécois French trade vocabulary (chantier, maçon, charpentier,
ferrailleur, coffrage, …).

Source notes (audit trail):

* CSA G30.18:21 metric rebar sizes 10M–55M and Type R/W grades 400W/500W:
  https://aamasonry.ca/what-are-rebar-sizes-grades-and-types/
  https://www.pittini.com/wp-content/uploads/sites/21/Pittini-Group-rebar-SPB305.pdf
* National Building Code of Canada (NBC) Section 1.4 defined terms:
  https://canadianbuildingcodes.ca/section-1-4-terms-and-abbreviations/
* CSA Group standards (concrete, lumber, plywood, electrical safety):
  https://www.csagroup.org/
* CCDC contract documents (CCDC 2 stipulated price, CCDC 3 cost-plus, …):
  https://www.ccdc.org/
* WSIB Ontario / WorkSafeBC workers' compensation in construction:
  https://www.wsib.ca/en/operational-policy-manual/insurable-earnings-construction
  https://www.worksafebc.com/
* Québec construction terminology (CCQ / RBQ / TERMIUM Plus):
  https://ccq.org/annexes/Lexique-CCQ
  https://www.rbq.gouv.qc.ca/lexique/
  https://www.btb.termiumplus.gc.ca/
* Construction Specifications Canada (CSC) Glossary of Terms (EN+FR):
  https://csc-dcc.ca/newsevents/CSCAnnouncesUpdatedGlossaryofTerms%E2%80%93AvailableinEnglishandFrench-619/
"""

from __future__ import annotations

_INDUSTRY = "construction"

DICTIONARY_DEFINITIONS: tuple[dict, ...] = (
    # --- CSA G30.18 metric rebar (M-prefix Canadian standard) ---
    {"industry": _INDUSTRY, "category": None, "term": "10M", "normalized_term": "10M rebar (11.3mm, CSA G30.18)"},
    {"industry": _INDUSTRY, "category": None, "term": "15M", "normalized_term": "15M rebar (16.0mm, CSA G30.18)"},
    {"industry": _INDUSTRY, "category": None, "term": "20M", "normalized_term": "20M rebar (19.5mm, CSA G30.18)"},
    {"industry": _INDUSTRY, "category": None, "term": "25M", "normalized_term": "25M rebar (25.2mm, CSA G30.18)"},
    {"industry": _INDUSTRY, "category": None, "term": "30M", "normalized_term": "30M rebar (29.9mm, CSA G30.18)"},
    {"industry": _INDUSTRY, "category": None, "term": "35M", "normalized_term": "35M rebar (35.7mm, CSA G30.18)"},
    {"industry": _INDUSTRY, "category": None, "term": "45M", "normalized_term": "45M rebar (43.7mm, CSA G30.18)"},
    {"industry": _INDUSTRY, "category": None, "term": "55M", "normalized_term": "55M rebar (56.4mm, CSA G30.18)"},

    # --- CSA G30.18 rebar types and grades ---
    {"industry": _INDUSTRY, "category": None, "term": "Type R", "normalized_term": "CSA G30.18 Type R rebar (general application)"},
    {"industry": _INDUSTRY, "category": None, "term": "Type W", "normalized_term": "CSA G30.18 Type W weldable rebar"},
    {"industry": _INDUSTRY, "category": None, "term": "400R", "normalized_term": "CSA Grade 400R rebar (400 MPa yield)"},
    {"industry": _INDUSTRY, "category": None, "term": "400W", "normalized_term": "CSA Grade 400W weldable rebar (400 MPa)"},
    {"industry": _INDUSTRY, "category": None, "term": "500W", "normalized_term": "CSA Grade 500W weldable rebar (500 MPa)"},
    {"industry": _INDUSTRY, "category": None, "term": "600W", "normalized_term": "CSA Grade 600W weldable rebar (600 MPa)"},

    # --- CSA A3001 Portland cement types ---
    {"industry": _INDUSTRY, "category": None, "term": "Type GU", "normalized_term": "CSA A3001 Type GU General-Use cement"},
    {"industry": _INDUSTRY, "category": None, "term": "Type MH", "normalized_term": "CSA A3001 Type MH Moderate-Heat cement"},
    {"industry": _INDUSTRY, "category": None, "term": "Type HE", "normalized_term": "CSA A3001 Type HE High-Early-Strength cement"},
    {"industry": _INDUSTRY, "category": None, "term": "Type LH", "normalized_term": "CSA A3001 Type LH Low-Heat-of-Hydration cement"},
    {"industry": _INDUSTRY, "category": None, "term": "Type HS", "normalized_term": "CSA A3001 Type HS High-Sulfate-Resistant cement"},

    # --- Canadian dimensional lumber grading ---
    {"industry": _INDUSTRY, "category": None, "term": "SPF", "normalized_term": "Spruce-Pine-Fir dimensional lumber"},
    {"industry": _INDUSTRY, "category": None, "term": "S-P-F", "normalized_term": "Spruce-Pine-Fir dimensional lumber"},
    {"industry": _INDUSTRY, "category": None, "term": "DF-L", "normalized_term": "Douglas Fir-Larch dimensional lumber"},
    {"industry": _INDUSTRY, "category": None, "term": "Hem-Fir", "normalized_term": "Hem-Fir dimensional lumber"},

    # --- CSA standards (referenced on Canadian drawings) ---
    {"industry": _INDUSTRY, "category": None, "term": "CSA", "normalized_term": "Canadian Standards Association"},
    {"industry": _INDUSTRY, "category": None, "term": "CSA A23.1", "normalized_term": "CSA A23.1 concrete materials and construction"},
    {"industry": _INDUSTRY, "category": None, "term": "CSA O141", "normalized_term": "CSA O141 softwood lumber grading"},
    {"industry": _INDUSTRY, "category": None, "term": "CSA O121", "normalized_term": "CSA O121 Douglas Fir plywood"},
    {"industry": _INDUSTRY, "category": None, "term": "CSA O151", "normalized_term": "CSA O151 Canadian softwood plywood"},
    {"industry": _INDUSTRY, "category": None, "term": "CSA Z462", "normalized_term": "CSA Z462 workplace electrical safety"},

    # --- Building codes ---
    {"industry": _INDUSTRY, "category": None, "term": "NBC", "normalized_term": "National Building Code of Canada"},
    {"industry": _INDUSTRY, "category": None, "term": "NBCC", "normalized_term": "National Building Code of Canada"},
    {"industry": _INDUSTRY, "category": None, "term": "OBC", "normalized_term": "Ontario Building Code"},
    {"industry": _INDUSTRY, "category": None, "term": "BCBC", "normalized_term": "British Columbia Building Code"},
    {"industry": _INDUSTRY, "category": None, "term": "QCC", "normalized_term": "Québec Construction Code"},
    {"industry": _INDUSTRY, "category": None, "term": "CEC", "normalized_term": "Canadian Electrical Code"},
    {"industry": _INDUSTRY, "category": None, "term": "RBQ", "normalized_term": "Régie du bâtiment du Québec"},

    # --- Workers' compensation boards (province-specific) ---
    {"industry": _INDUSTRY, "category": None, "term": "WSIB", "normalized_term": "Workplace Safety and Insurance Board (Ontario)"},
    {"industry": _INDUSTRY, "category": None, "term": "WCB", "normalized_term": "Workers' Compensation Board (BC/Alberta/Manitoba/Sask.)"},
    {"industry": _INDUSTRY, "category": None, "term": "CNESST", "normalized_term": "Commission des normes, équité, santé et sécurité du travail (QC)"},
    {"industry": _INDUSTRY, "category": None, "term": "WSCC", "normalized_term": "Workers' Safety and Compensation Commission (NWT/NU)"},
    {"industry": _INDUSTRY, "category": None, "term": "WorkSafeBC", "normalized_term": "WorkSafeBC workers' compensation"},

    # --- CCDC contracts ---
    {"industry": _INDUSTRY, "category": None, "term": "CCDC", "normalized_term": "Canadian Construction Documents Committee contract suite"},
    {"industry": _INDUSTRY, "category": None, "term": "CCDC 2", "normalized_term": "CCDC 2 stipulated-price construction contract"},
    {"industry": _INDUSTRY, "category": None, "term": "CCDC 3", "normalized_term": "CCDC 3 cost-plus construction contract"},
    {"industry": _INDUSTRY, "category": None, "term": "CCDC 4", "normalized_term": "CCDC 4 unit-price construction contract"},
    {"industry": _INDUSTRY, "category": None, "term": "CCDC 5A", "normalized_term": "CCDC 5A construction management contract (services)"},
    {"industry": _INDUSTRY, "category": None, "term": "CCDC 5B", "normalized_term": "CCDC 5B construction management contract (at-risk)"},

    # --- Industry orgs ---
    {"industry": _INDUSTRY, "category": None, "term": "CCA", "normalized_term": "Canadian Construction Association"},
    {"industry": _INDUSTRY, "category": None, "term": "CSC", "normalized_term": "Construction Specifications Canada"},
    {"industry": _INDUSTRY, "category": None, "term": "RAIC", "normalized_term": "Royal Architectural Institute of Canada"},

    # --- Canadian trade certifications & roles ---
    {"industry": _INDUSTRY, "category": None, "term": "red seal", "normalized_term": "Red Seal interprovincial trade certification"},
    {"industry": _INDUSTRY, "category": None, "term": "journeyperson", "normalized_term": "journeyperson tradesperson"},
    {"industry": _INDUSTRY, "category": None, "term": "millwright", "normalized_term": "industrial millwright"},
    {"industry": _INDUSTRY, "category": None, "term": "ironworker", "normalized_term": "structural ironworker"},
    {"industry": _INDUSTRY, "category": None, "term": "labourer", "normalized_term": "construction labourer"},

    # --- Québécois French trades ---
    {"industry": _INDUSTRY, "category": None, "term": "maçon", "normalized_term": "mason", "description": "Québec French for 'mason'."},
    {"industry": _INDUSTRY, "category": None, "term": "charpentier", "normalized_term": "carpenter", "description": "Québec French for 'carpenter'."},
    {"industry": _INDUSTRY, "category": None, "term": "électricien", "normalized_term": "electrician", "description": "Québec French for 'electrician'."},
    {"industry": _INDUSTRY, "category": None, "term": "plombier", "normalized_term": "plumber", "description": "Québec French for 'plumber'."},
    {"industry": _INDUSTRY, "category": None, "term": "plâtrier", "normalized_term": "plasterer", "description": "Québec French for 'plasterer'."},
    {"industry": _INDUSTRY, "category": None, "term": "peintre", "normalized_term": "painter", "description": "Québec French for 'painter'."},
    {"industry": _INDUSTRY, "category": None, "term": "ferrailleur", "normalized_term": "steel-fixer", "description": "Québec French for 'steel-fixer / rebar worker'."},
    {"industry": _INDUSTRY, "category": None, "term": "couvreur", "normalized_term": "roofer", "description": "Québec French for 'roofer'."},
    {"industry": _INDUSTRY, "category": None, "term": "briqueteur", "normalized_term": "bricklayer", "description": "Québec French for 'bricklayer'."},
    {"industry": _INDUSTRY, "category": None, "term": "manœuvre", "normalized_term": "labourer", "description": "Québec French for 'site labourer'."},
    {"industry": _INDUSTRY, "category": None, "term": "contremaître", "normalized_term": "foreman", "description": "Québec French for 'site foreman'."},

    # --- Québécois French materials ---
    {"industry": _INDUSTRY, "category": None, "term": "ciment", "normalized_term": "cement"},
    {"industry": _INDUSTRY, "category": None, "term": "béton", "normalized_term": "concrete"},
    {"industry": _INDUSTRY, "category": None, "term": "brique", "normalized_term": "brick"},
    {"industry": _INDUSTRY, "category": None, "term": "acier", "normalized_term": "steel"},
    {"industry": _INDUSTRY, "category": None, "term": "sable", "normalized_term": "sand"},
    {"industry": _INDUSTRY, "category": None, "term": "gravier", "normalized_term": "gravel"},
    {"industry": _INDUSTRY, "category": None, "term": "granulat", "normalized_term": "aggregate"},
    {"industry": _INDUSTRY, "category": None, "term": "armature", "normalized_term": "reinforcement bar"},

    # --- Québécois French structural elements ---
    {"industry": _INDUSTRY, "category": None, "term": "poutre", "normalized_term": "beam"},
    {"industry": _INDUSTRY, "category": None, "term": "colonne", "normalized_term": "column"},
    {"industry": _INDUSTRY, "category": None, "term": "dalle", "normalized_term": "slab"},
    {"industry": _INDUSTRY, "category": None, "term": "fondation", "normalized_term": "foundation"},
    {"industry": _INDUSTRY, "category": None, "term": "semelle", "normalized_term": "footing"},
    {"industry": _INDUSTRY, "category": None, "term": "toiture", "normalized_term": "roof"},
    {"industry": _INDUSTRY, "category": None, "term": "plancher", "normalized_term": "floor"},
    {"industry": _INDUSTRY, "category": None, "term": "plafond", "normalized_term": "ceiling"},
    {"industry": _INDUSTRY, "category": None, "term": "escalier", "normalized_term": "staircase"},
    {"industry": _INDUSTRY, "category": None, "term": "cloison", "normalized_term": "partition wall"},

    # --- Québécois French actions / verbs ---
    {"industry": _INDUSTRY, "category": None, "term": "chantier", "normalized_term": "construction site"},
    {"industry": _INDUSTRY, "category": None, "term": "coffrage", "normalized_term": "formwork"},
    {"industry": _INDUSTRY, "category": None, "term": "ferraillage", "normalized_term": "rebar installation"},
    {"industry": _INDUSTRY, "category": None, "term": "carrelage", "normalized_term": "tile-laying"},
    {"industry": _INDUSTRY, "category": None, "term": "couler béton", "normalized_term": "pour concrete"},
    {"industry": _INDUSTRY, "category": None, "term": "creuser", "normalized_term": "excavate"},
    {"industry": _INDUSTRY, "category": None, "term": "couler", "normalized_term": "pour (concrete)"},
    {"industry": _INDUSTRY, "category": None, "term": "boulon", "normalized_term": "bolt"},

    # --- Sales tax (scoped to labor_payment so it shows up on wage records) ---
    {"industry": _INDUSTRY, "category": "labor_payment", "term": "HST", "normalized_term": "Harmonized Sales Tax (Canada)"},
    {"industry": _INDUSTRY, "category": "labor_payment", "term": "GST", "normalized_term": "Goods and Services Tax (Canada)"},
    {"industry": _INDUSTRY, "category": "labor_payment", "term": "PST", "normalized_term": "Provincial Sales Tax"},
    {"industry": _INDUSTRY, "category": "labor_payment", "term": "QST", "normalized_term": "Québec Sales Tax"},

    # --- CRA tax slips & contractor statements ---
    {"industry": _INDUSTRY, "category": "labor_payment", "term": "T4", "normalized_term": "CRA T4 Statement of Remuneration Paid"},
    {"industry": _INDUSTRY, "category": "labor_payment", "term": "T4A", "normalized_term": "CRA T4A Statement of Other Income"},
    {"industry": _INDUSTRY, "category": "labor_payment", "term": "T5018", "normalized_term": "CRA T5018 Statement of Contract Payments"},
    {"industry": _INDUSTRY, "category": "labor_payment", "term": "CRA", "normalized_term": "Canada Revenue Agency"},

    # --- Canadian payment rails ---
    {"industry": _INDUSTRY, "category": "labor_payment", "term": "Interac", "normalized_term": "Interac e-Transfer"},
    {"industry": _INDUSTRY, "category": "labor_payment", "term": "e-Transfer", "normalized_term": "Interac e-Transfer"},
    {"industry": _INDUSTRY, "category": "labor_payment", "term": "EFT", "normalized_term": "electronic funds transfer"},
    {"industry": _INDUSTRY, "category": "labor_payment", "term": "certified cheque", "normalized_term": "certified bank cheque"},
)
