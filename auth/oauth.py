"""Generic OAuth2 PKCE helper (local-redirect style).

Not used by OneDrive (which uses the device-code flow in ``graph_token``);
provided as a small reusable helper for future API-based services. Stdlib only.
"""
import base64
import hashlib
import os
import urllib.parse


def generate_pkce_pair():
    """Return (code_verifier, code_challenge) for an S256 PKCE exchange."""
    verifier = base64.urlsafe_b64encode(os.urandom(40)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    return verifier, challenge


def build_authorize_url(auth_endpoint, client_id, redirect_uri, scopes, challenge, state):
    q = urllib.parse.urlencode({
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": " ".join(scopes),
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
    })
    return f"{auth_endpoint}?{q}"
