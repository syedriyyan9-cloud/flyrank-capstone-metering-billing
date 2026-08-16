# Usage Metering & Billing Engine

## Problem Statement
Every SaaS needs to answer: How much has this customer used? What does it cost? Have they hit their limit?

## Solution
A metering and billing service that tracks usage, enforces quotas, calculates costs, and syncs subscriptions via Stripe.

## Architecture

┌─────────────┐
│ Client │
└──────┬──────┘
│ POST /api/generate
▼
┌─────────────────────────────────────────────┐
│ FastAPI Server │
│ ┌─────────────────────────────────────┐ │
│ │ Meter Service │ │
│ │ - Record usage (idempotent) │ │
│ │ - Duplicate prevention │ │
│ └─────────────────────────────────────┘ │
│ ┌─────────────────────────────────────┐ │
│ │ Quota Service │ │
│ │ - Check limits │ │
│ │ - Return 429/402 │ │
│ └─────────────────────────────────────┘ │
│ ┌─────────────────────────────────────┐ │
│ │ Cost Service │ │
│ │ - Token pricing rules │ │
│ │ - Monthly rollup │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
│ │
▼ ▼
┌─────────────────┐ ┌─────────────────┐
│ PostgreSQL │ │ Stripe │
│ (usage data) │ │ (test mode) │
└─────────────────┘ └─────────────────┘


## Data Model

### Tenants
- id, name, email, plan_id, stripe_customer_id, is_active

### Plans
- id, name, api_limit, token_limit, pricing constants

### Subscriptions
- id, tenant_id, stripe_subscription_id, plan_id, status, period dates

### Usage Events
- id, tenant_id, idempotency_key (unique), usage_type, quantity, cost, timestamp

## Key Design Decisions

1. **Idempotency via idempotency_key** - Clients provide a unique key per request; duplicates return cached result
2. **Integer cents for money** - Store as integers, never floats
3. **Usage checked before action** - Reject before processing, not after
4. **Stripe webhooks verified** - Cryptographic signature check before any state change

## Non-Goals (Scope Boundaries)

- No invoicing or billing cycle logic
- No proration
- No overage billing
- No UI/dashboard (API only)

## Pricing Rules (AI Tokens)

| Token Type | Cost Factor |
|------------|-------------|
| Input Token | 1x |
| Cached Input Token | 0.3x |
| Output Token | 2x |
| Reasoning Token | 2x (same as output) |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/generate | Dummy billable endpoint |
| GET | /api/usage | Get usage stats |
| POST | /api/webhooks/stripe | Stripe webhook handler |

## How It Works

1. Client calls POST /api/generate with idempotency_key
2. Meter Service checks if key exists (duplicate → return cached)
3. Quota Service checks if tenant has remaining usage
4. If under limit: record usage, calculate cost, return success
5. If over limit: return 429/402 with explanation

## Subscription Flow

1. Client initiates Checkout → Stripe
2. Customer completes test payment
3. Stripe sends webhook to /api/webhooks/stripe
4. Service verifies signature, deduplicates, updates tenant plan

## Limitations (Honest)

- Single-currency only (GBP/USD)
- No proration on plan changes
- Monthly billing only (no daily/quarterly)
- No invoice generation
- Test mode only (no real payments)