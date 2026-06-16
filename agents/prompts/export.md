## Task: Export Library

The user wants to export their Calibre library to one or more services.

Steps:
1. Call `shelf_bridge.list_adapters` to confirm available services.
2. Identify which services the user wants. If ambiguous, ask.
3. For each target service, call `shelf_bridge.validate_service`.
4. For each valid service, call `shelf_bridge.test_connection`.
5. If all checks pass, call `shelf_bridge.export` with the list of service IDs.
6. Report the result: books exported per service, destination, any errors.

If any service fails validation or connection, report it clearly and ask the user
whether to proceed with the remaining services or abort.
