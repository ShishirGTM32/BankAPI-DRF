# serializers.py
from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import CustomUser, Account, Transaction, Loan, LoanInterest

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'phone', 'address', 'date_of_birth', 'is_staff']
        read_only_fields = ['id']

class UserRegistrationSerializer(serializers.ModelSerializer):
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password', 'password_confirm', 'first_name', 'last_name', 'phone', 'address', 'date_of_birth']
        extra_kwargs = {'password': {'write_only': True}}
    
    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("Passwords do not match")
        return data
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = CustomUser.objects.create_user(**validated_data)
        return user

class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        user = authenticate(username=data['username'], password=data['password'])
        if not user:
            raise serializers.ValidationError("Invalid credentials")
        return user

class AccountSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Account
        fields = ['id', 'user', 'account_number', 'account_type', 'balance', 'currency', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'account_number', 'created_at', 'updated_at', 'is_active']

class TransactionSerializer(serializers.ModelSerializer):
    recipient_account_number = serializers.CharField(source='recipient_account.account_number', read_only=True)
    
    class Meta:
        model = Transaction
        fields = ['id', 'account', 'transaction_type', 'amount', 'balance_after', 'description', 'recipient_account', 'recipient_account_number', 'status', 'created_at']
        read_only_fields = ['id', 'balance_after', 'status', 'created_at']

class LoanSerializer(serializers.ModelSerializer):
    borrower_name = serializers.CharField(source='borrower.user.username', read_only=True)
    total_payable = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    remaining_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_paid = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    
    class Meta:
        model = Loan
        fields = [
            'loan_id', 'borrower', 'borrower_name', 'loan_amount', 'interest_rate', 
            'loan_term_months', 'monthly_payment', 'status', 'is_accepted', 
            'applied_date', 'accepted_date', 'next_payment_date', 'last_payment_date',
        'purpose', 'total_payable', 'remaining_amount', 'total_paid'
        ]
        read_only_fields = ['loan_id', 'monthly_payment', 'status', 'is_accepted', 'applied_date', 'accepted_date', 'borrower']
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['total_payable'] = instance.total_payable()
        representation['remaining_amount'] = instance.remaining_amount()
        representation['total_paid'] = instance.total_paid()
        return representation

class LoanInterestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanInterest
        fields = ['id', 'loan', 'amount', 'payment_date', 'payment_method', 'notes', 'transaction_id']
        read_only_fields = ['id', 'loan', 'payment_date', 'payment_method']