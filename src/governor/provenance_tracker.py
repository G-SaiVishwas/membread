"""Provenance tracking with cryptographic hashing."""

import hashlib
import json
from datetime import datetime
import structlog

logger = structlog.get_logger()


class ProvenanceTracker:
    """
    Track provenance of observations using cryptographic hashing.
    """

    def generate_hash(self, observation: str, metadata: dict) -> str:
        """
        Generate SHA-256 hash for provenance tracking.

        Args:
            observation: Observation text
            metadata: Observation metadata

        Returns:
            Hex-encoded SHA-256 hash
        """
        # Create deterministic string representation (exclude timestamp for consistency)
        data = {
            "observation": observation,
            "metadata": {k: v for k, v in metadata.items() if k != "timestamp"},
        }

        # Sort keys for deterministic hashing
        data_str = json.dumps(data, sort_keys=True)

        # Generate SHA-256 hash
        hash_obj = hashlib.sha256(data_str.encode("utf-8"))
        provenance_hash = hash_obj.hexdigest()

        logger.debug(
            "provenance_hash_generated",
            hash=provenance_hash[:16] + "...",
            observation_length=len(observation),
        )

        return provenance_hash

    def verify_hash(self, observation: str, metadata: dict, expected_hash: str) -> bool:
        """
        Verify provenance hash.

        Args:
            observation: Observation text
            metadata: Observation metadata
            expected_hash: Expected hash value

        Returns:
            True if hash matches, False otherwise
        """
        computed_hash = self.generate_hash(observation, metadata)
        matches = computed_hash == expected_hash

        if not matches:
            logger.warning(
                "provenance_hash_mismatch",
                expected=expected_hash[:16] + "...",
                computed=computed_hash[:16] + "...",
            )

        return matches
