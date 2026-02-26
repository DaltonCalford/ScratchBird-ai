# ScratchBird AI Specifications (Normative Draft Set)

This directory contains the fully fleshed implementation specification set for the ScratchBird AI platform expansion.

## Document Set

1. `01_ScratchBird_AI_Integration_Roadmap.md`
2. `02_LangChain_Adapter_Specification.md`
3. `03_LlamaIndex_Adapter_Specification.md`
4. `04_VectorStore_API_Specification.md`
5. `05_Hybrid_Retrieval_API_Specification.md`
6. `06_Tool_Calling_Schema_Specification.md`
7. `07_Plan_Introspection_API_Specification.md`
8. `08_AI_Execution_Mode_Specification.md`
9. `09_Deterministic_Audit_Bundle_Specification.md`
10. `10_Cluster_Aware_AI_Routing_Specification.md`
11. `11_Cross_Spec_Conformance_Matrix.md`
12. `12_External_Evidence_Traceability.md`

## Ordering Rules

1. `06` and `08` are mandatory before mutation enablement.
2. `07` is mandatory before `09` replay validation finalization.
3. `04` is mandatory before `05`.
4. `10` requires `04` and `05` local-node conformance completion.

## Implementation Rule

No feature may be marked production-ready unless:
1. its corresponding spec requirements are implemented,
2. conformance tests are automated and passing,
3. its row in `11_Cross_Spec_Conformance_Matrix.md` is complete.
4. its bound evidence gate in `12_External_Evidence_Traceability.md` is `PASS`.
