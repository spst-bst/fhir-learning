# Module 6 — SMART on FHIR: Patient Launch and Backend Services Auth

## Concepts

FHIR defines the data shape; **SMART on FHIR** (built on OAuth2 +
OpenID Connect) defines how an app gets authorized to access it. Three
launch flows show up in practice, and they answer different questions:

- **EHR launch**: the app is launched *from inside* the EHR (a button in
  Epic/Cerner's UI), which hands it a `launch` parameter carrying context
  — which patient, which encounter, who's logged in — the EHR already
  knows. The app redeems `launch` for that context as part of the OAuth
  exchange. This is how most clinician-facing SMART apps actually run.
- **Standalone launch**: the app is opened directly (its own URL, not
  from inside the EHR), so there's no context yet — the app sends the
  user through the authorization server itself, which prompts them to
  pick a patient (and FHIR server, in a sandbox) before anything is
  granted. Same OAuth machinery, context acquired differently.
- **Backend services**: no end user at all — system-to-system, like a
  nightly batch job pulling data for Module 5's bulk export. There's no
  browser redirect to authenticate a human, so the client authenticates
  *itself* with a **signed JWT** instead of a client secret: it holds a
  private key (registered with the authorization server up front as a
  public key / JWKS), and for every token request it mints a short-lived
  JWT asserting its own identity, signs it with that private key, and
  trades it for an access token via `grant_type=client_credentials`.

**Scopes** gate what the resulting token can do: `patient/Observation.read`
(this patient's observations, user-launch context), `user/*.read`
(everything this logged-in user can see), `system/Patient.read` (backend
services — no user, so `system/` instead of `patient/` or `user/`).
Always request the narrowest scope the integration actually needs.

**Why a signed JWT instead of a plain client secret:** a secret is a
shared value both sides store — if either side's storage leaks, it's
compromised, and it travels over the wire on every request. A JWT
assertion is signed with a private key that *never leaves the client*; the
server only ever holds the corresponding public key, and can't forge a
request on the client's behalf even if its own storage were compromised.
This module builds and signs that assertion by hand so the shape stops
being a black box.

This module works directly on the request/response shapes (claims dicts,
token responses) rather than a live authorization server — same posture
as Modules 3-5. The one exception is the standalone-launch walkthrough
below, which is inherently a browser flow and worth seeing once with your
own eyes.

## Standalone launch walkthrough (do this once, by hand)

1. Open https://launch.smarthealthit.org in a browser.
2. Leave the launch type as **Provider EHR Launch** or switch to
   **Patient Standalone Launch** — try standalone first: it's closer to
   "app opened on its own," which is the scenario this module's code
   covers conceptually.
3. Pick a sample patient, pick scopes (`patient/Patient.read`,
   `patient/Observation.read`), and launch. Watch the URL bar: you'll see
   a redirect to an `/authorize` endpoint, then a redirect back to the
   app's `redirect_uri` with a `code` parameter — the authorization code.
4. Notice there's no app to actually receive that code here (the sandbox
   launcher just shows you the exchange) — the point is to *see* the
   redirect dance once, since the code below starts one step later, at
   "I already have a signed assertion, now I trade it for a token."

## Why it matters in practice

A nightly ingestion job (Module 5's `$export`, or a per-partner API pull)
has no human sitting at a browser to grant consent each time — it has to
authenticate itself, unattended, on a schedule. Backend services auth is
exactly that: a long-lived credential (the private key) that mints
short-lived, narrowly-scoped access tokens on demand, each one cheap to
revoke or rotate without touching the key itself. Getting the JWT
assertion's claims wrong (missing `jti`, an `exp` that's too long, a
mismatched `aud`) is a common real-world integration failure mode when
standing up a new partner feed.

## 3 Key Takeaways

1. **"EHR launch has context already; standalone launch has to ask for
   it; backend services has no user to ask at all."** Same OAuth2 core,
   three different starting points — knowing which one a given
   integration needs is most of the design question.
2. **"Backend services auth trades a shared secret for a signed
   assertion — the private key never leaves the client."** Same
   motivation as asymmetric auth anywhere: the verifier only needs the
   public half, so a breach of the server's stored credentials can't be
   used to impersonate the client.
3. **"`jti` and a short `exp` on the assertion prevent replay — the
   opposite problem from Module 4's idempotent id."** There, you *wanted*
   the same content to produce the same id so retries were safe. Here,
   you want every assertion to be usable *exactly once*, so a captured
   JWT can't be replayed after the fact — same JWT mechanics, opposite
   intent.

## What to do

No running authorization server needed for the coding exercises — they
work directly on claims dicts, signed JWT strings, and token response
JSON, plus a locally-generated RSA keypair (a test fixture, not a real
registered client). Open `exercises/smart_auth.py`, fill in the TODOs,
then:

```bash
make test-06
```

Each function dumps its inputs/outputs as JSON when `DEBUG = True` (the
default) — pytest hides it unless you pass `-s`.

Hints before answers — ask if you get stuck for more than ~10 minutes on
any one function. Don't open `solutions/` until you've got a passing (or
honestly-stuck) attempt.
