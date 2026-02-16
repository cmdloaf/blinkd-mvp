from django import forms

from .models import ProductFlow
from .personas import PERSONA_CHOICES


class ProductBackgroundForm(forms.ModelForm):
    class Meta:
        model = ProductFlow
        fields = ["product_background"]
        widgets = {
            "product_background": forms.Textarea(attrs={
                "rows": 10,
                "placeholder": (
                    "Describe your product: what it does, its value proposition, "
                    "target audience, and key use cases."
                ),
            }),
        }


class PersonaSelectionForm(forms.Form):
    persona_type = forms.ChoiceField(
        choices=PERSONA_CHOICES,
        widget=forms.RadioSelect,
    )
    custom_persona_description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "rows": 6,
            "placeholder": (
                "Describe your persona: their age, role, tech comfort level, "
                "what motivates them, what frustrates them, and how they "
                "typically interact with digital products."
            ),
        }),
    )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("persona_type") == "custom":
            desc = cleaned_data.get("custom_persona_description", "").strip()
            if not desc:
                self.add_error(
                    "custom_persona_description",
                    "Please describe your custom persona.",
                )
        return cleaned_data
