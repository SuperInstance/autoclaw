# Third-Party API Integration

## Overview

Integrating third-party APIs extends agent capabilities with external services. Successful integration requires managing authentication, rate limiting, error handling, and data transformation.

## Integration Patterns

```yaml
api_integration_patterns:
  synchronous_calls:
    pattern: "Agent calls API, waits for response"
    use_case: "Lookup operations"
    timeout: 5000ms
    retry_strategy: "exponential_backoff"

  asynchronous_callbacks:
    pattern: "Agent initiates request, continues work"
    use_case: "Background processing"
    timeout: 30000ms
    notification: "webhook_callback"

  polling:
    pattern: "Agent checks status periodically"
    use_case: "Long-running operations"
    interval: "5_seconds"
    max_attempts: 60
```

## API Error Handling

```python
def handle_api_error(error, retry_count=0, max_retries=3):
    """Handle common API errors with retry logic"""

    if error.status_code == 429:  # Rate limited
        wait_time = exponential_backoff(retry_count)
        if retry_count < max_retries:
            retry_after_delay(wait_time)
        else:
            fallback_to_cached_result()

    elif error.status_code == 503:  # Service unavailable
        if retry_count < max_retries:
            retry_after_delay(60)  # Wait 1 minute
        else:
            use_degraded_functionality()

    elif error.status_code in [400, 401, 403]:  # Client errors
        log_error_and_alert()  # Don't retry
```

🔗 **Related Topics**: [Data Connectors](INTEGRATION_DATA_CONNECTORS.md) | [Webhook Handling](INTEGRATION_WEBHOOK_HANDLING.md)
