from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import AllowedEmail, CustomUser, WaitlistEntry


@admin.register(WaitlistEntry)
class WaitlistEntryAdmin(admin.ModelAdmin):
    list_display = ("email", "name", "submitted_at", "is_approved")
    search_fields = ("email", "name")
    readonly_fields = ("submitted_at",)
    actions = ["approve_selected"]

    def is_approved(self, obj):
        return AllowedEmail.objects.filter(email__iexact=obj.email).exists()
    is_approved.boolean = True
    is_approved.short_description = "Approved"

    @admin.action(description="Approve selected → grant app access")
    def approve_selected(self, request, queryset):
        approved = 0
        for entry in queryset:
            _, created = AllowedEmail.objects.get_or_create(
                email=entry.email,
                defaults={"note": f"Approved from waitlist — {entry.name or 'no name'}"},
            )
            if created:
                approved += 1
        self.message_user(request, f"{approved} email(s) approved for access.")


@admin.register(AllowedEmail)
class AllowedEmailAdmin(admin.ModelAdmin):
    list_display = ("email", "note", "added_at")
    search_fields = ("email", "note")
    readonly_fields = ("added_at",)


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    model = CustomUser
    list_display = ("email", "is_active", "is_staff", "date_joined")
    list_filter = ("is_active", "is_staff", "is_superuser")
    ordering = ("-date_joined",)
    search_fields = ("email",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("date_joined",)}),
    )
    readonly_fields = ("date_joined",)
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2", "is_active", "is_staff"),
        }),
    )
