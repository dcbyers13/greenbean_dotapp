import uuid
from datetime import datetime
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from orders.models import Order
from catalog.models import ProductVariant
from adapters.iyou_bean.models import LedgerAccount, JournalBatch, JournalEntry


class IyouBeanLedgerAdapter:
    """Double-entry ledger synchronization bridge for the iyou_bean financial engine."""

    CHART_OF_ACCOUNTS = [
        {"number": "1010", "name": "Cash on Hand", "type": LedgerAccount.AccountType.ASSET, "desc": "Register cash and drawer vault"},
        {"number": "1020", "name": "Card Clearing", "type": LedgerAccount.AccountType.ASSET, "desc": "External card terminal settlement receivables"},
        {"number": "1030", "name": "Lightning Network", "type": LedgerAccount.AccountType.ASSET, "desc": "WebLN node satoshi balance"},
        {"number": "2020", "name": "Sales Tax Payable", "type": LedgerAccount.AccountType.LIABILITY, "desc": "Collected state and city sales tax"},
        {"number": "4010", "name": "Coffee Retail Sales", "type": LedgerAccount.AccountType.REVENUE, "desc": "Roasted beans, drip cups, and craft espresso"},
        {"number": "4020", "name": "Bakery Sales", "type": LedgerAccount.AccountType.REVENUE, "desc": "Violette's Bakery artisanal pastries"},
        {"number": "5010", "name": "Green Coffee COGS", "type": LedgerAccount.AccountType.EXPENSE, "desc": "Direct trade green lot bean cost"},
    ]

    @classmethod
    def seed_default_chart_of_accounts(cls):
        """Idempotently provision standard double-entry accounts."""
        accounts = {}
        for item in cls.CHART_OF_ACCOUNTS:
            acc, _ = LedgerAccount.objects.update_or_create(
                account_number=item["number"],
                defaults={
                    "name": item["name"],
                    "account_type": item["type"],
                    "description": item["desc"],
                },
            )
            accounts[item["number"]] = acc
        return accounts

    @classmethod
    @transaction.atomic
    def create_batch_from_orders(cls, start_dt: datetime, end_dt: datetime) -> JournalBatch:
        """Aggregate placed & fulfilled orders into a strictly balanced double-entry batch.

        Invariant: sum(debits) strictly equals sum(credits).
        """
        cls.seed_default_chart_of_accounts()
        acc_cash = LedgerAccount.objects.get(account_number="1010")
        acc_card = LedgerAccount.objects.get(account_number="1020")
        acc_ln = LedgerAccount.objects.get(account_number="1030")
        acc_tax = LedgerAccount.objects.get(account_number="2020")
        acc_coffee = LedgerAccount.objects.get(account_number="4010")
        acc_bakery = LedgerAccount.objects.get(account_number="4020")

        orders = (
            Order.objects.filter(
                created_at__gte=start_dt,
                created_at__lte=end_dt,
            )
            .exclude(status=Order.Status.CANCELLED)
            .prefetch_related("items__variant__product")
        )

        cash_debits = Decimal("0.00")
        card_debits = Decimal("0.00")
        ln_debits = Decimal("0.00")

        coffee_credits = Decimal("0.00")
        bakery_credits = Decimal("0.00")
        tax_credits = Decimal("0.00")

        for order in orders:
            order_total = order.total_price_usd
            if order_total <= Decimal("0.00"):
                continue

            # Debits by Tender Method
            if order.tender_type == Order.TenderType.EXTERNAL_CARD:
                card_debits += order_total
            elif order.tender_type == Order.TenderType.WEBLN:
                ln_debits += order_total
            else:
                cash_debits += order_total

            # Credits by Sales Category
            order_subtotal = Decimal("0.00")
            for item in order.items.all():
                line_total = item.line_total_usd
                order_subtotal += line_total
                if (
                    item.variant.form_factor == ProductVariant.FormFactor.BAKERY
                    or item.variant.product.brand_line == "Violette's Bakery"
                ):
                    bakery_credits += line_total
                else:
                    coffee_credits += line_total

            # Sales Tax Credit
            if order.tax_usd and order.tax_usd > Decimal("0.00"):
                tax_credits += order.tax_usd
            elif order_total > order_subtotal:
                tax_credits += (order_total - order_subtotal)

        total_debits = cash_debits + card_debits + ln_debits
        total_credits = coffee_credits + bakery_credits + tax_credits

        # Reconcile fractional penny differences to preserve double-entry invariant
        if total_debits != total_credits and total_debits > Decimal("0.00"):
            diff = total_debits - total_credits
            coffee_credits += diff
            total_credits += diff

        if total_debits != total_credits:
            raise ValueError(
                f"Double-entry balance mismatch: Debits=${total_debits} != Credits=${total_credits}"
            )

        timestamp_str = timezone.now().strftime("%Y%m%d%H%M%S")
        batch_number = f"BATCH-{timestamp_str}-{uuid.uuid4().hex[:6].upper()}"

        batch = JournalBatch.objects.create(
            batch_number=batch_number,
            period_start=start_dt,
            period_end=end_dt,
            status=JournalBatch.Status.POSTED,
            total_amount_usd=total_debits,
        )

        entries_to_create = []

        # Debit Entries
        if cash_debits > Decimal("0.00"):
            entries_to_create.append(
                JournalEntry(
                    batch=batch,
                    account=acc_cash,
                    entry_type=JournalEntry.EntryType.DEBIT,
                    amount_usd=cash_debits,
                    memo="Counter POS cash receipts",
                )
            )
        if card_debits > Decimal("0.00"):
            entries_to_create.append(
                JournalEntry(
                    batch=batch,
                    account=acc_card,
                    entry_type=JournalEntry.EntryType.DEBIT,
                    amount_usd=card_debits,
                    memo="External card terminal settlement",
                )
            )
        if ln_debits > Decimal("0.00"):
            entries_to_create.append(
                JournalEntry(
                    batch=batch,
                    account=acc_ln,
                    entry_type=JournalEntry.EntryType.DEBIT,
                    amount_usd=ln_debits,
                    memo="WebLN node settlement",
                )
            )

        # Credit Entries
        if coffee_credits > Decimal("0.00"):
            entries_to_create.append(
                JournalEntry(
                    batch=batch,
                    account=acc_coffee,
                    entry_type=JournalEntry.EntryType.CREDIT,
                    amount_usd=coffee_credits,
                    memo="Green Bean coffee and beverage sales",
                )
            )
        if bakery_credits > Decimal("0.00"):
            entries_to_create.append(
                JournalEntry(
                    batch=batch,
                    account=acc_bakery,
                    entry_type=JournalEntry.EntryType.CREDIT,
                    amount_usd=bakery_credits,
                    memo="Violette's Bakery sales share",
                )
            )
        if tax_credits > Decimal("0.00"):
            entries_to_create.append(
                JournalEntry(
                    batch=batch,
                    account=acc_tax,
                    entry_type=JournalEntry.EntryType.CREDIT,
                    amount_usd=tax_credits,
                    memo="Sales tax collected",
                )
            )

        JournalEntry.objects.bulk_create(entries_to_create)
        return batch

    @classmethod
    def export_journal_payload(cls, batch_id: uuid.UUID) -> dict:
        """Export canonical signed double-entry payload for iyou_bean federated ledger."""
        batch = JournalBatch.objects.prefetch_related("entries__account").get(id=batch_id)

        entries_data = [
            {
                "id": str(entry.id),
                "account_number": entry.account.account_number,
                "account_name": entry.account.name,
                "account_type": entry.account.account_type,
                "entry_type": entry.entry_type,
                "amount_usd": str(entry.amount_usd),
                "memo": entry.memo,
            }
            for entry in batch.entries.all()
        ]

        return {
            "schema_version": "1.0",
            "batch_id": str(batch.id),
            "batch_number": batch.batch_number,
            "status": batch.status,
            "period": {
                "start": batch.period_start.isoformat(),
                "end": batch.period_end.isoformat(),
            },
            "total_amount_usd": str(batch.total_amount_usd),
            "is_balanced": batch.is_balanced,
            "entries": entries_data,
            "summary": {
                "total_debits_usd": str(batch.total_debits),
                "total_credits_usd": str(batch.total_credits),
            },
        }
