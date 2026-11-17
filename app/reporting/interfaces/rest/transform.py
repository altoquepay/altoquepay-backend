from dataclasses import asdict

from app.billing.interfaces.acl.billing_facade import CycleStatement
from app.credit.interfaces.acl.credit_facade import InstallmentSummary, PurchaseSummary
from app.reporting.application.query_services.customer_portal_service import (
    AccountOverview,
    CustomerStore,
    PurchaseSchedule,
)
from app.reporting.application.query_services.store_report_service import Dashboard, PeriodReport
from app.reporting.interfaces.rest.resources.report_resources import (
    AccountOverviewResource,
    BcrpCapResource,
    CustomerStoreResource,
    CycleStatementResource,
    DashboardResource,
    InstallmentResource,
    PaymentTotalsResource,
    PeriodReportResource,
    PurchaseResource,
    PurchaseScheduleResource,
    PurchaseTotalsResource,
    UpcomingDueResource,
)


def to_customer_store(listed: CustomerStore) -> CustomerStoreResource:
    return CustomerStoreResource(
        store_id=listed.store.store_id,
        business_name=listed.store.business_name,
        store_status=listed.store.status,
        account_status=listed.account.status,
    )


def to_installment(installment: InstallmentSummary) -> InstallmentResource:
    return InstallmentResource(
        installment_id=installment.installment_id,
        purchase_id=installment.purchase_id,
        number=installment.number,
        due_date=installment.due_date,
        amount=installment.amount,
        status=installment.status,
    )


def to_overview(overview: AccountOverview) -> AccountOverviewResource:
    terms = overview.terms
    return AccountOverviewResource(
        store_id=overview.store.store_id,
        business_name=overview.store.business_name,
        account_status=terms.status,
        credit_limit=terms.credit_limit,
        outstanding_principal=overview.outstanding_principal,
        available_credit=overview.available_credit,
        tea=terms.tea,
        late_tea=terms.late_tea,
        cutoff_day=terms.cutoff_day,
        payment_day=terms.payment_day,
        max_weeks=terms.max_weeks,
        installments=[to_installment(i) for i in overview.installments],
    )


def to_statement(statement: CycleStatement) -> CycleStatementResource:
    return CycleStatementResource(**asdict(statement))


def to_purchase(purchase: PurchaseSummary) -> PurchaseResource:
    return PurchaseResource(
        purchase_id=purchase.purchase_id,
        purchased_at=purchase.purchased_at,
        mode=purchase.mode,
        amount=purchase.amount,
        tea=purchase.tea,
        term_days=purchase.term_days,
        installments_count=purchase.installments_count,
        installment_amount=purchase.installment_amount,
        ordinary_interest=purchase.ordinary_interest,
        status=purchase.status,
    )


def to_schedule(schedule: PurchaseSchedule) -> PurchaseScheduleResource:
    return PurchaseScheduleResource(
        purchase=to_purchase(schedule.purchase),
        installments=[
            to_installment(i) for i in sorted(schedule.installments, key=lambda i: i.number)
        ],
    )


def to_dashboard(dashboard: Dashboard) -> DashboardResource:
    cap = dashboard.bcrp_cap
    return DashboardResource(
        active_customers=dashboard.active_customers,
        outstanding_principal=dashboard.outstanding_principal,
        overdue_installments=dashboard.overdue_installments,
        overdue_statements=dashboard.overdue_statements,
        overdue_amount=dashboard.overdue_amount,
        purchases_this_month=PurchaseTotalsResource(**asdict(dashboard.purchases_this_month)),
        payments_this_month=PaymentTotalsResource(**asdict(dashboard.payments_this_month)),
        bcrp_cap=BcrpCapResource(**asdict(cap)) if cap else None,
        upcoming=[UpcomingDueResource(**asdict(due)) for due in dashboard.upcoming],
        next_cutoff=dashboard.next_cutoff,
    )


def to_period_report(report: PeriodReport) -> PeriodReportResource:
    return PeriodReportResource(
        from_date=report.from_date,
        to_date=report.to_date,
        purchases=PurchaseTotalsResource(**asdict(report.purchases)),
        payments=PaymentTotalsResource(**asdict(report.payments)),
    )
