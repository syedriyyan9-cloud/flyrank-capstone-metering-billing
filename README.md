# Usage Metering & Billing Engine

A production-ready metering and billing service that tracks API usage, enforces quotas, calculates costs (including AI token pricing), and integrates with Stripe for subscription management.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Installation & Running](#installation--running)
- [API Endpoints](#api-endpoints)
- [Usage Examples](#usage-examples)
- [Testing](#testing)
- [Pricing Rules](#pricing-rules)
- [Stripe Integration](#stripe-integration)
- [Project Structure](#project-structure)
- [Environment Variables](#environment-variables)
- [Limitations](#limitations)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

Every SaaS product must answer three questions:
1. **How much has this customer used?** → Metering
2. **How much should they pay?** → Cost calculation
3. **Have they reached their plan limits?** → Quota enforcement

This service answers all three with idempotent metering, correct money math, and Stripe test-mode integration.

---

## ✨ Features

- **Idempotent Metering**: Same request with same key = one usage event (no double-counting).
- **Quota Enforcement**: `429` / `402` status codes with clear error messages.
- **Cost Calculation**: AI token pricing (cached input, reasoning tokens, output tokens).
- **Stripe Integration**: Checkout + webhooks with signature verification.
- **Plan Management**: Free (1k API calls, 100k tokens) & Pro (10k API calls, 1M tokens).
- **Dockerized**: Entire stack runs with one command.
- **Full Test Suite**: 13 tests covering edge cases.

---

## 🛠️ Tech Stack

| Component | Technology |
| :--- | :--- |
| **Language** | Python 3.10+ |
| **Framework** | FastAPI |
| **Database** | PostgreSQL 15 (Docker) |
| **ORM** | SQLAlchemy 2.0 |
| **Payments** | Stripe (test mode) |
| **Container** | Docker & Docker Compose |
| **Testing** | Pytest |
| **Validation** | Pydantic |

---

## 🏗️ Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                           Client                            │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                       FastAPI Server                        │
│ ┌─────────────────────────────────────────────────────┐ │
│ │                  POST /api/generate                 │ │
│ └─────────────────────────┬───────────────────────────┘ │
│                           │                             │
│                           ▼                             │
│ ┌─────────────────────────────────────────────────────┐ │
│ │                    Meter Service                    │ │
│ │ - Check idempotency key                             │ │
│ │ - Record usage event                                │ │
│ │ - Prevent duplicates                                │ │
│ └─────────────────────────┬───────────────────────────┘ │
│                           │                             │
│                           ▼                             │
│ ┌─────────────────────────────────────────────────────┐ │
│ │                    Quota Service                    │ │
│ │ - Check current usage vs plan limits                │ │
│ │ - Return 429/402 if exceeded                        │ │
│ └─────────────────────────┬───────────────────────────┘ │
│                           │                             │
│                           ▼                             │
│ ┌─────────────────────────────────────────────────────┐ │
│ │                    Cost Service                     │ │
│ │ - Calculate costs with pricing rules                │ │
│ │ - Token pricing (cached input, reasoning)           │ │
│ └─────────────────────────────────────────────────────┘ │
└──────────────────────────┬──────────────────────────────────┘
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
┌──────────────────────────┐ ┌──────────────────────────────┐
│        PostgreSQL        │ │            Stripe            │
│ - tenants                │ │ - Checkout sessions          │
│ - plans                  │ │ - Subscriptions              │
│ - subscriptions          │ │ - Webhooks                   │
│ - usage_events           │ │                              │
└──────────────────────────┘ └──────────────────────────────┘
```

---

## 📦 Installation & Running

### Prerequisites

- Docker Desktop installed and running
- Python 3.10+ (for local development)
- Stripe account (free - test mode)

### Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/syedriyyan9-cloud/flyrank-capstone-metering-billing
   cd flyrank-capstone-metering-billing
   ```

2. **Create `.env` file (copy from `.env.example`)**
   ```bash
   cp .env.example .env
   ```
   Update `.env` with your Stripe test keys and price IDs.

3. **Start everything with one command**
   ```bash
   docker-compose up -d
   ```

4. **Seed the database (first run only)**
   ```bash
   docker exec -it metering_app python scripts/seed.py
   ```

5. **Access the API** at [http://localhost:8000](http://localhost:8000)

### Useful Commands

```bash
# View logs
docker-compose logs -f app

# Stop services
docker-compose down

# Stop and delete volume (data lost)
docker-compose down -v

# Run tests
docker exec -it metering_app python -m pytest tests/ -v
```

---

## 📡 API Endpoints

### Endpoint Directory

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| **POST** | `/api/generate` | Record a usage event | ❌ No |
| **GET** | `/api/usage` | Get monthly usage summary | ❌ No |
| **GET** | `/api/tenants` | List all tenants | ❌ No |
| **GET** | `/api/plans` | List all plans | ❌ No |
| **POST** | `/api/checkout` | Create Stripe Checkout session | ❌ No |
| **POST** | `/api/webhooks/stripe` | Stripe webhook handler | ❌ No |
| **GET** | `/api/stripe/success` | Checkout success redirect | ❌ No |
| **GET** | `/api/stripe/cancel` | Checkout cancel redirect | ❌ No |

### HTTP Status Codes

| Code | Meaning | Description |
| :--- | :--- | :--- |
| **200** | Success | Request processed successfully |
| **201** | Created | Usage event created |
| **204** | No Content | Action completed without body |
| **400** | Bad Request | Invalid parameter payload |
| **402** | Payment Required | Quota exceeded on hard enforcement |
| **404** | Not Found | Resource or tenant does not exist |
| **429** | Too Many Requests | Rate or quota limit exceeded |
| **500** | Server Error | Internal service error |

---

## 🧪 Usage Examples

### 1. Record a Usage Event (Idempotent)

```bash
curl -X POST http://localhost:8000/api/generate   -H "Content-Type: application/json"   -d '{
    "tenant_id": 1,
    "idempotency_key": "unique-key-123",
    "usage_type": "api_call",
    "quantity": 1
  }'
```

**Response (`201 Created`):**
```json
{
  "usage_id": 1,
  "tenant_id": 1,
  "usage_type": "api_call",
  "quantity": 1,
  "cost": 0.001,
  "timestamp": "2026-08-17T10:00:00Z",
  "duplicate": false,
  "message": "Usage recorded successfully"
}
```

### 2. Record Token Usage with Pricing Rules

```bash
curl -X POST http://localhost:8000/api/generate   -H "Content-Type: application/json"   -d '{
    "tenant_id": 1,
    "idempotency_key": "token-key-456",
    "usage_type": "token_bundle",
    "quantity": 1000,
    "input_tokens": 500,
    "cached_input_tokens": 200,
    "output_tokens": 250,
    "reasoning_tokens": 50
  }'
```

### 3. Check Usage Summary

```bash
curl "http://localhost:8000/api/usage?tenant_id=1"
```

**Response (`200 OK`):**
```json
{
  "tenant_id": 1,
  "tenant_name": "Demo Tenant",
  "plan_name": "Free",
  "usage": {
    "api_calls": {
      "used": 150,
      "limit": 1000,
      "remaining": 850
    },
    "tokens": {
      "used": 50000,
      "limit": 100000,
      "remaining": 50000
    },
    "total_cost": 1.25
  },
  "quota_status": {
    "tenant_id": 1,
    "plan_name": "Free",
    "api_used": 150,
    "api_limit": 1000,
    "api_remaining": 850,
    "has_api_quota": true
  },
  "message": "Used 150/1000 API calls, 50000/100000 tokens"
}
```

### 4. Create Stripe Checkout Session

```bash
curl -X POST "http://localhost:8000/api/checkout?tenant_id=1&price_id=price_xxxxxxxxxxxxx"
```

**Response (`200 OK`):**
```json
{
  "checkout_url": "https://checkout.stripe.com/...",
  "session_id": "cs_test_...",
  "tenant_id": 1,
  "plan_name": "Pro"
}
```

### 5. Quota Exceeded Response

When a tenant exceeds their plan limits, the API returns a `429 Too Many Requests` error:

```json
{
  "detail": "API quota exceeded. Used 1000/1000. Upgrade to Pro for higher limits."
}
```

---

## 🧪 Testing

### Run All Tests

```bash
# In Docker container
docker exec -it metering_app python -m pytest tests/ -v

# Locally
python -m pytest tests/ -v
```

### Sample Test Output

```text
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
```

---

## 💰 Pricing Rules

### Token Pricing Constants (Pinned)

| Token Type | Price per Unit | Free Plan | Pro Plan |
| :--- | :--- | :--- | :--- |
| **API Call** | $0.001 | 1,000 / month | 10,000 / month |
| **Input Token** | $0.00001 | 100k / month | 1M / month |
| **Cached Input Token** | $0.000003 (30% of input) | 100k / month | 1M / month |
| **Output Token** | $0.00002 | 100k / month | 1M / month |
| **Reasoning Token** | $0.00002 (same as output) | 100k / month | 1M / month |

### Key Pricing Rules (Verified by Tests)

1. **Cached input tokens are cheaper**: Priced at **30%** of regular input tokens.
2. **Reasoning tokens = output tokens**: Priced identically to output tokens.
3. **Pro plan discount**: Pro plan subscribers receive a **20% discount** on usage costs.

---

## 💳 Stripe Integration

### Setup Steps

1. Create a free [Stripe Account](https://stripe.com).
2. Retrieve test keys from **Dashboard → API Keys**.
3. Create products and recurring prices in the Stripe Dashboard.
4. Copy `price_id` values to your `.env` configuration file.
5. Install and launch Stripe CLI for local webhook forwarding.

### Webhook Testing

```bash
# Start Stripe CLI listener
stripe listen --forward-to http://localhost:8000/api/webhooks/stripe

# Trigger test events
stripe trigger checkout.session.completed
stripe trigger customer.subscription.updated
stripe trigger customer.subscription.deleted
```

### Test Cards

| Card Number | Description |
| :--- | :--- |
| `4242 4242 4242 4242` | Payment succeeds |
| `4000 0000 0000 0002` | Payment fails |
| `4000 0000 0000 9995` | Requires authentication (3D Secure) |

---

## 📁 Project Structure

```text
flyrank-capstone-metering-billing/
├── main.py                # FastAPI application
├── database.py            # Database connection
├── requirements.txt       # Python dependencies
├── Dockerfile             # Docker build
├── docker-compose.yml     # Services definition
├── .env.example           # Environment variables template
├── .gitignore             # Git ignore rules
├── README.md              # Documentation
├── EVIDENCE.md            # Proof per requirement
├── BUILDLOG.md            # AI usage log
├── capstone.yaml          # Evaluator manifest
├── models/
│   ├── __init__.py
│   ├── base.py            # SQLAlchemy Base
│   ├── tenant.py          # Tenant model
│   ├── plan.py            # Plan model
│   ├── subscription.py    # Subscription model
│   └── usage_event.py     # Usage event model
├── services/
│   ├── __init__.py
│   ├── meter_service.py   # Idempotent metering
│   ├── quota_service.py   # Quota enforcement
│   ├── cost_service.py    # Cost calculation
│   └── stripe_service.py  # Stripe integration
├── api/
│   ├── __init__.py
│   ├── routes.py          # API routes
│   └── webhooks/
│       ├── __init__.py
│       └── stripe.py      # Stripe webhook handler
├── scripts/
│   └── seed.py            # Database seeding
└── tests/
    ├── __init__.py
    ├── test_cost.py       # Cost tests
    ├── test_meter.py      # Metering tests
    ├── test_quota.py      # Quota tests
    └── test_webhooks.py   # Webhook tests
```

---

## 🔧 Environment Variables

### `.env` (gitignored - contains real credentials)
```env
DATABASE_URL=postgresql://postgres:postgres@db:5432/metering
STRIPE_SECRET_KEY=sk_test_xxxxxxxxxxxxxxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxxxxxxxxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxxxxxxxxxxxxxxxxxxx
STRIPE_PRO_PRICE_ID=price_xxxxxxxxxxxxxxxxxxxx
FREE_API_LIMIT=1000
FREE_TOKEN_LIMIT=100000
PRO_API_LIMIT=10000
PRO_TOKEN_LIMIT=1000000
```

### `.env.example` (committed - contains placeholder values)
```env
DATABASE_URL=postgresql://postgres:postgres@db:5432/metering
STRIPE_SECRET_KEY=sk_test_xxxxxxxxxxxxxxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxxxxxxxxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxxxxxxxxxxxxxxxxxxx
STRIPE_PRO_PRICE_ID=price_xxxxxxxxxxxxxxxxxxxx
FREE_API_LIMIT=1000
FREE_TOKEN_LIMIT=100000
PRO_API_LIMIT=10000
PRO_TOKEN_LIMIT=1000000
```

---

## ⚠️ Limitations

| Limitation | Future Improvement |
| :--- | :--- |
| **Single-currency only (USD)** | Add multi-currency support |
| **No proration on plan changes** | Add mid-cycle proration logic |
| **Monthly billing only** | Add daily/weekly billing intervals |
| **No invoice generation** | Generate downloadable PDF invoices |
| **Test mode only** | Add production live mode support |
| **No email notifications** | Send quota warning alerts (at 80% / 100%) |
| **No admin dashboard** | Develop an internal administrative UI |

---

## 🤝 Contributing

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/AmazingFeature`
3. Commit your changes: `git commit -m 'Add some AmazingFeature'`
4. Push to the branch: `git push origin feature/AmazingFeature`
5. Open a Pull Request.

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for more information.

---

## 🙏 Acknowledgments

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Stripe API Documentation](https://stripe.com/docs/api)
- [SQLAlchemy Documentation](https://www.sqlalchemy.org/)
- [FlyRank Internship Program](https://github.com/)

---

## 👤 Author

**Syed Riyyan**