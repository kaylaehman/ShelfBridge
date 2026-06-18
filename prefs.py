"""Plugin preferences (JSONConfig wrapper) + all defaults.

NOTE on credentials: sensitive values (API tokens, OAuth token blobs) are NOT
stored here in plain text. They live in the OS credential store via
``auth.credential_store``. The keys still appear in ``defaults`` (as empty
placeholders) so the rest of the code can treat them uniformly; the runtime
overlays the real secret from the credential store when constructing adapters.
"""
from calibre.utils.config import JSONConfig

prefs = JSONConfig("plugins/shelf_bridge")

prefs.defaults = {
    # ── Global ────────────────────────────────────────────────────────────
    "default_service": "goodreads",
    "export_all": True,
    "export_filter": "",            # Calibre search string if export_all=False

    # ── Goodreads / StoryGraph ────────────────────────────────────────────
    "goodreads_output_path": "",
    "storygraph_output_path": "",   # distinct file from Goodreads (review M5)

    # ── Google Sheets ─────────────────────────────────────────────────────
    "google_client_id": "",
    "google_client_secret": "",     # secret -> credential_store
    "google_spreadsheet_id": "",
    "google_sheet_name": "Books",
    "google_token": {},             # secret -> credential_store ({access,refresh,expires_at})

    # ── OneDrive ──────────────────────────────────────────────────────────
    "onedrive_client_id": "",
    "onedrive_path": "/Calibre/catalog.csv",
    "onedrive_csv_schema": "goodreads",   # "goodreads" only for now
    "onedrive_token": {},           # secret -> credential_store ({access,refresh,expires_at})

    # ── Field mapping overrides (calibre_field -> service_column) ──────────
    "field_maps": {},

    # ── Automation ────────────────────────────────────────────────────────
    "auto_export_on_change": False,
    "auto_export_debounce_secs": 60,
    "schedule_enabled": False,
    "schedule_interval_minutes": 60,        # 15 / 30 / 60 / 360 / 1440
    "notify_on_auto_export": True,
    "enabled_services": [],                 # services included in headless export

    # ── Internal bookkeeping ──────────────────────────────────────────────
    "_last_export_summary": {},             # scrubbed summary of most recent export
}
