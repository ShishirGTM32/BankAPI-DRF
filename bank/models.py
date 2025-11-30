# models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import random
import string

class CustomUser(AbstractUser):
    phone = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    
    def __str__(self):
        return self.username

class Account(models.Model):
    ACCOUNT_TYPES = [
        ('SAVINGS', 'Savings'),
        ('CHECKING', 'Checking'),
        ('BUSINESS', 'Business'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='accounts')
    account_number = models.CharField(max_length=20, unique=True)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    currency = models.CharField(max_length=3, default='NPR')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.account_number:
            self.account_number = self.generate_account_number()
        super().save(*args, **kwargs)
    
    def generate_account_number(self):
        return ''.join(random.choices(string.digits, k=12))
    
    def __str__(self):
        return f"{self.account_number} - {self.user.username}"

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('DEPOSIT', 'Deposit'),
        ('WITHDRAWAL', 'Withdrawal'),
        ('TRANSFER', 'Transfer'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    balance_after = models.DecimalField(max_digits=15, decimal_places=2)
    description = models.TextField(blank=True)
    recipient_account = models.ForeignKey(
        Account, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='received_transactions'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.transaction_type} - {self.amount} - {self.created_at}"

class Loan(models.Model):
    LOAN_STATUS = [
        ('PENDING', 'Pending'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
        ('PAID', 'Paid'),
    ]
    
    loan_id = models.AutoField(primary_key=True)
    borrower = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='loans')
    loan_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal('10000.00')),
            MaxValueValidator(Decimal('5000000.00'))  # Max 50 Lakh NPR
        ]
    )
    interest_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=12.00,
        validators=[
            MinValueValidator(Decimal('5.00')),
            MaxValueValidator(Decimal('25.00'))
        ]
    )  # Annual interest rate
    loan_term_months = models.IntegerField(
        validators=[
            MinValueValidator(6),
            MaxValueValidator(120)  # Max 10 years
        ]
    )
    monthly_payment = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=LOAN_STATUS, default='PENDING')
    is_accepted = models.BooleanField(default=False)
    applied_date = models.DateTimeField(auto_now_add=True)
    accepted_date = models.DateTimeField(null=True, blank=True)
    next_payment_date = models.DateField(null=True, blank=True)
    last_payment_date = models.DateField(null=True, blank=True)
    purpose = models.TextField(blank=True, null=True, help_text="Purpose of the loan")
    
    def calculate_monthly_payment(self):
        """
        Calculate EMI using formula: P * r * (1+r)^n / ((1+r)^n - 1)
        P = Principal loan amount
        r = Monthly interest rate (annual rate / 12 / 100)
        n = Number of months
        """
        if self.interest_rate > 0 and self.loan_term_months > 0:
            principal = float(self.loan_amount)
            monthly_rate = (float(self.interest_rate) / 100) / 12
            n = self.loan_term_months
            
            if monthly_rate > 0:
                emi = principal * monthly_rate * ((1 + monthly_rate) ** n) / (((1 + monthly_rate) ** n) - 1)
                return Decimal(str(round(emi, 2)))
        return Decimal('0.00')
    
    def total_payable(self):
        """Calculate total amount to be paid"""
        return self.monthly_payment * self.loan_term_months
    
    def remaining_amount(self):
        """Calculate remaining loan amount"""
        paid = sum(float(payment.amount) for payment in self.payments.all())
        total = float(self.total_payable())
        return max(Decimal(str(total - paid)), Decimal('0.00'))
    
    def total_paid(self):
        """Calculate total amount paid so far"""
        return sum(float(payment.amount) for payment in self.payments.all())
    
    def save(self, *args, **kwargs):
        if not self.monthly_payment or self.monthly_payment == 0:
            self.monthly_payment = self.calculate_monthly_payment()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Loan #{self.loan_id} - {self.borrower.user.username} - {self.status}"

class LoanInterest(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=50, default='Online Transfer')
    notes = models.TextField(blank=True)
    transaction_id = models.CharField(max_length=50, blank=True, null=True)
    
    class Meta:
        ordering = ['-payment_date']
    
    def __str__(self):
        return f"Payment for Loan #{self.loan.loan_id} - NPR {self.amount}"