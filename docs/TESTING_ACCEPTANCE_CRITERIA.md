# Acceptance Criteria and UAT

## Overview

Acceptance criteria define when a feature is complete. User Acceptance Testing (UAT) validates features meet business requirements before release.

## Acceptance Criteria Format

```yaml
feature: "Dynamic Pricing Optimization"
acceptance_criteria:
  - criterion: "Prices update within 5 minutes of cost change"
    condition: "When supplier price changes"
    expected: "System price adjusted within 5 minutes"
    measurement: "Automated test"

  - criterion: "Margin maintained within 2-5%"
    condition: "For all price adjustments"
    expected: "Margin never below 2% or above 5%"
    measurement: "Business rule validation"

  - criterion: "Customer satisfaction maintained"
    condition: "After implementing new prices"
    expected: "NPS score within 5 points of baseline"
    measurement: "Post-release survey"
```

## UAT Process

```python
def conduct_uat(feature, uat_participants, test_scenarios):
    """Execute user acceptance testing"""

    uat_results = {
        'feature': feature,
        'participants': len(uat_participants),
        'test_scenarios_passed': 0,
        'issues_found': [],
        'recommendation': None
    }

    for scenario in test_scenarios:
        for participant in uat_participants:
            result = participant.test_scenario(scenario, feature)

            if result.passed:
                uat_results['test_scenarios_passed'] += 1
            else:
                uat_results['issues_found'].append(result.issue)

    # Determine go/no-go
    pass_rate = uat_results['test_scenarios_passed'] / len(test_scenarios)
    uat_results['recommendation'] = 'GO' if pass_rate > 0.95 else 'NO_GO'

    return uat_results
```

🔗 **Related Topics**: [Edge Cases](TESTING_EDGE_CASES_SYSTEMATIC.md) | [Continuous Integration](TESTING_CONTINUOUS_INTEGRATION.md)
