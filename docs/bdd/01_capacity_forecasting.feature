Feature: Capacity headroom forecasting (Capacity-Mngt-App)
  As a Cloud Operations executive
  I want to know which product/region streams will run out of headroom
  So that I can fund capacity before customers feel it

  Background:
    Given the synthetic estate generated with seed 42
    And a utilization headroom threshold of 80%

  Scenario: A stream already over the threshold is CRITICAL
    Given the "Assist" product in "us-east-1"
    When Capacity-Mngt-App forecasts utilization 45 days ahead
    Then the 7-day trailing average is at or above 80%
    And the status is "CRITICAL"
    And already_breached is true
    # test_capacity_app_flags_critical_capacity

  Scenario: A stream with adequate headroom is HEALTHY
    Given the "Analyze" product in "ap-southeast-1"
    When Capacity-Mngt-App forecasts utilization 45 days ahead
    Then the status is "HEALTHY" or "WATCH"
    # test_capacity_app_reports_healthy_where_expected

  Scenario Outline: Status is derived from days-to-breach
    Given a forecast that first crosses 80% in <days> days
    Then the status is "<status>"
    Examples:
      | days | status  |
      | 12   | WARNING |
      | 30   | WARNING |
      | 31   | WATCH   |
      | none | HEALTHY |

  Scenario: Forecasts are accurate on a clean seasonal signal
    Given the "Engage" product in "us-west-2"
    When Capacity-Mngt-App fits ridge regression on trend, day-of-week and weekly Fourier terms
    Then the in-sample MAPE is below 8%
    # test_capacity_app_forecast_is_accurate

  Scenario: Spend forecast carries an honest prediction interval
    When Capacity-Mngt-App forecasts estate daily spend 45 days ahead
    Then every point satisfies lower <= yhat <= upper
    And the band width is 1.96 x the residual standard deviation
    # test_cost_forecast_has_interval
