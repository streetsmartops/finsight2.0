Feature: Cost anomaly detection and attribution (Cost-Mngt-App)
  As a FinOps lead
  I want spend spikes flagged with a baseline and a suspected cause
  So that I can act on waste and explain bill movements to finance

  Background:
    Given the synthetic estate generated with seed 42
    And 5 incidents injected into the cost data

  Scenario: Every injected incident is recovered
    When Cost-Mngt-App scores each product x region x service stream
    And uses a trailing 21-day median and MAD baseline
    Then points with robust z >= 4.0 are flagged
    And all 5 distinct suspected causes appear among the anomalies
    # test_cost_app_catches_injected_anomalies

  Scenario: A spike does not poison its own baseline
    Given a stream whose cost triples on a single day
    When the robust z-score is computed for that day
    Then the baseline is the median of the prior window, excluding the spike
    And the spike is flagged with its excess over baseline in USD

  Scenario: Anomalies are ranked by dollar impact
    When the anomaly table is returned
    Then rows are sorted by excess_usd descending
    And the cockpit shows the top 6 with the root cause on hover

  Scenario: Attribution explains the whole movement
    Given period A is the prior 14 days and period B the last 14 days
    When Cost-Mngt-App attributes the per-day delta by "service"
    Then each service's pct_of_change is reported
    And the shares sum to 100% within 1 point
    And the largest contributor is listed first
    # test_cost_app_attribution_sums_to_total
