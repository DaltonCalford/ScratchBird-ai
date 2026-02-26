# ScratchBird AI Research Library

This directory stores downloaded reference artifacts used to implement and verify the ScratchBird AI specifications.

## Structure
- `00_index/`
  - `TASK_MATRIX.md`: Sub-task plan for bounded-context research execution
  - `SOURCES_INDEX.md`: Source metadata (URL, retrieval time, spec mapping)
  - `COMPARATIVE_PARITY_MATRIX.md`: Parity/exceed targets versus comparative tools
- `01_core_standards/`: RFCs, OpenAPI, JSON Schema, MCP core specifications
- `02_security_governance/`: NIST, OWASP, OpenTelemetry, W3C tracing references
- `03_frameworks_protocols/`: LangChain, LlamaIndex, MCP SDKs, comparative agent frameworks
- `04_vector_hybrid/`: Vector and hybrid retrieval implementation references
- `05_planning_introspection/`: Explain/profile/auditability references
- `06_comparative_tools/`: Academic and benchmark artifacts (HNSW, BEIR, RRF, ANN benchmarks)
- `07_local_clone_evidence/`: Curated snapshots copied from local database engine clones

## Notes
- Some primary URLs are blocked from CLI fetch in this environment (for example, HTTP 403/404). Fallback canonical mirrors or upstream repository specs are recorded in `00_index/SOURCES_INDEX.md`.
- Research is split into batches to keep context bounded and reproducible.
