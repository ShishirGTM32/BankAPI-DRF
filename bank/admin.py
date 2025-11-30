# admin.py
from django.contrib import admin
from .models import CustomUser, Account, Transaction, Loan, LoanInterest

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active']
    list_filter = ['is_staff', 'is_active', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['-date_joined']

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['account_number', 'user', 'account_type', 'balance', 'currency', 'is_active', 'created_at']
    list_filter = ['account_type', 'is_active', 'currency']
    search_fields = ['account_number', 'user__username', 'user__email']
    readonly_fields = ['account_number', 'created_at', 'updated_at']
    ordering = ['-created_at']

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'account', 'transaction_type', 'amount', 'status', 'created_at']
    list_filter = ['transaction_type', 'status', 'created_at']
    search_fields = ['account__account_number', 'description']
    readonly_fields = ['id', 'balance_after', 'created_at']
    ordering = ['-created_at']

@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ['loan_id', 'borrower', 'loan_amount', 'interest_rate', 'loan_term_months', 'monthly_payment', 'status', 'applied_date']
    list_filter = ['status', 'is_accepted', 'applied_date']
    search_fields = ['borrower__account_number', 'borrower__user__username']
    readonly_fields = ['loan_id', 'monthly_payment', 'applied_date', 'accepted_date', 'total_payable_display', 'remaining_amount_display', 'total_paid_display']
    ordering = ['-applied_date']
    
    fieldsets = (
        ('Loan Information', {
            'fields': ('loan_id', 'borrower', 'loan_amount', 'interest_rate', 'loan_term_months')
        }),
        ('Payment Details', {
            'fields': ('monthly_payment', 'total_payable_display', 'total_paid_display', 'remaining_amount_display')
        }),
        ('Status', {
            'fields': ('status', 'is_accepted', 'purpose')
        }),
        ('Dates', {
            'fields': ('applied_date', 'accepted_date', 'next_payment_date', 'last_payment_date')
        }),
    )
    
    def total_payable_display(self, obj):
        return f"NPR {obj.total_payable():,.2f}"
    total_payable_display.short_description = 'Total Payable'
    
    def remaining_amount_display(self, obj):
        return f"NPR {obj.remaining_amount():,.2f}"
    remaining_amount_display.short_description = 'Remaining Amount'
    
    def total_paid_display(self, obj):
        return f"NPR {obj.total_paid():,.2f}"
    total_paid_display.short_description = 'Total Paid'

@admin.register(LoanInterest)
class LoanInterestAdmin(admin.ModelAdmin):
    list_display = ['id', 'loan', 'amount', 'payment_date', 'payment_method']
    list_filter = ['payment_date', 'payment_method']
    search_fields = ['loan__loan_id', 'transaction_id', 'notes']
    readonly_fields = ['id', 'payment_date']
    ordering = ['-payment_date']