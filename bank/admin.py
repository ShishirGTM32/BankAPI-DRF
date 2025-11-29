from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Account, Transaction

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('phone', 'address', 'date_of_birth')}),
    )
    list_display = ['username', 'email', 'first_name', 'last_name', 'phone', 'is_staff']

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['account_number', 'user', 'account_type', 'balance', 'currency', 'is_active', 'created_at']
    list_filter = ['account_type', 'is_active', 'currency']
    search_fields = ['account_number', 'user__username']
    readonly_fields = ['account_number', 'created_at', 'updated_at']

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_id', 'account', 'transaction_type', 'amount', 'status', 'created_at']
    list_filter = ['transaction_type', 'status', 'created_at']
    search_fields = ['transaction_id', 'account__account_number']
    readonly_fields = ['transaction_id', 'balance_after', 'created_at']