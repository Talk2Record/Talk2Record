Extending Talk2Record to a new industry
=======================================

Talk2Record's extraction pipeline is fully data-driven. Adding a new
industry (logistics, healthcare, agriculture, ...) does **not** require a
Python deploy — every step below is performed through the Django admin or,
optionally, by adding rows to ``talk2record.seed.taxonomy_seed``.

The pipeline at runtime
-----------------------

Every transcript flows through these stages:

1. **Transcription** — audio → text.
2. **Classification** — :class:`~talk2record.taxonomy.services.classification.ClassificationService`
   scores enabled :class:`~talk2record.taxonomy.models.ProcessingRule` rows
   against the transcript. If the top score is below
   ``TAXONOMY_CLASSIFICATION_MIN_CONFIDENCE`` (default ``0.5``) and an LLM
   provider is available, a global ``classification`` prompt is used as a
   fallback.
3. **Normalization** — :class:`~talk2record.taxonomy.services.dictionary.DictionaryNormalizer`
   rewrites the transcript using :class:`~talk2record.taxonomy.models.DomainDictionary`
   rows. Narrowest scope wins, longest term wins.
4. **Extraction** — for each detected category,
   :class:`~talk2record.taxonomy.services.extraction.DynamicExtractionService`
   resolves the most specific enabled
   :class:`~talk2record.taxonomy.models.PromptTemplate` of purpose
   ``extraction`` and runs the LLM with the resolved
   :class:`~talk2record.taxonomy.models.ExtractionSchema` as JSON Schema.
5. **Validation** — :class:`~talk2record.taxonomy.services.validation.SchemaValidator`
   validates each result against the schema. Failures populate
   ``Record.validation_errors`` and flip the record into ``review`` state.
6. **Persistence** — ``RecordProcessingService.apply_pipeline_outcome``
   writes the projection columns
   (``detected_industries``, ``detected_categories``, ``extracted_data``,
   ``validation_errors``, ``confidence_score``). Each sub-step also writes
   an immutable :class:`~talk2record.records.models.RecordArtifact` for
   audit and replay.

Step 1 — Define the industry
----------------------------

Admin path: **Taxonomy → Industries → Add**.

Fields:

* ``slug`` — short URL-safe handle, e.g. ``logistics``.
* ``name`` — human-readable, e.g. ``Logistics``.
* ``priority`` — lower numbers run first when the classifier breaks ties.
* ``enabled`` — flip to false to retire an industry without deleting data.

Step 2 — Add categories
-----------------------

Admin path: **Taxonomy → Categories → Add**.

A category lives inside a single industry. Examples:

* ``logistics.delivery``
* ``logistics.dispatch``
* ``healthcare.visit``
* ``agriculture.harvest``

Use lowercase, snake_case slugs. The slug appears in the API
(``record.detected_categories[].slug``) and in the frontend table.

Step 3 — Author the extraction schema
-------------------------------------

Admin path: **Taxonomy → Extraction schemas → Add**.

Paste a JSON Schema draft-07 document into ``json_schema``. Mark the row
``is_default`` if it should be picked automatically (only one default per
category is allowed). Required fields go in the ``required`` array inside
the JSON Schema; the convenience ``required_fields`` column mirrors that
list and is used by the frontend to flag fields visibly.

Bump ``version`` to ship a breaking change without losing the ability to
replay historical records against the original schema.

Step 4 — Author the extraction prompt
-------------------------------------

Admin path: **Taxonomy → Prompt templates → Add**.

Pick ``purpose = extraction`` and link the row to the industry and
category. The resolver evaluates rows in order:

1. ``(industry, category, extraction)``
2. ``(industry, null, extraction)``
3. ``(null, null, extraction)``

Within a tier the highest ``version`` wins. The shipped construction
``Global extraction fallback v1`` row covers any category that has no
specific prompt yet — useful while iterating.

Prompts support these placeholders, rendered with
:py:meth:`str.format_map`:

* ``{transcript}`` — the (normalized) transcript text.
* ``{schema}`` — the resolved JSON Schema, pretty-printed.
* ``{dictionary}`` — newline list of normalization rules applied to the
  transcript.
* ``{industry}``, ``{category}`` — slugs of the resolved category.

Always tell the model to **return JSON only**. The platform parses the
response with ``json.loads`` and falls back to ``{}`` on failure.

Step 5 — Build a domain dictionary
----------------------------------

Admin path: **Taxonomy → Domain dictionary entries → Add**.

Each row maps ``term`` → ``normalized_term``. Scope it as narrowly as
possible:

* Category-scoped entries (industry + category) override
* industry-scoped entries (industry set, category empty), which override
* global entries (both empty).

Pre-deploy checklist for a new dictionary entry:

* The term must not contain regex metacharacters that the normalizer would
  treat specially — the lookup uses word-boundary matching, so spaces and
  hyphens are fine but ``(``, ``.``, ``?`` should be avoided in the term.
* If you have ``m3`` AND ``m``, both can coexist — longer matches win.

Step 6 — Author processing rules (cheap classifier)
---------------------------------------------------

Admin path: **Taxonomy → Processing rules → Add**.

A rule is a fast, deterministic classifier that scores
``(industry, category)`` from the transcript without an LLM call. Three
rule types:

* ``keyword_match`` — ``{"keywords": ["paid", "wages"], "weight": 0.5}``
* ``regex_match`` — ``{"pattern": "(\\b\\d+\\s*bags?)", "weight": 0.3}``
* ``phrase_score`` — ``{"phrases": ["paid the fundi"], "weight": 0.5}``

Aim for rule confidences in ``[0, 1]``. Repeated rules per category are
fine — multiple hits accumulate up to ``1.0``. When no rule clears the
``TAXONOMY_CLASSIFICATION_MIN_CONFIDENCE`` threshold, the pipeline falls
back to the LLM classifier if one is configured.

Step 7 — Wire up the AI provider (optional)
-------------------------------------------

The platform ships with a ``mock`` provider that returns a deterministic
stub. To use a real model, ensure an
:class:`~talk2record.ai.models.AIProvider` of category ``chat`` is enabled
in **AI → Providers** and an
:class:`~talk2record.ai.models.AITaskBinding` for ``extraction`` points at
it. If no key is configured, the pipeline transparently degrades to the
mock provider and logs a warning.

Step 8 — Verify in the dashboard
--------------------------------

Send a sample audio (or text) to the ingestion endpoint. Within the
record detail page you should see:

* the **Classification** panel populated with the detected category and
  confidence,
* the **Extracted data** panel rendering whatever fields the schema
  defined (the renderer is fully generic — no frontend code change is
  required),
* a **Validation errors** panel listing any failures and which schema
  required field is missing.

Step 9 — Optional: bake into the seed
-------------------------------------

For canonical industries that the platform should ship with, add the new
records to ``talk2record/seed/taxonomy_seed.py`` and rerun
``make seed``. The seed is idempotent:

* :class:`Industry` / :class:`Category` / :class:`ExtractionSchema` rows
  are upserted on their natural keys.
* :class:`PromptTemplate` / :class:`DomainDictionary` / :class:`ProcessingRule`
  rows are created-if-missing, so admin tweaks are never overwritten.
  Bump ``version`` to roll a new prompt without touching the existing one.

Reference
---------

* :class:`talk2record.taxonomy.models.Industry`
* :class:`talk2record.taxonomy.models.Category`
* :class:`talk2record.taxonomy.models.ExtractionSchema`
* :class:`talk2record.taxonomy.models.PromptTemplate`
* :class:`talk2record.taxonomy.models.DomainDictionary`
* :class:`talk2record.taxonomy.models.ProcessingRule`
* :class:`talk2record.taxonomy.services.orchestrator.ExtractionPipeline`
