import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse

from .personas import PERSONA_CHOICES


class ProductFlow(models.Model):
    ANALYSIS_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("complete", "Complete"),
        ("failed", "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="flows",
    )
    name = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Short name for this test run, e.g. 'Onboarding flow v2'",
    )
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

    @property
    def title(self):
        if self.name and self.name.strip():
            return self.name.strip()
        first_line = self.product_background.strip().split("\n")[0]
        if not first_line:
            return "Untitled flow"
        return first_line[:80] + "…" if len(first_line) > 80 else first_line

    def get_next_url(self):
        if not self.screenshots.exists():
            return reverse("uploads:step2", kwargs={"flow_id": self.id})
        if not self.persona_type:
            return reverse("uploads:step3", kwargs={"flow_id": self.id})
        if not self.goals:
            return reverse("uploads:step4", kwargs={"flow_id": self.id})
        return reverse("uploads:confirm", kwargs={"flow_id": self.id})


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
