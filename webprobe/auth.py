"""Authentication & Session Setup (Epic 1).

PRD ref: prd.md > Epic 1 > Stories 1.1, 1.2, 1.3, 1.4, 1.5.
Spec ref: spec.md > Authentication & Session Setup (Epic 1).

This module is intentionally a stub at Item 5b. Concrete bodies for
`setup_form_login`, `setup_cookie_session`, `setup_baseline`,
`ephemeral_login_form`, `resolve_password`, `detect_shared_session`, and
`validate_auth_flags` land in Item 6 (split into 6a/6b).

The custom exception classes are declared here at Item 5b time because the
Engine's Phase 0.5 / Phase 1 helpers raise/catch `ConfigurationError`.
"""
from __future__ import annotations


# --- Custom Exception Hierarchy ------------------------------------------
# Per spec.md > Custom Exception Hierarchy.

class LoginDiscoveryError(Exception):
    """Form not found, multi-step login detected, etc.

    Message MUST be user-actionable (full sentence with remediation).
    Engine prints message verbatim to stderr before sys.exit(1).
    """


class LoginValidationError(Exception):
    """POST succeeded but login didn't (form re-rendered)."""


class PasswordResolutionError(Exception):
    """No flag, no env var, no TTY available."""


class ConfigurationError(Exception):
    """Inter-flag invariant violated (mutex / required-with).

    Engine catches at top level, exits with code 2.
    """


# --- Stub validators (concrete bodies land in Item 6) --------------------

def validate_auth_flags(args) -> None:
    """Phase 0.5 inter-flag validator.

    Item 6 will implement:
      - mutex: --cookie / --auth-form
      - mutex: --idor-baseline / --idor-baseline-form
      - required-with: --auth-form needs --auth-user
    """
    return None
