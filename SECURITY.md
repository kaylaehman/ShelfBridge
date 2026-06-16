# Security

## Credential storage

ShelfBridge stores service tokens and OAuth credentials (Notion, Airtable,
Hardcover, OneDrive, and the optional agent API key) in your operating system's
secure credential store via the `keyring` library:

- **Windows** — Credential Manager
- **macOS** — Keychain
- **Linux** — Secret Service (libsecret / GNOME Keyring / KWallet)

If no functional keyring backend is available, ShelfBridge falls back to the
plugin's preferences file and logs a clearly-visible warning. In that mode the
tokens are **not** encrypted; install a keyring backend for secure storage.

Credentials are never written to the plain-text preferences JSON when a keyring
backend is present.

## Transport security

All outbound requests use HTTPS with certificate validation. When the vendored
`certifi` bundle is present it is used explicitly as the trust store.

## Agent safety

The optional Smart Export agent treats all book metadata (titles, authors,
comments) as untrusted input — it is sanitized and length-capped before reaching
the language model, and obvious prompt-injection patterns are suppressed.

The agent can only:

- read a fixed allowlist of non-sensitive preferences, and
- write a fixed allowlist of automation settings.

It can never read or write credentials, change the model backend, or modify the
Calibre library. Credential changes must go through the settings dialog.

## Reporting

Please report security issues privately to the maintainer rather than opening a
public issue.
