# Uninstall

Deleting the unsigned macOS `.app` removes the application bundle only. It does not automatically
remove user data.

Retained by default:

- database
- workspaces
- exports
- reports
- logs
- cache
- crash events
- migration backups
- diagnostics bundles
- configuration and release metadata

Reinstalling the same compatible version should reuse retained app data, run database readiness
checks, and start without duplicate initialization. Cache may be cleared independently. Destructive
reset of all local application data is a separate recovery action and requires explicit
confirmation.
