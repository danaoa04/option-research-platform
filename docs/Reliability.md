# Reliability

Sprint 12D adds a lightweight reliability harness for:

- cancellation acknowledgement
- checkpoint creation
- deterministic resume
- bounded worker usage
- readiness blocking on failed measured budgets

Long-duration endurance, desktop-route churn, and crash-under-load sweeps remain
explicitly unvalidated unless the opt-in environment runs them. They should not
be reported as passed otherwise.
