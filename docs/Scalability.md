# Scalability

Sprint 12D documents scalability as measured local support, not a universal
guarantee. The current implementation adds:

- deterministic synthetic option-chain generation across multiple workload sizes;
- paginated chain querying with bounded page sizes;
- payload-size guards;
- worker-count guards;
- grid-size guards for scenario and surface-style matrices;
- resumable workload checkpoints for cancellation and restart validation.

Large, very-large, and endurance tiers remain opt-in so normal `make test`
stays practical.
