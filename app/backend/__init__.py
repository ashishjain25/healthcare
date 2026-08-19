"""Runs before any other backend submodule (every entry point — the FastAPI
app, scripts/seed_data.py, and the test suite — imports something under
`backend`, so this executes first).

Uses the OS certificate trust store instead of the `certifi`-bundled CA list
for all SSL contexts created in this process. Needed on machines where a
locally-installed root CA (e.g. an antivirus's HTTPS-scanning proxy, or a
corporate MITM proxy) is trusted by the OS/browser but isn't in certifi's
fixed bundle, which otherwise makes every outbound HTTPS call (OpenAI,
Langfuse, ChromaDB telemetry) fail with CERTIFICATE_VERIFY_FAILED even
though the same connection works fine outside Python. This still performs
full certificate validation — it just validates against a more complete,
OS-managed source of trust rather than a static list that can't know about
locally-installed roots.
"""
import truststore

truststore.inject_into_ssl()
