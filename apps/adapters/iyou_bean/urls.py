from django.urls import path
from adapters.iyou_bean import views

app_name = "iyou_bean"

urlpatterns = [
    path(
        "batches/<uuid:batch_id>/export/",
        views.JournalBatchExportView.as_view(),
        name="batch_export",
    ),
]
