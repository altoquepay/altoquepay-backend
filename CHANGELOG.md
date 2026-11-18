# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.0] - 2026-11-17

Breaking for API clients: `GET /customers/lookup` returns only `customer_id`, `dni`, `account_id` and `notice`, `POST /customers` always needs `first_names` and `last_names`, and a token issued before a password change answers 401 for every role. Python 3.13 or newer is required. Run `alembic upgrade head`: there are two new migrations.

### Added
- **Credit**: `PATCH /purchases/{purchase_id}/void` voids a purchase registered by mistake, while nothing of it is paid (else `PURCHASE_NOT_VOIDABLE`, 409) and its cycle is still open (else `CYCLE_CLOSED`, 409). Its installments are cancelled, so it frees the credit and is not billed, and purchases gain `voided_at` and `voided_by`.
- **Reporting**: the dashboard's `overdue_statements` counts the closed, unpaid cycle statements whose payment date passed.
- **IAM**: sign-in and password reset requests share 20 attempts per IP every 15 minutes, then answer `TOO_MANY_ATTEMPTS` (429).
- **Shared**: a request body over 3 MB answers `CONTENT_TOO_LARGE` (413) before an upload is written to disk.

### Changed
- **Customers**: names, phone and address belong to each store's account, so a store never sees or changes what another store typed. Lookup returns only the person's ids, and a store reads its own account with `GET /customers/{account_id}`.
- **Reporting**: `overdue_amount` adds the overdue cycle statements to the overdue installments, and voided purchases are left out of the purchase totals.
- **IAM**: the token's `password_version` is checked on every signed-in request, for store and system administrators too.
- **Build**: Python 3.13 or newer; CI runs on 3.13.
- **Database**: migration `64bc8f7a560c` moves the person's names, phone and address to `store_customers`, and `7cdbcc056b7c` adds the `VOIDED` status, `voided_at` and `voided_by` to `purchases`.

### Fixed
- **Credit**: each purchase and simulation is checked against the BCRP cap in force on the purchase day: `RATE_ABOVE_BCRP_CAP` (422) above it, `NO_BCRP_CAP_IN_FORCE` (409) when that day has none.
- **Billing**: a purchase registered as its cycle closed at midnight could land in the closed cycle, and paying the statement then marked it paid without billing it. The purchase now locks its cycle.
- **Reporting**: the dashboard counts overdue single date cycle statements, the known gap of 0.4.0.

### Security
- A store could read the phone and address another store typed for a customer, or change the names, phone and address every store saw.
- Sign-in and password reset had no attempt limit, the known gap of 0.5.0; a script could also flood an administrator's inbox with reset emails.
- Product image uploads of any size were written to disk before the 2 MB check.
- A store or system administrator's token kept working after their password was reset.

### Known gaps
- The attempt limit is counted in each process's memory: several workers or replicas each keep their own count. Behind a proxy, set `FORWARDED_ALLOW_IPS`.
- Password reset requests are limited per IP, not per email.
- Paying a voided purchase answers `ALREADY_PAID` (409).
- Still open from 0.5.0: a store the customer trusts, or one that activates someone's DNI before they do, can lock them out until the system administrator steps in, without a support screen.

## [0.5.0] - 2026-11-17

Breaking for API clients: `POST /customers` returns `{account, access_code}` and `POST /customers/{account_id}/reset-password` is gone. Run `alembic upgrade head`: there are three new migrations.

### Added
- **Customers**: one-time store access codes, 12 characters without `0`, `O`, `1` or `I`, valid 48 hours and stored as SHA-256. Opening an account issues one, and `POST /customers/{account_id}/access-code` issues a new one that replaces the previous.
- **IAM**: `POST /auth/redeem-access-code` with `{dni, code, new_password}`. The customer chooses their own password with a store's code, which links that store to their portal and unlinks the others.
- **Customers**: `POST /me/stores/link` adds a store to the signed-in customer's portal with that store's code.
- **Customers**: trusted stores. Once a customer has linked a store, only a store they trust can restore their access without a session; any other answers `STORE_NOT_TRUSTED` (403). The system administrator settles disputes with `POST /admin/customers/trusted-store`. A deactivated store's codes answer `STORE_INACTIVE` (403).
- **IAM**: `users.password_version`, carried in the JWT and checked on every customer request, so a customer's older tokens stop working when the password changes.

### Changed
- **Customers**: `POST /customers` returns the account and its access code, and `CustomerAccountResource` gains `portal_linked`.
- **Reporting**: the customer portal shows only the accounts linked with their store's code; any other answers 404.
- **IAM**: customer users start with a random password nobody knows; `must_change_password` now applies only to the first system administrator.
- **Database**: `store_customers` gains the portal link, access code and trust columns, and `users` gains `password_version`.

### Removed
- **Customers**: `POST /customers/{account_id}/reset-password` and `CredentialsResource`.
- **IAM**: `IamFacade.reset_password`, `TemporaryCredentials` and `User.assign_temporary_password`.

### Security
- A store could create or reset the password of a DNI's single user, sign in as that person and read their debt in other stores. Stores no longer know customer passwords, and each store links only its own account to the portal.

### Known gaps
- A store the customer trusts, or one that activates someone's DNI before they do, can lock them out until the system administrator steps in. There is no support screen yet.
- Customers get no notice outside the app when their access is restored.
- Sign-in has no attempt limit.

## [0.4.1] - 2026-11-17

### Fixed
- **Billing**: a purchase dated in a cycle whose cutoff day already ended is refused with `CYCLE_CLOSED`. Before, it was added to a statement the customer had already seen, or it opened a past cycle that was overdue from the start and charged late interest at once.
- **Billing**: the cycles a read closes after their cutoff are saved. Before, every dashboard, cycle list and statement closed them again, one query per cycle, and they stayed `OPEN` in the database until a payment of that account.

## [0.4.0] - 2026-11-16

### Added
- **Reporting**: the dashboard lists what falls due in the next 7 days (`upcoming`: installments and closed cycle statements, with their type, customer, date and amount) and the store's next cycle cutoff (`next_cutoff`).
- **Billing**: the cycle statement as a downloadable PDF at `/customers/{customer_id}/cycles/{year}/{month}/pdf`, and `CustomersFacade.get_account_holder` for the holder's name and DNI.
- **Catalog**: the `product_images` table, with images served at `/media/products/{name}` and cached for a year.

### Changed
- **Reporting**: the dashboard and the period report read the whole store at once through new store-wide facade methods, so their query count no longer grows with the number of customers.
- **Catalog**: product images are stored in PostgreSQL instead of the container disk, so they survive redeploys; replacing an image deletes the previous one.
- **Customers**: `CustomersFacade.list_account_holders` replaces `list_accounts_of_store` and returns each account with its holder's DNI and name.

### Removed
- **Catalog**: the `MEDIA_DIR` setting and the static `/media` mount.

### Known gaps
- The dashboard's `overdue_amount` counts overdue installments only, not overdue single date cycle statements.

## [0.3.0] - 2026-11-16

### Added
- **Customers API**: store customer accounts with search, DNI lookup, opening with the store's default conditions and BCRP-validated rates, editing, deactivation and password reset under `/customers`.
- **Catalog API**: products with search, editing, deactivation and image upload under `/products`; images are stored on disk under `MEDIA_DIR` and served at `/media`.
- **Billing Payments**: the `payments` table and the five payment kinds (cycle statement, installment, installment advance, early single date payment and full prepayment), applied first to late interest, then to ordinary interest, then to principal, with no partial payments; cycles close the first time billing reads them after their cutoff; late interest on overdue amounts; `/cycles`, the cycle statement, `/payments/quote` and `/payments`; and `BillingFacade.get_cycle_statement` and `list_payments`.
- **Reporting**: the customer portal under `/me/stores`, the store dashboard and the period report.

### Changed
- **Credit**: `purchases.payment_id` and `installments.payment_id` now reference `payments`.

### Known gaps
- Product images live on the container disk, so they are lost on every redeploy.
- The store report reads each account through the facades one at a time.
- The cycle statement has no PDF export.

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
