<p align="center">
  <img src="docs/banner.png" alt="ShelfBridge — Export your Calibre library, everywhere." width="640">
</p>

# ShelfBridge

A [Calibre](https://calibre-ebook.com/) desktop plugin that exports your book
catalog to reading-tracker and productivity services — CSV (Goodreads /
StoryGraph), API-based services (Notion, Airtable, Hardcover), and Microsoft
OneDrive (CSV upload via Microsoft Graph).

## Features

- **CSV export** — Goodreads / StoryGraph import schema, written UTF-8 with BOM.
- **API export** — Notion databases, Airtable bases, Hardcover (by ISBN).
  Re-exports **upsert by Calibre ID** instead of creating duplicates.
- **OneDrive** — uploads the CSV via Microsoft Graph (device-code OAuth, no
  client secret needed).
- **Automation** — export when your library changes, or on a schedule.
- **Smart Export (agent)** — an optional in-process agent that validates,
  tests, and runs exports for you.

## Security

- Service tokens and OAuth credentials are stored in your operating system's
  secure credential store (Windows Credential Manager / macOS Keychain /
  libsecret) when available, with a clearly-logged fallback otherwise. They are
  **not** written to the plugin's plain-text preferences file.
- The agent layer treats all book metadata as untrusted input and runs behind
  an allowlist of writable preferences. See [SECURITY.md](SECURITY.md).

## Installation

Download the latest `shelf_bridge.zip` from Releases, then:

```
calibre-customize -a shelf_bridge.zip
```

Or in Calibre: **Preferences → Plugins → Load plugin from file**.

## Usage

1. **Preferences → Plugins → ShelfBridge → Configure**, or click the toolbar
   button and choose **Configure Services…**.
2. Enter credentials for the services you want and pick an output location.
3. Click the **ShelfBridge** toolbar button (default shortcut `Ctrl+Shift+E`)
   to export.

## Requirements

- Calibre 6.0 or newer (PyQt5 on 6.x, PyQt6 on 7.x — both supported).

## License

See [LICENSE](LICENSE).
