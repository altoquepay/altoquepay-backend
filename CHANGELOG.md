# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.9.1] - 2026-11-27

No new migrations, and no routes or fields change.

### Fixed
- **Deploy**: CORS accepts the frontend published on Firebase Hosting, `https://altoquepay-frontend.web.app` and `https://altoquepay-frontend.firebaseapp.com`, and the password reset links point to `https://altoquepay-frontend.web.app`. Both values are set in `deploy/compose.yml`, so every deploy applies them; the server's `.env` no longer sets them.

## [0.9.0] - 2026-11-24

No new migrations, and no routes or fields change. The last installment of a new weekly purchase, and so its total, may differ by a few cents from what 0.8.0 calculated.

### Changed
- **Credit**: every installment of a weekly purchase is equal. Before, the last one amortized whatever was left and kept its own interest, so it differed from the others by a few cents: in the report's test N°3 it was 109.69 after three of 109.68. Its interest now takes the cents lost to rounding. Every row still adds up and the schedule closes at 0.00.
- **Credit and Billing**: the rate of a period is calculated with the 7 decimals it is shown with, instead of 28 digits. It applies to the installments, the grace period, single date purchases, late interest and early payments.

### Known gaps
- The last installment is still a few cents larger when its interest is too small to take the cents lost to rounding: with a TEA of 0%, or in very small purchases.
- Purchases registered before 0.9.0 keep the schedule they were registered with.
- Still open from 0.8.0: phones saved before 0.8.0 are not checked until their account or store profile is edited.
- Still open from 0.7.1: Run workflow can only roll back to versions the workflow published, from 0.7.1 on.
- Still open from 0.7.0: the compose in `deploy` makes no backups of its own, paying a voided purchase answers `ALREADY_PAID` (409), and the 0.5.0 lockouts still need the system administrator.

## [0.8.0] - 2026-11-22

No new migrations. A phone with letters or symbols, which the API accepted before, now answers `INVALID_PHONE` (422).

### Added
- **Catalog**: `PATCH /products/{product_id}/reactivate` sells a deactivated product again, with the details and prices it has now. Its code stays taken while it is inactive, so before this a product deactivated by mistake could be neither sold nor created again.
- **Customers**: `PATCH /customers/{account_id}/reactivate` lets a deactivated account buy on credit again, with its current terms. Before this the store could neither reactivate it nor open another account for the same DNI.

### Fixed
- **Customers and Stores**: the phone of a customer account and of the store profile accepted any text of up to 20 characters, such as `abcdefgh`. It now needs 6 to 15 digits, optionally separated by spaces or hyphens and starting with `+`; otherwise the request answers `INVALID_PHONE` (422) on the `phone` field. A blank phone is still `null`.
- **Customers**: the description of `PUT /customers/{account_id}` said the person's data is shared by every store where they buy, which stopped being true in 0.6.0.

### Known gaps
- Phones saved before 0.8.0 are not checked until their account or store profile is edited, and saving it then needs a valid phone.
- Still open from 0.7.1: Run workflow can only roll back to versions the workflow published, from 0.7.1 on.
- Still open from 0.7.0: the compose in `deploy` makes no backups of its own, paying a voided purchase answers `ALREADY_PAID` (409), and the 0.5.0 lockouts still need the system administrator.

## [0.7.1] - 2026-11-19

No changes to the API and no new migrations.

### Added
- **Build**: the Deploy workflow deploys every release. A tag such as `v0.7.1` runs the tests, publishes the image as `ghcr.io/altoquepay/altoquepay-backend:0.7.1`, deploys it to the server over SSH and checks `/health` and the version. Run workflow deploys a published version again, for example to roll back.
- **Build**: `deploy/deploy.sh`, the only command the GitHub Actions key can run on the server. It accepts only a version, and pulls the image with the job's token, which expires when the job ends.

### Changed
- **Build**: the compose in `deploy` runs the API image published for the version in `API_VERSION`, and builds it locally when that is unset.

### Known gaps
- Run workflow can only roll back to versions the workflow published, from 0.7.1 on.
- Still open from 0.7.0: the compose in `deploy` makes no backups of its own, paying a voided purchase answers `ALREADY_PAID` (409), and the 0.5.0 lockouts still need the system administrator.

## [0.7.0] - 2026-11-18

No breaking changes for API clients. Run `alembic upgrade head`: there is one new migration. The Docker image applies the migrations every time it starts.

### Added
- **IAM**: each email gets at most 3 password reset emails every 15 minutes. Past that, `POST /auth/forgot-password` still answers 204 but sends nothing, so the limit never shows which emails have an account.
- **Build**: a `Dockerfile` for the API and a `deploy` folder that runs it on one server with Docker Compose. Caddy gets the HTTPS certificate and forwards to the API, and PostgreSQL stays on the internal network. The README explains how to deploy on Amazon Lightsail.

### Changed
- **Database**: migration `3c8dcad76508` adds the `sign_in_attempts` table.

### Fixed
- **IAM**: the attempt limit is counted in PostgreSQL, so every worker and instance of the API shares it and a restart no longer resets it. This was a known gap of 0.6.0.

### Security
- Password reset requests were limited per IP only, so a script spread over many IPs could flood one inbox with reset emails. This was a known gap of 0.6.0.
- The README suggested `FORWARDED_ALLOW_IPS=*` behind a proxy. With it, Uvicorn takes the first address in `X-Forwarded-For`, which the client writes, so anyone could dodge the limit per IP. The README now warns against it, and the compose in `deploy` trusts only Caddy.

### Known gaps
- The compose in `deploy` keeps PostgreSQL on the same server as the API and makes no backups of its own.
- Still open from 0.6.0: paying a voided purchase answers `ALREADY_PAID` (409).
- Still open from 0.5.0: a store the customer trusts, or one that activates someone's DNI before they do, can lock them out until the system administrator steps in, without a support screen.

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
