# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-11-16

### Added
- **Shared Kernel**: `Money` and rate value objects, the TEP and TE7d finance formulas, business errors with their JSON error handlers, pagination, the async SQLAlchemy `UnitOfWork`, JWT security with role checks, the Lima business date, Alembic migrations and a Docker Compose PostgreSQL 16 database.
- **ACL Facade Contracts**: the facade signatures each bounded context exposes to the others.
- **Continuous Integration**: a GitHub Actions workflow that runs `ruff check`, `ruff format --check` and `pytest` on Python 3.12 against PostgreSQL.
- **Regulation**: BCRP interest rate caps, managed by the platform admin under `/admin/bcrp-caps`, with the current cap at `/bcrp-caps/current` and the rate validation other contexts use.
- **IAM**: sign-in with JWT, `/auth/me`, password change, and forgotten password recovery with a single-use reset token.
- **Stores**: store registration, the store profile, and platform admin listing, deactivation and reactivation of stores; an inactive store is refused on every store route.
- **Customers, Catalog and Billing**: the `customers`, `store_customers`, `products` and `billing_cycles` tables and the facade methods the credit context uses, including the cycle a purchase belongs to by its date in Lima.
- **Credit**: purchase simulation and registration paid on a single date or in weekly installments with the French method, purchase history and detail, the installment schedule, the store's installments with their computed overdue status, and the `CreditFacade` for billing and reporting.

### Fixed
- **Shared Kernel**: the rate formulas take a `Rate` instead of a raw decimal, and the application refuses to start with a JWT secret shorter than 32 characters.
- **Audit Fixes**: tests run on their own `<database>_test` database, the connection pool survives idle periods, PostgreSQL is published only on `127.0.0.1`, and malformed JSON, huge page numbers, huge rates and negative zero money now fail cleanly instead of returning a 500 or odd values.

### Known gaps
- The `customers`, `catalog` and `billing` contexts have no REST endpoints yet.
- Payments, cycle closing and late interest are not implemented, so `BillingFacade.get_cycle_statement` and `BillingFacade.list_payments` still raise `NotImplementedError`.
- The `reporting` context is not implemented.

## [0.1.0] - 2026-10-23

### Added
- **FastAPI Scaffold**: the FastAPI application with a `/health` endpoint and its test, the initial dependencies, and the pytest and ruff configuration.
- **Project Documentation**: `README.md` with the setup instructions.
