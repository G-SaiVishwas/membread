#!/usr/bin/env python3
"""Generate JWT tokens for testing ChronosMCP."""

import sys
sys.path.insert(0, ".")

from src.auth.jwt_authenticator import JWTAuthenticator
from uuid import uuid4

def main():
    """Generate test JWT tokens."""
    print("=" * 60)
    print("ChronosMCP - JWT Token Generator")
    print("=" * 60)
    
    auth = JWTAuthenticator()
    
    # Generate tokens for different scenarios
    scenarios = [
        ("Demo User", "demo-tenant", "demo-user"),
        ("Test Tenant A", str(uuid4()), str(uuid4())),
        ("Test Tenant B", str(uuid4()), str(uuid4())),
    ]
    
    print("\nGenerated Tokens:\n")
    
    for name, tenant_id, user_id in scenarios:
        token = auth.generate_token(tenant_id, user_id, expires_in_hours=24)
        print(f"{name}:")
        print(f"  Tenant ID: {tenant_id}")
        print(f"  User ID: {user_id}")
        print(f"  Token: {token}")
        print()
    
    print("=" * 60)
    print("Copy a token and use it in your MCP tool calls")
    print("=" * 60)

if __name__ == "__main__":
    main()
