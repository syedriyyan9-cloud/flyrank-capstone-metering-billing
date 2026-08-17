# Evidence - Usage Metering & Billing Engine

## Metering
- [x] Idempotent metering prevents double-counting
  - Test: `tests/test_meter.py::test_idempotency_prevents_double_counting`
  - Proof: Same idempotency_key returns `duplicate: true`

## Quotas
- [x] Quota enforcement with correct status codes
  - Test: `tests/test_quota.py::test_quota_boundary_blocks_after_limit`
  - Proof: 429 status code returned when quota exceeded

## Cost Calculation
- [x] AI token pricing rules correctly implemented
  - Test: `tests/test_cost.py::test_cached_input_tokens_are_cheaper`
  - Test: `tests/test_cost.py::test_reasoning_tokens_equal_output_tokens`
  - Proof: Pricing constants pinned and tests pass

## Stripe Integration
- [x] Checkout flow works in test mode
  - Proof: `curl -X POST "http://localhost:8000/api/checkout?tenant_id=1&price_id=price_1U548i8gviZLUIsz1F2FQnDB"`
  - Response: `{"checkout_url":"https://checkout.stripe.com/...","session_id":"cs_test_..."}`

- [x] Webhook signature verification
  - Test: `tests/test_webhooks.py::test_webhook_signature_verification`
  - Proof: Invalid signature returns False

- [x] Duplicate webhook events ignored
  - Test: `tests/test_webhooks.py::test_duplicate_webhook_prevention`
  - Proof: processed_events set prevents duplicates

## Data Model & Tests
- [x] Database includes tenants, plans, subscriptions, usage_events
  - Proof: Models in `models/` directory
  - Screenshot: (attach database schema screenshot)

## Documentation
- [x] README with architecture diagram
- [x] Setup instructions work
- [x] Limitations documented

## Test Results

```bash
$ python -m pytest tests/ -v
============================= test session starts ==============================
collected 13 items

tests/test_cost.py::test_pricing_constants_are_pinned PASSED
tests/test_cost.py::test_cached_input_tokens_are_cheaper PASSED
tests/test_cost.py::test_reasoning_tokens_equal_output_tokens PASSED
tests/test_cost.py::test_pro_plan_gets_20_percent_discount PASSED
tests/test_cost.py::test_token_bundle_cost_calculation PASSED
tests/test_cost.py::test_zero_tokens_cost_zero PASSED
tests/test_meter.py::test_idempotency_prevents_double_counting PASSED
tests/test_meter.py::test_quota_boundary_blocks_after_limit PASSED
tests/test_quota.py::test_quota_boundary_exact_limit PASSED
tests/test_quota.py::test_quota_under_limit PASSED
tests/test_quota.py::test_quota_over_limit PASSED
tests/test_webhooks.py::test_webhook_signature_verification PASSED
tests/test_webhooks.py::test_duplicate_webhook_prevention PASSED

============================== 13 passed in 4.66s ===============================

