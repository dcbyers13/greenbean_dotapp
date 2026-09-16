import uuid
from decimal import Decimal
from django.db import models


class WorkerMember(models.Model):
    """Worker-owner member of the Green Bean cooperative."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    did = models.CharField(
        max_length=100,
        unique=True,
        help_text="Decentralized Identifier or pubkey",
    )
    role = models.CharField(max_length=50, default="Worker-Owner")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Worker Member"
        verbose_name_plural = "Worker Members"

    def __str__(self):
        return f"{self.name} ({self.did})"


class LaborLog(models.Model):
    """Shift labor logs used to compute proportional patronage dividends."""

    class Station(models.TextChoices):
        BARISTA = "BARISTA", "Barista"
        ROASTER = "ROASTER", "Roaster"
        BAKERY = "BAKERY", "Bakery"
        MAINTENANCE = "MAINTENANCE", "Maintenance"
        ADMIN = "ADMIN", "Administration"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(
        WorkerMember,
        on_delete=models.CASCADE,
        related_name="labor_logs",
    )
    shift_date = models.DateField()
    hours_worked = models.DecimalField(max_digits=6, decimal_places=2)
    station = models.CharField(max_length=30, choices=Station.choices)

    class Meta:
        ordering = ["-shift_date"]
        verbose_name = "Labor Log"
        verbose_name_plural = "Labor Logs"

    def __str__(self):
        return f"{self.member.name} - {self.hours_worked}h ({self.station}) on {self.shift_date}"


class SurplusDistribution(models.Model):
    """Quarterly or annual democratic profit waterfall distribution."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        FINALIZED = "FINALIZED", "Finalized"
        DISBURSED = "DISBURSED", "Disbursed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    period_label = models.CharField(max_length=64)  # e.g. "Q3-2026"
    period_start = models.DateField()
    period_end = models.DateField()
    gross_revenue_usd = models.DecimalField(max_digits=12, decimal_places=2)
    operating_costs_usd = models.DecimalField(max_digits=12, decimal_places=2)
    reinvestment_reserve_usd = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Retained capital for equipment/growth",
    )
    distributable_surplus_usd = models.DecimalField(max_digits=12, decimal_places=2)
    worker_pool_usd = models.DecimalField(max_digits=12, decimal_places=2)
    community_pool_usd = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-period_end"]
        verbose_name = "Surplus Distribution"
        verbose_name_plural = "Surplus Distributions"

    def __str__(self):
        return f"Surplus Distribution {self.period_label} (${self.distributable_surplus_usd})"


class WorkerDividend(models.Model):
    """Individual worker patronage dividend allocation calculated from labor hours."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    distribution = models.ForeignKey(
        SurplusDistribution,
        on_delete=models.CASCADE,
        related_name="worker_dividends",
    )
    member = models.ForeignKey(
        WorkerMember,
        on_delete=models.CASCADE,
        related_name="dividends",
    )
    hours_worked = models.DecimalField(max_digits=6, decimal_places=2)
    share_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    dividend_usd = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ("distribution", "member")
        ordering = ["-dividend_usd", "member__name"]

    def __str__(self):
        return f"{self.member.name}: ${self.dividend_usd} ({self.share_percentage}%)"
