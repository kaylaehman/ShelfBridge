## Task: Configure Automated Export

The user wants to set up automatic exports on a schedule or on library change.

Steps:
1. Call `shelf_bridge.get_prefs` to read current automation settings.
2. Clarify with the user:
   - Which trigger: library change, schedule, or both?
   - Which services to include?
   - For schedules: what interval? (15 min / 30 min / 1 hour / 6 hours / daily)
3. Validate that all target services pass `shelf_bridge.validate_service`.
4. Apply the changes using `shelf_bridge.set_pref`:
   - `auto_export_on_change`: true/false
   - `schedule_enabled`: true/false
   - `schedule_interval_minutes`: integer
   - `enabled_services`: list of service IDs
5. Confirm the new configuration back to the user in plain language.

Note: Do not enable scheduling for a service that fails validation.
