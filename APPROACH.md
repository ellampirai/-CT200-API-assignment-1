# CT200 API — Engineering Approach

## 1. Architecture and Data Model

The application uses FastAPI for HTTP endpoints, Pydantic for data validation, SQLAlchemy for database operations, and SQLite for document versions, section nodes, named selections, and generation metadata.

Selections store snapshots of the selected node headings, body text, identifiers, and content hashes. This preserves the source content used when test cases are generated.

Generated output is currently stored as JSON in the SQLite database. This is a simple persistence choice; a separate JSON-file or NoSQL store would align more closely with the assignment's expected stack.

## 2. PDF Parsing Approach

The parser targets the supplied CT-200 manuals rather than arbitrary PDFs. It extracts section headings and body text and assigns hierarchy levels, identifiers, and content hashes.

Extraction quality must be checked against the original PDF. Duplicate headings, nested sections, tables, repeated headers, and content spanning pages can cause incorrect hierarchy or missing text.

The current implementation requires additional validation before claiming that every structural irregularity is handled correctly. OCR for scanned pages and reliable extraction of figures and captions also need verification.

## 3. Version Matching

The application stores document versions separately and compares section identifiers and content hashes.

This detects changes when the same logical section retains its identifier. If headings or hierarchy change, a logical section might instead appear as a removed node and a newly added node.

A stronger implementation could match normalized section paths and heading similarity, with manual review for ambiguous matches.

## 4. Selection and Traceability

A selection records its source version and snapshots the selected node identifiers, headings, body text, and hashes.

This preserves the original source content after another document version is ingested. Generated output should remain linked to the selection and the exact snapshots used to create it.

## 5. Test Case Generation and Validation

The current generator is a deterministic mock implementation, not a live LLM integration. It returns structured test cases and validates them using Pydantic, with a bounded retry loop for parsing or validation errors.

Some generated cases are generic and may not accurately reflect the selected requirement. They require review before use in medical-device QA.

A live LLM integration should request three to five concrete cases grounded in the selected manual sections, require structured JSON, validate every field, retry malformed responses within a limit, and report a clear failure if validation still fails.

## 6. Staleness and Impact Detection

Generated results are linked to the exact source selection and its content hashes. At retrieval time, the source hashes should be compared with corresponding nodes in the latest document version.

A missing or changed node should mark a generation as potentially stale. Hash comparison detects textual changes but does not assess clinical significance: a wording correction and a changed pressure threshold can both trigger staleness.

The v1-to-v2 workflow must be tested before staleness detection can be considered fully verified.

## 7. Decision Log

### Decision 1: Most likely silent failure

Incorrect PDF hierarchy or text extraction is the most likely silent failure. A tree may look correct while attaching text to the wrong parent or omitting a table row. I would detect this through page-by-page manual comparison, targeted parser tests, and checks for missing or duplicated content.

### Decision 2: Simplicity over correctness

For the prototype, I chose deterministic mock generation and a simple identifier/hash comparison strategy. In production, generic test cases and incorrect logical-node matching when headings or hierarchy change would be major weaknesses.

### Decision 3: Unsupported input

The generator does not treat an empty or text-free selection as valid input; it raises an error rather than generating cases without source evidence. Scanned PDFs, complex tables, and figures also need further validation before reliable extraction can be claimed.

## 8. Validation and Limitations

The existing automated test suite reports six passing tests. This does not prove that all PDF irregularities, live LLM failure cases, or versioning and staleness scenarios work correctly.

Additional tests should cover duplicate headings, malformed extraction structures, changed requirements, deleted nodes, malformed LLM output, and retrieval of stale generations.

## 9. Future Improvements

- Add OCR for scanned pages where required.
- Add at least three parser tests for actual CT-200 structural irregularities.
- Improve logical-node matching across document versions.
- Integrate a live LLM with structured-output validation and bounded retries.
- Complete retrieval by selection ID and node ID.
- Add an end-to-end v1-to-v2 staleness demonstration.
