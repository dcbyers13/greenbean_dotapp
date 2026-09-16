import uuid
from django.http import JsonResponse, Http404
from django.views import View
from adapters.iyou_bean.services import IyouBeanLedgerAdapter
from adapters.iyou_bean.models import JournalBatch


class JournalBatchExportView(View):
    """Expose balanced double-entry journal batch payload for iyou_bean bridge."""

    def get(self, request, batch_id: uuid.UUID):
        try:
            payload = IyouBeanLedgerAdapter.export_journal_payload(batch_id)
            return JsonResponse(payload, json_dumps_params={"indent": 2})
        except JournalBatch.DoesNotExist:
            raise Http404(f"JournalBatch {batch_id} not found.")
