Feature: Executive cockpit and live demo readiness
  As a presenter
  I want a one-command, offline-safe demo with a pre-flight check
  So that nothing surprises me on stage

  Scenario: One-command start
    Given a clean clone
    When I run "./demo/demo.sh --offline"
    Then dependencies install into .venv
    And the 14-test suite passes
    And the cockpit starts on port 8000
    And the smoke test passes for every endpoint

  Scenario: The cockpit loads every panel independently
    When I open http://localhost:8000
    Then the header shows "operational · 32 facts indexed"
    And the KPI strip, capacity table, anomaly feed and forecast chart render
    And a failing panel shows "unavailable" without blanking the others

  Scenario: The grounding contract is checked before going live
    When "./demo/smoke_test.sh" runs
    Then an in-domain question returns citations that are all in the evidence
    And an off-domain question returns no evidence and no citations

  Scenario: The container is production-shaped
    When I run "docker compose up --build"
    Then the container runs as a non-root user
    And the HEALTHCHECK on /api/health reports healthy
    And setting PORT changes the listening port for PaaS hosts
