# RC Testing

This checklist is for local release-candidate dogfooding of `1.0.0-rc.1`.

## Onboarding checklist

1. Install the unsigned RC.
2. Launch the app.
3. Open Diagnostics and verify version and schema metadata.
4. Confirm offline demo mode is available.
5. Complete the [Quick Start](Quick_Start.md) workflow.
6. Import or open an example workspace.
7. Run an example backtest.
8. Open the volatility surface view.
9. Run a risk scenario.
10. Preview a report export.
11. Restart the app.
12. Confirm workspace state is still available where supported.
13. Generate a redacted diagnostic bundle preview.
14. Record issues with the [Support](Support.md) template.

## Usability evidence model

For each task, record:

- whether the task completed;
- time on task;
- errors or confusing steps;
- whether documentation was needed;
- blockers;
- whether the issue reproduces in offline mode.

Automation writes `final-e2e.json` and `desktop-smoke.json`; it does not count as
a human dogfood observation. Record human results in
`manual-rc-validation.json` only after actually completing the checklist.

## Final RC commands

```text
make final-e2e
make final-desktop-smoke
make clean-install-test
make upgrade-test
make reinstall-test
make recovery-test
make release-finalize
```

The current desktop harness validates packaged launch, sidecar health, fixture
support, and shutdown. Native file dialogs, a human-observed report export, and
workspace reopen through the packaged UI remain unvalidated until manually
recorded.
