import uuid
from django.db import models


class RoastProfile(models.Model):
    """Artisanal roasting curve configuration and sensory characteristics."""

    class RoastLevel(models.TextChoices):
        LIGHT = "LIGHT", "Light"
        MEDIUM_LIGHT = "MEDIUM_LIGHT", "Medium-Light"
        MEDIUM = "MEDIUM", "Medium"
        MEDIUM_DARK = "MEDIUM_DARK", "Medium-Dark"
        DARK = "DARK", "Dark"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    roast_name = models.CharField(max_length=100)
    roast_level = models.CharField(
        max_length=20,
        choices=RoastLevel.choices,
        default=RoastLevel.MEDIUM,
    )
    tasting_notes = models.CharField(
        max_length=255,
        help_text="e.g. Citrus, Jasmine, Milk Chocolate",
    )
    target_drop_temp_f = models.PositiveIntegerField(default=415)
    development_time_sec = models.PositiveIntegerField(default=120)

    class Meta:
        verbose_name = "Roast Profile"
        verbose_name_plural = "Roast Profiles"
        ordering = ["roast_name"]

    def __str__(self):
        return f"{self.roast_name} ({self.get_roast_level_display()})"
