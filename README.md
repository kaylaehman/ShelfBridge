<p align="center">
  <img src="docs/banner.png" alt="ShelfBridge — Export your Calibre library, everywhere." width="640">
</p>

# ShelfBridge

A [Calibre](https://calibre-ebook.com/) desktop plugin that exports your book
catalog to reading-tracker and productivity services — a Goodreads /
StoryGraph CSV, the [Hardcover](https://hardcover.app/) API, or a CSV uploaded
to Microsoft OneDrive.

## Supported services

| Service | What it does | Setup needed |
| --- | --- | --- |
| **Goodreads / StoryGraph** | Writes a CSV in the Goodreads import schema (StoryGraph accepts the same file) | An output folder |
| **OneDrive** | Builds the same CSV and uploads it to your OneDrive via Microsoft Graph | A free Microsoft app registration (see below) |
| **Hardcover** | Adds each book to your Hardcover library by ISBN, as *Read* or *Want to read* | A Hardcover API token |

> Books are marked **Read** when they have a rating or a `#read_date`, otherwise
> **To read** / **Want to read**.

## Features

- **CSV export** in the Goodreads / StoryGraph schema, written UTF-8 with a BOM
  so it opens cleanly in Excel.
- **OneDrive upload** over Microsoft Graph using device-code OAuth — no client
  secret, works behind firewalls.
- **Resilient API calls** — requests retry automatically with backoff and honor
  rate-limit `Retry-After` headers, so large libraries export without manual
  retries.
- **Automation** — export automatically when your library changes, or on a
  schedule (every 15 min through daily).

## Installation

Download the latest `shelf_bridge.zip` from the
[Releases](https://github.com/kaylaehman/ShelfBridge/releases) page, then either:

- **In Calibre:** *Preferences → Plugins → Load plugin from file*, and pick the
  ZIP. Restart Calibre when prompted.
- **From the command line:**

  ```text
  calibre-customize -a shelf_bridge.zip
  ```

A **ShelfBridge** button appears on the toolbar.

## Usage

1. Open **Preferences → Plugins → ShelfBridge → Configure**, or click the
   toolbar button's menu and choose **Configure Services…**.
2. Fill in the tab for each service you want to use and pick an output location.
3. Click the **ShelfBridge** toolbar button (default shortcut `Ctrl+Shift+E`)
   to export, or set up automation (below).

### Automating exports

On the **Automation** tab you can:

- **Export when the library changes** (debounced so rapid edits don't spam the
  services).
- **Export on a schedule** — every 15 / 30 / 60 / 360 minutes, or daily.
- Choose which services are included, and whether to show a notification after
  each automatic export.

## Setting up OneDrive

OneDrive upload uses your own free Microsoft *app registration*. You only do
this once.

### 1. Register an app in Entra ID (Azure)

1. Sign in to the [Azure Portal](https://portal.azure.com/) and open
   **Microsoft Entra ID → App registrations → New registration**.
2. Give it any name (e.g. `ShelfBridge`).
3. Under **Supported account types**, choose
   *Accounts in any organizational directory and personal Microsoft accounts*.
4. Under **Redirect URI**, select platform **Public client/native (mobile &
   desktop)** and enter:

   ```text
   https://login.microsoftonline.com/common/oauth2/nativeclient
   ```

5. Click **Register**.

### 2. Allow the device-code flow

1. In your new app, open **Authentication**.
2. Scroll to **Advanced settings → Allow public client flows** and set it to
   **Yes**. Save.

### 3. Grant the Graph permissions

1. Open **API permissions → Add a permission → Microsoft Graph → Delegated
   permissions**.
2. Add **`Files.ReadWrite`** and **`offline_access`**.

### 4. Connect it in ShelfBridge

1. Copy the **Application (client) ID** from the app's **Overview** page.
2. In ShelfBridge's **OneDrive** tab, paste it into **Client ID** and set the
   **OneDrive path** (must end in `.csv`, e.g. `/Calibre/catalog.csv`).
3. Click **Authorize**, then open
   [microsoft.com/devicelogin](https://microsoft.com/devicelogin) and enter the
   code shown. Once it says **Authorized**, you're done.

Use **Test Connection** to confirm, or **Revoke** to disconnect.

## Setting up Hardcover

1. Sign in at [hardcover.app](https://hardcover.app/) and copy your API token
   from your account settings.
2. Paste it into ShelfBridge's **Hardcover** tab and click **Test Connection**.

Books are matched by ISBN-13 (falling back to ISBN-10); titles without an ISBN
are skipped and reported.

## Security

- Service tokens and OAuth credentials are stored in your operating system's
  secure credential store (Windows Credential Manager / macOS Keychain /
  libsecret) when available. If no secure store is present, the plugin falls
  back to the preferences file and **logs a clear warning** — they are never
  silently written to plain text without notice.
- The plugin only **reads** your Calibre library; it never modifies it.

See [SECURITY.md](SECURITY.md) for details and how to report issues.

## Requirements

- Calibre 6.0 or newer (PyQt5 on 6.x, PyQt6 on 7.x — both supported).

## License

See [LICENSE](LICENSE).
