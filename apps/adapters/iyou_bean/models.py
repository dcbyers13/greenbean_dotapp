import uuid
from decimal import Decimal
from django.db import models


class LedgerAccount(models.Model):
    """Chart of Accounts ledger account for double-entry bookkeeping."""

    class AccountType(models.TextChoices):
        ASSET = "ASSET", "Asset"
        LIABILITY = "LIABILITY", "Liability"
        EQUITY = "EQUITY", "Equity"
        REVENUE = "REVENUE", "Revenue"
        EXPENSE = "EXPENSE", "Expense"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account_number = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, choices=AccountType.choices)
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Ledger Account"
        verbose_name_plural = "Ledger Accounts"
        ordering = ["account_number"]

    def __str__(self):
        return f"{self.account_number} — {self.name} ({self.get_account_type_display()})"


class JournalBatch(models.Model):
    """Batch of double-entry journal entries representing a settlement period."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        POSTED = "POSTED", "Posted"
        SYNCED = "SYNCED", "Synced with iyou_bean"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch_number = models.CharField(max_length=32, unique=True, db_index=True)
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.POSTED,
    )
    total_amount_usd = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Journal Batch"
        verbose_name_plural = "Journal Batches"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Batch {self.batch_number} (${self.total_amount_usd}) [{self.get_status_display()}]"

    @property
    def total_debits(self) -> Decimal:
        return sum(
            (e.amount_usd for e in self.entries.filter(entry_type=JournalEntry.EntryType.DEBIT)),
            Decimal("0.00"),
        )

    @property
    def total_credits(self) -> Decimal:
        return sum(
            (e.amount_usd for e in self.entries.filter(entry_type=JournalEntry.EntryType.CREDIT)),
            Decimal("0.00"),
        )

    @property
    def is_balanced(self) -> bool:
        """Double-entry invariant: sum(debits) must equal sum(credits)."""
        return self.total_debits == self.total_credits


class JournalEntry(models.Model):
    """Individual debit or credit line item in a balanced journal batch."""

    class EntryType(models.TextChoices):
        DEBIT = "DEBIT", "Debit"
        CREDIT = "CREDIT", "Credit"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(
        JournalBatch,
        on_delete=models.CASCADE,
        related_name="entries",
    )
    account = models.ForeignKey(
        LedgerAccount,
        on_delete=models.PROTECT,
        related_name="entries",
    )
    entry_type = models.CharField(max_length=10, choices=EntryType.choices)
    amount_usd = models.DecimalField(max_digits=10, decimal_places=2)
    memo = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Journal Entry"
        verbose_name_plural = "Journal Entries"
        ordering = ["batch", "entry_type", "account"]

    def __str__(self):
        return f"{self.entry_type} ${self.amount_usd} -> {self.account.account_number} ({self.memo})"
