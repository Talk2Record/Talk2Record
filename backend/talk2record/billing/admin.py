from django.contrib import admin

from .models import Plan
from .models import Subscription
from .models import Transaction


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "base_price", "currency", "region", "is_active"]
    search_fields = ["name", "code", "region"]
    list_filter = ["currency", "is_active"]


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ["organization", "plan", "provider", "status", "amount", "currency", "current_period_end"]
    search_fields = ["organization__name", "provider_subscription_id"]
    list_filter = ["provider", "status", "currency"]


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ["subscription", "invoice_number", "amount", "currency", "status", "issued_at"]
    search_fields = ["invoice_number", "provider_transaction_id", "subscription__organization__name"]
    list_filter = ["status", "currency"]
