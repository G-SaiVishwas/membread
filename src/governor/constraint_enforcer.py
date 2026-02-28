"""Constraint enforcer for privilege layers and injection detection."""

import re
import asyncpg
from typing import List
import structlog

from src.models import (
    Operation,
    ValidationResult,
    Constraint,
    PrivilegeLayer,
    ValidationError,
)

logger = structlog.get_logger()


class ConstraintEnforcer:
    """
    Enforce Layer 0/1/2 privilege constraints and detect injection attacks.
    """

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
        self.constraints: List[Constraint] = []

    async def load_constraints(self) -> None:
        """Load Layer 0 immutable constraints from database."""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT id, constraint_type, rule, description FROM constraints"
                )

                self.constraints = [
                    Constraint(
                        id=str(row["id"]),
                        constraint_type=row["constraint_type"],
                        rule=row["rule"],
                        description=row["description"],
                    )
                    for row in rows
                ]

                logger.info("constraints_loaded", count=len(self.constraints))

        except Exception as e:
            logger.error("load_constraints_failed", error=str(e))
            raise

    async def enforce_constraints(
        self,
        operation: Operation,
        constraints: List[Constraint] = None,
    ) -> ValidationResult:
        """
        Validate operation against immutable constraints.

        Args:
            operation: Operation to validate
            constraints: Optional specific constraints (uses loaded if None)

        Returns:
            ValidationResult indicating pass/fail and reasons
        """
        constraints = constraints or self.constraints
        errors = []
        warnings = []

        # Check privilege layer violations
        if operation.privilege_layer == PrivilegeLayer.USER:
            # Layer 2 operations cannot override Layer 0/1
            layer_0_violations = self._check_layer_0_violations(operation, constraints)
            if layer_0_violations:
                errors.extend(layer_0_violations)

        # Check for prompt injection
        if "text" in operation.data or "observation" in operation.data:
            text = operation.data.get("text") or operation.data.get("observation", "")
            if self._detect_prompt_injection(text, constraints):
                errors.append("Prompt injection detected")

        # Check for SQL injection
        if self._detect_sql_injection(operation.data, constraints):
            errors.append("SQL injection detected")

        # Check observation length
        if "text" in operation.data:
            max_length = self._get_max_observation_length(constraints)
            if len(operation.data["text"]) > max_length:
                errors.append(f"Observation exceeds maximum length of {max_length}")

        valid = len(errors) == 0

        if not valid:
            logger.warning(
                "constraint_validation_failed",
                operation_type=operation.operation_type,
                privilege=operation.privilege_layer.name,
                errors=errors,
            )

        return ValidationResult(valid=valid, errors=errors, warnings=warnings)

    def _check_layer_0_violations(
        self,
        operation: Operation,
        constraints: List[Constraint],
    ) -> List[str]:
        """Check if Layer 2 operation violates Layer 0 constraints."""
        violations = []

        # Example: Check if trying to modify immutable user properties
        if operation.operation_type == "update" and "preferences" in operation.data:
            prefs = operation.data["preferences"]

            # Check against Layer 0 constraints
            for constraint in constraints:
                if constraint.constraint_type == "immutable_preference":
                    immutable_keys = constraint.rule.get("keys", [])
                    for key in immutable_keys:
                        if key in prefs:
                            violations.append(
                                f"Cannot modify immutable preference: {key}"
                            )

        return violations

    def _detect_prompt_injection(self, text: str, constraints: List[Constraint]) -> bool:
        """Detect prompt injection patterns."""
        text_lower = text.lower()

        for constraint in constraints:
            if constraint.constraint_type == "prompt_injection_pattern":
                patterns = constraint.rule.get("patterns", [])
                for pattern in patterns:
                    if pattern.lower() in text_lower:
                        logger.warning(
                            "prompt_injection_detected",
                            pattern=pattern,
                            text_preview=text[:100],
                        )
                        return True

        return False

    def _detect_sql_injection(self, data: dict, constraints: List[Constraint]) -> bool:
        """Detect SQL injection patterns."""
        # Check all string values in data
        for value in data.values():
            if isinstance(value, str):
                value_upper = value.upper()

                for constraint in constraints:
                    if constraint.constraint_type == "sql_injection_pattern":
                        patterns = constraint.rule.get("patterns", [])
                        for pattern in patterns:
                            if re.search(pattern, value_upper, re.IGNORECASE):
                                logger.warning(
                                    "sql_injection_detected",
                                    pattern=pattern,
                                    value_preview=value[:100],
                                )
                                return True

        return False

    def _get_max_observation_length(self, constraints: List[Constraint]) -> int:
        """Get maximum observation length from constraints."""
        for constraint in constraints:
            if constraint.constraint_type == "max_observation_length":
                return constraint.rule.get("max_length", 10000)
        return 10000  # Default
