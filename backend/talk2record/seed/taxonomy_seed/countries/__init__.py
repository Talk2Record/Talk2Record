"""Per-country terminology overlays.

Each subpackage owns a ``dictionary.py`` (term → normalized-term mappings)
and a ``rules.py`` (deterministic classifier rules — keyword lists and
regex patterns that lean on the country's vocabulary).

Add a new country by creating a sibling folder with the same two modules
and listing the package in
:mod:`talk2record.seed.taxonomy_seed.__init__`.
"""
