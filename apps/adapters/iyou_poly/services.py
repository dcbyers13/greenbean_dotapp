import uuid
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum

from orders.models import Order
from .models import WorkerMember, LaborLog, SurplusDistribution, WorkerDividend


class PatronageCalculatorService:
    """Service for computing quarterly democratic patronage distributions and exporting payloads for iyou_poly."""

    @classmethod
    @transaction.atomic
    def calculate_quarterly_distribution(
        cls,
        period_label: str,
        start_date,
        end_date,
        operating_costs: Decimal = Decimal("0.00"),
        reinvestment_rate: Decimal = Decimal("0.20"),
        worker_share: Decimal = Decimal("0.50"),
        gross_revenue_override: Decimal = None,
    ) -> SurplusDistribution:
        """
        Calculate democratic waterfall distribution for a given period:
        1. Determine Gross Revenue: Sum of completed orders in [start_date, end_date] or gross_revenue_override.
        2. Compute Net Surplus = gross_revenue - operating_costs.
           Invariant: Net surplus arithmetic must be non-negative. If store operations yield zero or negative surplus,
           zero dividends are distributed (no negative equity draw).
        3. Deduct Reinvestment Reserve = net_surplus * reinvestment_rate.
        4. Distributable Surplus = net_surplus - reinvestment_reserve.
        5. Split into Worker Pool (worker_share, default 50%) and Community Pool ((1 - worker_share), default 50%).
        6. Compute per-worker dividends based on hours worked in the period.
        """
        operating_costs = Decimal(str(operating_costs))
        reinvestment_rate = Decimal(str(reinvestment_rate))
        worker_share = Decimal(str(worker_share))

        if gross_revenue_override is not None:
            gross_revenue = Decimal(str(gross_revenue_override))
        else:
            orders_rev = (
                Order.objects.filter(
                    status=Order.Status.COMPLETED,
                    created_at__date__gte=start_date,
                    created_at__date__lte=end_date,
                ).aggregate(total=Sum("total_price_usd"))["total"]
                or Decimal("0.00")
            )
            gross_revenue = Decimal(str(orders_rev))

        # Net surplus arithmetic (strictly non-negative)
        raw_surplus = gross_revenue - operating_costs
        if raw_surplus <= Decimal("0.00"):
            net_surplus = Decimal("0.00")
            reinvestment_reserve = Decimal("0.00")
            distributable_surplus = Decimal("0.00")
            worker_pool = Decimal("0.00")
            community_pool = Decimal("0.00")
        else:
            net_surplus = raw_surplus
            reinvestment_reserve = (net_surplus * reinvestment_rate).quantize(Decimal("0.01"))
            distributable_surplus = net_surplus - reinvestment_reserve
            worker_pool = (distributable_surplus * worker_share).quantize(Decimal("0.01"))
            # Guarantee worker_pool + community_pool == distributable_surplus exactly
            community_pool = distributable_surplus - worker_pool

        distribution = SurplusDistribution.objects.create(
            period_label=period_label,
            period_start=start_date,
            period_end=end_date,
            gross_revenue_usd=gross_revenue,
            operating_costs_usd=operating_costs,
            reinvestment_reserve_usd=reinvestment_reserve,
            distributable_surplus_usd=distributable_surplus,
            worker_pool_usd=worker_pool,
            community_pool_usd=community_pool,
            status=SurplusDistribution.Status.FINALIZED,
        )

        # Calculate per-worker dividends from labor logs in the period
        logs = LaborLog.objects.filter(
            shift_date__gte=start_date,
            shift_date__lte=end_date,
        ).select_related("member")

        member_hours = {}
        for log in logs:
            member_hours[log.member] = member_hours.get(log.member, Decimal("0.00")) + Decimal(str(log.hours_worked))

        total_hours = sum(member_hours.values(), Decimal("0.00"))

        if total_hours > Decimal("0.00") and worker_pool > Decimal("0.00"):
            for member, hours in member_hours.items():
                proportion = hours / total_hours
                share_pct = (proportion * Decimal("100.00")).quantize(Decimal("0.01"))
                dividend_amt = (worker_pool * proportion).quantize(Decimal("0.01"))
                WorkerDividend.objects.create(
                    distribution=distribution,
                    member=member,
                    hours_worked=hours,
                    share_percentage=share_pct,
                    dividend_usd=dividend_amt,
                )
        elif total_hours > Decimal("0.00"):
            for member, hours in member_hours.items():
                proportion = hours / total_hours
                share_pct = (proportion * Decimal("100.00")).quantize(Decimal("0.01"))
                WorkerDividend.objects.create(
                    distribution=distribution,
                    member=member,
                    hours_worked=hours,
                    share_percentage=share_pct,
                    dividend_usd=Decimal("0.00"),
                )

        return distribution

    @classmethod
    def export_poly_payload(cls, distribution_id) -> dict:
        """Export canonical JSON payload for iyou_poly participatory budgeting ecosystem."""
        if isinstance(distribution_id, str):
            distribution_id = uuid.UUID(distribution_id)

        distribution = SurplusDistribution.objects.get(id=distribution_id)
        dividends_qs = distribution.worker_dividends.select_related("member").order_by("-dividend_usd", "member__name")

        worker_dividends = [
            {
                "worker_id": str(wd.member.id),
                "name": wd.member.name,
                "did": wd.member.did,
                "hours_worked": str(wd.hours_worked),
                "share_percentage": str(wd.share_percentage),
                "dividend_usd": str(wd.dividend_usd),
            }
            for wd in dividends_qs
        ]

        clean_slug = distribution.period_label.lower().replace(" ", "-")

        payload = {
            "protocol": "iyou_poly/v1",
            "collective": "Green Bean Coffee Collective",
            "store_did": "did:key:z6MkgReenBeanCollective2017OpCo",
            "ein": "82-1928471",
            "distribution_id": str(distribution.id),
            "period_label": distribution.period_label,
            "period_start": distribution.period_start.isoformat(),
            "period_end": distribution.period_end.isoformat(),
            "currency": "USD",
            "financials": {
                "gross_revenue_usd": str(distribution.gross_revenue_usd),
                "operating_costs_usd": str(distribution.operating_costs_usd),
                "reinvestment_reserve_usd": str(distribution.reinvestment_reserve_usd),
                "distributable_surplus_usd": str(distribution.distributable_surplus_usd),
                "worker_pool_usd": str(distribution.worker_pool_usd),
                "community_pool_usd": str(distribution.community_pool_usd),
            },
            "community_budget": {
                "voting_round_id": f"round-{clean_slug}-community-grant",
                "fund_amount_usd": str(distribution.community_pool_usd),
                "voting_method": "quadratic_token_weighted",
                "treasury_destination": "iyou_poly:community_participatory_treasury",
            },
            "worker_dividends": worker_dividends,
            "status": distribution.status,
            "created_at": distribution.created_at.isoformat(),
        }
        return payload
