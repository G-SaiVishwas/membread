"""Comprehensive test suite for all connector endpoints."""

import requests
import json
from collections import Counter

BASE = "http://localhost:8000"
PASS = 0
FAIL = 0


def ok(msg):
    global PASS
    PASS += 1
    print(f"  PASS: {msg}")


def fail(msg):
    global FAIL
    FAIL += 1
    print(f"  FAIL: {msg}")


def get_token():
    r = requests.post(f"{BASE}/api/auth/token", json={"tenant_id": "test-tenant", "user_id": "test-user"})
    assert r.status_code == 200, f"Token endpoint failed: {r.status_code}"
    return r.json()["token"]


def main():
    global PASS, FAIL

    print("=" * 60)
    print("Membread Connector Integration Tests")
    print("=" * 60)

    # ── 1. Health ─────────────────────────────────────────────
    print("\n1. Health Check")
    r = requests.get(f"{BASE}/health")
    if r.status_code == 200 and r.json()["status"] == "healthy":
        ok(f"Health OK, version={r.json()['version']}")
    else:
        fail(f"Health failed: {r.status_code}")

    # ── 2. Auth Token ─────────────────────────────────────────
    print("\n2. Auth Token")
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    ok("Token obtained")

    # Test invalid auth
    r = requests.get(f"{BASE}/api/connectors")
    if r.status_code == 401:
        ok("No-auth returns 401")
    else:
        fail(f"No-auth returned {r.status_code}, expected 401")

    r = requests.get(f"{BASE}/api/connectors", headers={"Authorization": "Bearer bad-token"})
    if r.status_code == 401:
        ok("Bad token returns 401")
    else:
        fail(f"Bad token returned {r.status_code}, expected 401")

    # ── 3. List Connectors ────────────────────────────────────
    print("\n3. List Connectors")
    r = requests.get(f"{BASE}/api/connectors", headers=headers)
    if r.status_code != 200:
        fail(f"List connectors returned {r.status_code}")
        return

    connectors = r.json()["connectors"]
    if len(connectors) == 47:
        ok(f"47 connectors returned")
    else:
        fail(f"Expected 47 connectors, got {len(connectors)}")

    # Check fields
    required_fields = ["id", "name", "description", "category", "method", "status",
                       "last_sync", "memories_captured", "connected_at", "auth_method", "has_provider"]
    sample = connectors[0]
    missing = [f for f in required_fields if f not in sample]
    if not missing:
        ok(f"All {len(required_fields)} fields present")
    else:
        fail(f"Missing fields: {missing}")

    auth_counts = Counter(c.get("auth_method") for c in connectors)
    if auth_counts.get("oauth") == 12:
        ok("12 OAuth connectors")
    else:
        fail(f"Expected 12 OAuth, got {auth_counts.get('oauth')}")

    if auth_counts.get("api_key") == 11:
        ok("11 API-key connectors")
    else:
        fail(f"Expected 11 API-key, got {auth_counts.get('api_key')}")

    if auth_counts.get("webhook") == 10:
        ok("10 webhook connectors")
    else:
        fail(f"Expected 10 webhook, got {auth_counts.get('webhook')}")

    if auth_counts.get("external") == 14:
        ok("14 external connectors")
    else:
        fail(f"Expected 14 external, got {auth_counts.get('external')}")

    provider_count = sum(1 for c in connectors if c.get("has_provider"))
    if provider_count == 30:
        ok(f"30 have real provider implementations")
    else:
        fail(f"Expected 30 with providers, got {provider_count}")

    # All initially disconnected
    all_disconnected = all(c["status"] == "disconnected" for c in connectors)
    if all_disconnected:
        ok("All 47 initially disconnected")
    else:
        fail("Some connectors not initially disconnected")

    # ── 4. Connect External Connector ─────────────────────────
    print("\n4. Connect External Connector (chatgpt)")
    r = requests.post(f"{BASE}/api/connectors/connect", json={"connector_id": "chatgpt"}, headers=headers)
    if r.status_code == 200 and r.json()["status"] == "connected":
        ok("chatgpt connected immediately")
    else:
        fail(f"chatgpt connect: {r.status_code} {r.json()}")

    # Verify in listing
    r = requests.get(f"{BASE}/api/connectors", headers=headers)
    chatgpt = next(c for c in r.json()["connectors"] if c["id"] == "chatgpt")
    if chatgpt["status"] == "connected":
        ok("chatgpt shows as connected in listing")
    else:
        fail(f"chatgpt status: {chatgpt['status']}")

    # ── 5. Connect OAuth Provider ─────────────────────────────
    print("\n5. Connect OAuth Provider (hubspot)")
    r = requests.post(f"{BASE}/api/connectors/connect", json={"connector_id": "hubspot"}, headers=headers)
    if r.status_code == 200 and r.json()["status"] == "requires_oauth":
        data = r.json()
        ok(f"hubspot returns requires_oauth, endpoint={data['authorize_endpoint']}")
    else:
        fail(f"hubspot connect: {r.status_code} {r.json()}")

    # Test OAuth authorize without credentials
    r = requests.get(f"{BASE}/api/oauth/hubspot/authorize", headers=headers)
    if r.status_code == 400 and "credentials not configured" in r.json().get("detail", ""):
        ok("OAuth authorize without credentials returns 400")
    else:
        fail(f"OAuth authorize: {r.status_code} {r.json()}")

    # ── 6. Save OAuth Credentials ─────────────────────────────
    print("\n6. Save OAuth Credentials")
    r = requests.post(f"{BASE}/api/connectors/credentials", json={
        "provider_id": "hubspot",
        "client_id": "test-client-id-12345",
        "client_secret": "test-client-secret-67890",
    }, headers=headers)
    if r.status_code == 200 and r.json()["status"] == "saved":
        ok("Credentials saved for hubspot")
    else:
        fail(f"Save credentials: {r.status_code} {r.json()}")

    # Invalid provider
    r = requests.post(f"{BASE}/api/connectors/credentials", json={
        "provider_id": "nonexistent",
        "client_id": "x",
        "client_secret": "y",
    }, headers=headers)
    if r.status_code == 404:
        ok("Invalid provider returns 404")
    else:
        fail(f"Invalid provider: {r.status_code}")

    # ── 7. OAuth Authorize with Credentials ───────────────────
    print("\n7. OAuth Authorize with Credentials")
    r = requests.get(f"{BASE}/api/oauth/hubspot/authorize", headers=headers, allow_redirects=False)
    if r.status_code == 200:
        data = r.json()
        if "authorize_url" in data and "state" in data:
            url = data["authorize_url"]
            if "app.hubspot.com" in url and "test-client-id-12345" in url:
                ok(f"Authorize URL generated correctly")
            else:
                fail(f"Authorize URL missing expected parts: {url[:100]}")
        else:
            fail(f"Missing authorize_url or state: {data}")
    else:
        fail(f"Authorize: {r.status_code} {r.text}")

    # ── 8. Connect API-Key Provider ───────────────────────────
    print("\n8. Connect API-Key Provider (freshdesk)")
    r = requests.post(f"{BASE}/api/connectors/connect", json={"connector_id": "freshdesk"}, headers=headers)
    if r.status_code == 200 and r.json()["status"] == "requires_api_key":
        ok("freshdesk returns requires_api_key")
    else:
        fail(f"freshdesk connect: {r.status_code} {r.json()}")

    # Actually connect with API key
    r = requests.post(f"{BASE}/api/connectors/api-key", json={
        "connector_id": "freshdesk",
        "api_key": "test-freshdesk-api-key-12345",
        "config": {"subdomain": "mycompany"},
    }, headers=headers)
    if r.status_code == 200 and r.json()["status"] == "connected":
        ok("freshdesk connected via API key")
    else:
        fail(f"freshdesk API-key connect: {r.status_code} {r.json()}")

    # Verify in listing
    r = requests.get(f"{BASE}/api/connectors", headers=headers)
    freshdesk = next(c for c in r.json()["connectors"] if c["id"] == "freshdesk")
    if freshdesk["status"] == "connected":
        ok("freshdesk shows as connected in listing")
    else:
        fail(f"freshdesk status: {freshdesk['status']}")

    # Invalid provider for API key
    r = requests.post(f"{BASE}/api/connectors/api-key", json={
        "connector_id": "nonexistent",
        "api_key": "xxx",
    }, headers=headers)
    if r.status_code == 404:
        ok("Invalid provider for API key returns 404")
    else:
        fail(f"Invalid API-key provider: {r.status_code}")

    # ── 9. Connect Webhook-Only ───────────────────────────────
    print("\n9. Connect Webhook-Only (zapier)")
    r = requests.post(f"{BASE}/api/connectors/connect", json={"connector_id": "zapier"}, headers=headers)
    if r.status_code == 200 and r.json()["status"] == "connected":
        ok("zapier connected immediately")
    else:
        fail(f"zapier connect: {r.status_code} {r.json()}")

    # ── 10. Test other OAuth providers ────────────────────────
    print("\n10. Test Other OAuth Providers")
    oauth_ids = ["salesforce", "shopify", "intercom", "pagerduty", "lever",
                 "docusign-clm", "zendesk", "outreach", "salesloft", "workday", "servicenow"]
    for oid in oauth_ids:
        r = requests.post(f"{BASE}/api/connectors/connect", json={"connector_id": oid}, headers=headers)
        if r.status_code == 200 and r.json()["status"] == "requires_oauth":
            ok(f"{oid} -> requires_oauth")
        else:
            fail(f"{oid}: {r.status_code} {r.json()}")

    # ── 11. Test other API-key providers ──────────────────────
    print("\n11. Test Other API-Key Providers")
    apikey_ids = ["greenhouse", "marketo", "uipath", "automation-anywhere",
                  "sap", "oracle-scm", "coupa", "ironclad", "magento", "twilio-flex"]
    for aid in apikey_ids:
        r = requests.post(f"{BASE}/api/connectors/connect", json={"connector_id": aid}, headers=headers)
        if r.status_code == 200 and r.json()["status"] == "requires_api_key":
            ok(f"{aid} -> requires_api_key")
        else:
            fail(f"{aid}: {r.status_code} {r.json()}")

    # ── 12. Disconnect ────────────────────────────────────────
    print("\n12. Disconnect")
    for cid in ["chatgpt", "zapier", "freshdesk"]:
        r = requests.post(f"{BASE}/api/connectors/disconnect", json={"connector_id": cid}, headers=headers)
        if r.status_code == 200 and r.json()["status"] == "disconnected":
            ok(f"{cid} disconnected")
        else:
            fail(f"{cid} disconnect: {r.status_code} {r.json()}")

    # Verify all back to disconnected
    r = requests.get(f"{BASE}/api/connectors", headers=headers)
    connected = [c for c in r.json()["connectors"] if c["status"] != "disconnected"]
    if not connected:
        ok("All connectors back to disconnected after cleanup")
    else:
        # hubspot might still be pending_oauth from earlier test
        non_clean = [(c["id"], c["status"]) for c in connected]
        # That's expected for hubspot
        expected_pending = [c for c in connected if c["status"] == "pending_oauth"]
        if len(expected_pending) == len(connected):
            ok(f"Only pending_oauth states remain ({len(expected_pending)})")
        else:
            fail(f"Unexpected states: {non_clean}")

    # ── 13. Non-OAuth provider for OAuth endpoint ─────────────
    print("\n13. Edge Cases")
    # freshdesk is an API-key provider (in provider registry but not OAuth)
    r = requests.get(f"{BASE}/api/oauth/freshdesk/authorize", headers=headers)
    if r.status_code == 400:
        ok("Non-OAuth provider at OAuth endpoint returns 400")
    else:
        fail(f"Non-OAuth at OAuth endpoint: {r.status_code}")

    # Non-existent provider
    r = requests.get(f"{BASE}/api/oauth/nonexistent/authorize", headers=headers)
    if r.status_code == 404:
        ok("Non-existent provider at OAuth endpoint returns 404")
    else:
        fail(f"Non-existent at OAuth endpoint: {r.status_code}")

    # ── 14. Poll endpoint ─────────────────────────────────────
    print("\n14. Manual Poll Trigger")
    # Not connected -> should return 400
    r = requests.post(f"{BASE}/api/connectors/freshdesk/poll", headers=headers)
    if r.status_code == 400:
        ok("Poll on disconnected connector returns 400")
    else:
        fail(f"Poll on disconnected: {r.status_code}")

    # Non-existent provider
    r = requests.post(f"{BASE}/api/connectors/nonexistent/poll", headers=headers)
    if r.status_code == 404:
        ok("Poll on non-existent returns 404")
    else:
        fail(f"Poll on non-existent: {r.status_code}")

    # ── 15. Config endpoint ───────────────────────────────────
    print("\n15. Connector Config")
    # First connect something
    requests.post(f"{BASE}/api/connectors/connect", json={"connector_id": "chatgpt"}, headers=headers)
    r = requests.post(f"{BASE}/api/connectors/chatgpt/config", json={
        "connector_id": "chatgpt",
        "config": {"custom_key": "custom_value"},
    }, headers=headers)
    if r.status_code == 200:
        ok("Config update OK")
    else:
        fail(f"Config update: {r.status_code}")

    # ── 16. Tenant isolation ──────────────────────────────────
    print("\n16. Tenant Isolation")
    r2 = requests.post(f"{BASE}/api/auth/token", json={"tenant_id": "other-tenant", "user_id": "other-user"})
    token2 = r2.json()["token"]
    headers2 = {"Authorization": f"Bearer {token2}"}

    r = requests.get(f"{BASE}/api/connectors", headers=headers2)
    connectors2 = r.json()["connectors"]
    chatgpt2 = next(c for c in connectors2 if c["id"] == "chatgpt")
    if chatgpt2["status"] == "disconnected":
        ok("Other tenant sees chatgpt as disconnected (tenant isolation)")
    else:
        fail(f"Tenant isolation failed: chatgpt status for other tenant = {chatgpt2['status']}")

    # Cleanup
    requests.post(f"{BASE}/api/connectors/disconnect", json={"connector_id": "chatgpt"}, headers=headers)

    # ── 17. Store, Recall, Stats (existing endpoints) ─────────
    print("\n17. Existing Endpoints")
    r = requests.post(f"{BASE}/api/memory/store", json={
        "observation": "Customer John signed a $50k deal with Acme Corp",
        "metadata": {"agent_id": "test-agent", "session_id": "sess-001"}
    }, headers=headers)
    if r.status_code == 200:
        ok("Store memory OK")
    else:
        fail(f"Store: {r.status_code}")

    r = requests.post(f"{BASE}/api/memory/recall", json={"query": "John deal"}, headers=headers)
    if r.status_code == 200:
        ok(f"Recall OK: {len(r.json().get('memories', []))} results")
    else:
        fail(f"Recall: {r.status_code}")

    r = requests.get(f"{BASE}/api/stats", headers=headers)
    if r.status_code == 200:
        stats = r.json()
        ok(f"Stats OK: {stats.get('total_memories', 0)} memories")
    else:
        fail(f"Stats: {r.status_code}")

    r = requests.get(f"{BASE}/api/activity", headers=headers)
    if r.status_code == 200:
        activities = r.json().get("items", [])
        ok(f"Activity log OK: {len(activities)} entries")
        # Check connector activities are logged
        connector_activities = [a for a in activities if a.get("type") == "connector"]
        if connector_activities:
            ok(f"Connector activities logged: {len(connector_activities)}")
        else:
            fail("No connector activities in log")
    else:
        fail(f"Activity: {r.status_code}")

    # ── Summary ───────────────────────────────────────────────
    print("\n" + "=" * 60)
    print(f"RESULTS: {PASS} passed, {FAIL} failed")
    print("=" * 60)

    if FAIL > 0:
        exit(1)


if __name__ == "__main__":
    main()
