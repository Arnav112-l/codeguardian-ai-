from __future__ import annotations

from typing import Any

Scenario = dict[str, Any]

SCENARIO_BANK: dict[str, list[Scenario]] = {
    "task_triage": [
        {
            "id": "triage-001",
            "context": "After deploying auth-service v2.1, users report HTTP 500 during login.",
            "available_actions": ["categorize_ticket", "set_severity", "route_oncall"],
            "ground_truth": {
                "category": "bug",
                "severity": "high",
                "module_label": "auth-service",
                "oncall_routing": "backend-oncall",
            },
        },
        {
            "id": "triage-002",
            "context": "Product asks for CSV export in the analytics dashboard for paid users.",
            "available_actions": ["categorize_ticket", "set_severity", "route_oncall"],
            "ground_truth": {
                "category": "feature",
                "severity": "medium",
                "module_label": "analytics-ui",
                "oncall_routing": "product-oncall",
            },
        },
        {
            "id": "triage-003",
            "context": "Onboarding docs do not mention required environment variables for local setup.",
            "available_actions": ["categorize_ticket", "set_severity", "route_oncall"],
            "ground_truth": {
                "category": "docs",
                "severity": "low",
                "module_label": "developer-portal",
                "oncall_routing": "devrel-oncall",
            },
        },
        {
            "id": "triage-004",
            "context": "A customer asks whether webhook retries are exponential or fixed interval.",
            "available_actions": ["categorize_ticket", "set_severity", "route_oncall"],
            "ground_truth": {
                "category": "question",
                "severity": "medium",
                "module_label": "webhooks",
                "oncall_routing": "support-oncall",
            },
        },
        {
            "id": "triage-005",
            "context": "Payment captures are duplicated under heavy load, leading to double charging.",
            "available_actions": ["categorize_ticket", "set_severity", "route_oncall"],
            "ground_truth": {
                "category": "bug",
                "severity": "critical",
                "module_label": "payment-gateway",
                "oncall_routing": "payments-oncall",
            },
        },
    ],
    "task_security_audit": [
        {
            "id": "sec-001",
            "context": "Flask handler renders user input into HTML without escaping.",
            "available_actions": ["report_findings"],
            "ground_truth": {
                "findings": [
                    {
                        "cwe_id": "CWE-79",
                        "line_number": 28,
                        "severity": "high",
                        "fix_description": "Escape HTML content and use template auto-escaping.",
                    }
                ]
            },
        },
        {
            "id": "sec-002",
            "context": "SQL query is built by concatenating a request parameter into SELECT statement.",
            "available_actions": ["report_findings"],
            "ground_truth": {
                "findings": [
                    {
                        "cwe_id": "CWE-89",
                        "line_number": 44,
                        "severity": "critical",
                        "fix_description": "Use parameterized queries via DB driver placeholders.",
                    }
                ]
            },
        },
        {
            "id": "sec-003",
            "context": "Function deserializes attacker-controlled pickle bytes from a queue payload.",
            "available_actions": ["report_findings"],
            "ground_truth": {
                "findings": [
                    {
                        "cwe_id": "CWE-502",
                        "line_number": 13,
                        "severity": "critical",
                        "fix_description": "Replace pickle with a safe serialization format like JSON.",
                    }
                ]
            },
        },
        {
            "id": "sec-004",
            "context": "Password reset token generator uses random.random() and fixed timestamp salt.",
            "available_actions": ["report_findings"],
            "ground_truth": {
                "findings": [
                    {
                        "cwe_id": "CWE-330",
                        "line_number": 72,
                        "severity": "high",
                        "fix_description": "Use secrets.token_urlsafe for cryptographically secure randomness.",
                    }
                ]
            },
        },
        {
            "id": "sec-005",
            "context": "API endpoint checks only username equality and skips authorization on role.",
            "available_actions": ["report_findings"],
            "ground_truth": {
                "findings": [
                    {
                        "cwe_id": "CWE-862",
                        "line_number": 57,
                        "severity": "high",
                        "fix_description": "Add explicit role-based authorization checks before processing.",
                    }
                ]
            },
        },
    ],
    "task_dependency_update": [
        {
            "id": "dep-001",
            "context": "Service uses requests==2.25.0 and urllib3 transitive vulnerabilities are reported.",
            "available_actions": ["recommend_upgrade"],
            "ground_truth": {
                "updated_version": "requests==2.32.3",
                "breaking_changes": [
                    "Re-test proxy and SSL configuration defaults.",
                    "Validate timeout handling behavior in integrations.",
                ],
                "migration_description": "Upgrade requests to 2.32.3, run regression tests for proxy/SSL behavior, and validate timeout handling in all external HTTP integrations before rollout.",
            },
        },
        {
            "id": "dep-002",
            "context": "FastAPI app pins pydantic==1.10.13 while team is standardizing on Pydantic v2.",
            "available_actions": ["recommend_upgrade"],
            "ground_truth": {
                "updated_version": "pydantic==2.12.5",
                "breaking_changes": [
                    "Replace parse_obj with model_validate.",
                    "Update validator decorators to field_validator/model_validator.",
                ],
                "migration_description": "Move to Pydantic 2.12.5, refactor validation API calls, and run full schema compatibility tests for request and response models.",
            },
        },
        {
            "id": "dep-003",
            "context": "Inference worker runs openai==0.28.0 but project uses OpenAI Python 1.x interface.",
            "available_actions": ["recommend_upgrade"],
            "ground_truth": {
                "updated_version": "openai==2.30.0",
                "breaking_changes": [
                    "Client construction changes to OpenAI(...).",
                    "Use client.chat.completions.create instead of legacy calls.",
                ],
                "migration_description": "Upgrade openai to 2.30.0, switch to OpenAI client instantiation, and update completion call sites with the new response object handling.",
            },
        },
        {
            "id": "dep-004",
            "context": "Pytest is pinned at 6.x and test suite relies on newer plugin APIs.",
            "available_actions": ["recommend_upgrade"],
            "ground_truth": {
                "updated_version": "pytest==9.0.2",
                "breaking_changes": [
                    "Revisit deprecated fixture usage patterns.",
                    "Update plugin compatibility constraints.",
                ],
                "migration_description": "Upgrade pytest to 9.0.2, fix deprecated fixture usage, and verify third-party plugin compatibility in CI before merging.",
            },
        },
        {
            "id": "dep-005",
            "context": "Async API stack uses httpx==0.23.0 and wants latest patch-level stability fixes.",
            "available_actions": ["recommend_upgrade"],
            "ground_truth": {
                "updated_version": "httpx==0.28.1",
                "breaking_changes": [
                    "Review timeout defaults and transport configuration.",
                    "Validate retry middleware behavior with new dependency versions.",
                ],
                "migration_description": "Upgrade httpx to 0.28.1, validate timeout and transport behavior, and run load tests to confirm retry middleware remains stable.",
            },
        },
    ],
}
