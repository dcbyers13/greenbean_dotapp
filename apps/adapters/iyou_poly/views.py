from decimal import Decimal
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views import View

from .models import SurplusDistribution, WorkerMember
from .services import PatronageCalculatorService


class DistributionExportView(View):
    """Export canonical iyou_poly JSON distribution payload."""

    def get(self, request, dist_id):
        dist = get_object_or_404(SurplusDistribution, id=dist_id)
        payload = PatronageCalculatorService.export_poly_payload(dist.id)
        response = JsonResponse(payload, json_dumps_params={"indent": 2})
        response["Access-Control-Allow-Origin"] = "*"
        return response


class GovernanceDashboardView(View):
    """Cooperative assembly portal and democratic profit waterfall dashboard."""

    def get(self, request):
        worker_members_count = WorkerMember.objects.filter(is_active=True).count()
        active_workers = WorkerMember.objects.filter(is_active=True)
        distributions = (
            SurplusDistribution.objects.all()
            .prefetch_related("worker_dividends__member")
            .order_by("-period_end")
        )

        aggregates = SurplusDistribution.objects.aggregate(
            comm_total=Sum("community_pool_usd"),
            reinv_total=Sum("reinvestment_reserve_usd"),
            worker_total=Sum("worker_pool_usd"),
            dist_total=Sum("distributable_surplus_usd"),
        )

        context = {
            "worker_members_count": worker_members_count,
            "active_workers": active_workers,
            "distributions": distributions,
            "total_community_fund": aggregates["comm_total"] or Decimal("0.00"),
            "total_reinvestment_reserve": aggregates["reinv_total"] or Decimal("0.00"),
            "total_worker_pool": aggregates["worker_total"] or Decimal("0.00"),
            "total_distributable_surplus": aggregates["dist_total"] or Decimal("0.00"),
        }
        return render(request, "governance/dashboard.html", context)
