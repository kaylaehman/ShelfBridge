## Task: Diagnose Export Failure

The user is reporting a problem with a ShelfBridge export.

Steps:
1. Call `shelf_bridge.last_export_summary` to get the most recent result.
2. Identify which services failed and read their `errors` arrays.
3. Call `shelf_bridge.validate_service` for each failed service.
4. Call `shelf_bridge.test_connection` for each failed service.
5. Based on the error messages, diagnose the root cause:
   - Auth errors → guide user to re-authorize in settings
   - Network errors → check connectivity, VPN, firewall
   - Schema errors → report which field mapping is mismatched
   - Rate limit errors → suggest retry interval
6. Propose a concrete fix. If it requires a pref change the agent can safely make
   (an allowlisted automation setting), use `shelf_bridge.set_pref`. If it requires a
   credential, direct the user to the settings dialog.
