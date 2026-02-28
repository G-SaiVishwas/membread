#!/usr/bin/env python3
"""Simple test to verify basic functionality."""

import sys
sys.path.insert(0, ".")

from src.auth.jwt_authenticator import JWTAuthenticator
from src.governor.provenance_tracker import ProvenanceTracker
from src.models import PrivilegeLayer

def test_jwt():
    """Test JWT generation and validation."""
    print("Testing JWT Authentication...")
    auth = JWTAuthenticator()
    
    # Generate token
    token = auth.generate_token(
        tenant_id="test-tenant",
        user_id="test-user"
    )
    print(f"✓ Generated token: {token[:50]}...")
    
    # Validate token
    claims = auth.validate_token(token)
    assert claims["tenant_id"] == "test-tenant"
    assert claims["user_id"] == "test-user"
    print(f"✓ Validated token: {claims}")
    
def test_provenance():
    """Test provenance tracking."""
    print("\nTesting Provenance Tracking...")
    tracker = ProvenanceTracker()
    
    observation = "Test observation"
    metadata = {"source": "test"}
    
    # Generate hash
    hash1 = tracker.generate_hash(observation, metadata)
    print(f"✓ Generated hash: {hash1[:32]}...")
    
    # Verify hash
    assert tracker.verify_hash(observation, metadata, hash1)
    print("✓ Hash verification passed")
    
def test_models():
    """Test data models."""
    print("\nTesting Data Models...")
    from src.models import StoreResult, RecallResult, PrivilegeLayer
    
    result = StoreResult(
        observation_id="test-id",
        provenance_hash="test-hash",
        conflicts_resolved=0,
        nodes_created=1
    )
    print(f"✓ Created StoreResult: {result}")
    
    assert PrivilegeLayer.IMMUTABLE.value == 0
    assert PrivilegeLayer.ADMIN.value == 1
    assert PrivilegeLayer.USER.value == 2
    print("✓ Privilege layers correct")

if __name__ == "__main__":
    print("=" * 60)
    print("ChronosMCP - Simple Functionality Tests")
    print("=" * 60)
    
    try:
        test_jwt()
        test_provenance()
        test_models()
        
        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
