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

For the ZIP distribution, remove the extracted `Option Research Platform.app`
from the installation location. Retained application data, database backups,
exports, workspaces, and logs remain under Application Support. Copying the same
RC app back into place is a reinstall and must not create a second data root.
