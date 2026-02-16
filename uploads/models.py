import uuid

from django.db import models

from .personas import PERSONA_CHOICES


class ProductFlow(models.Model):
    ANALYSIS_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("complete", "Complete"),
        ("failed", "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product_background = models.TextField(
        help_text="Product description, value prop, target audience, use cases"
    )
    persona_type = models.CharField(max_length=50, choices=PERSONA_CHOICES, default="")
    custom_persona_description = models.TextField(blank=True, default="")
    goals = models.TextField(
        blank=True, default="",
        help_text="What the persona should be able to achieve with this flow",
    )
    analysis_status = models.CharField(
        max_length=20,
        choices=ANALYSIS_STATUS_CHOICES,
        default="pending",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"ProductFlow {self.id} ({self.created_at:%Y-%m-%d})"


class Screenshot(models.Model):
    product_flow = models.ForeignKey(
        ProductFlow, on_delete=models.CASCADE, related_name="screenshots"
    )
    image = models.ImageField(upload_to="screenshots/%Y/%m/%d/")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"Screenshot {self.order} for {self.product_flow_id}"


class AnalysisResult(models.Model):
    product_flow = models.OneToOneField(
        ProductFlow, on_delete=models.CASCADE, related_name="analysis"
    )
    raw_response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Analysis for {self.product_flow_id}"
