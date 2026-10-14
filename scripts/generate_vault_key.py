"""Run privately on the app owner's machine; copy output to Secrets, never to GitHub."""
import base64
import secrets
print(base64.b64encode(secrets.token_bytes(32)).decode())
