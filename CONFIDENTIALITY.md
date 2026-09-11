# Confidentiality boundary

Only selected non-sensitive engineering evidence is public. Private source code, proprietary content, prompts, thresholds, customer data, credentials, internal endpoints, machine paths, operating volumes, commercial metrics and detailed production configuration remain private.

## Classification

- **Green:** approved test counts, scoped local benchmarks, aggregate quality-gate history and original synthetic examples, after source verification.
- **Yellow:** information that needs generalization or explicit owner approval before release. Excluded unless an approved generalized description is available.
- **Red:** secrets, personal/customer data, private source/content or commercially sensitive operating details. Never included.

The architecture descriptions here are approved generalized patterns. They reveal neither evaluator thresholds nor implementation details that would make the private system easier to game.

## Release controls

The public-release script checks common credential patterns, email addresses, machine paths, endpoint/query patterns, data schemas, links and generated assets. Error messages identify categories rather than reproducing matched sensitive values. Local source configuration is ignored and must not be tracked.

Automation is a guardrail, not a complete confidentiality classifier. Before every public commit, review the exact diff and the evidence classification. Never copy an entire private report or screenshot into this repository to make a chart. Extract only allowlisted values into public data.

The video fixture is original, unbranded and synthetic. Public CI needs no access to private repositories and stores no private-access credentials.
