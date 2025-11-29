from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import CustomUser, Account, Transaction

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password', 'password_confirm', 'first_name', 'last_name', 'phone', 'address', 'date_of_birth']

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("Passwords do not match. Re-enter password")
        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            phone=validated_data.get('phone', ''),
            address=validated_data.get('address', ''),
            date_of_birth=validated_data.get('date_of_birth', None)
        )
        return user


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        username = data.get('username')
        password = data.get('password')
        
        if username and password:
            user = authenticate(
                request=self.context.get('request'),
                username=username,
                password=password
            )
            if user:
                if user.is_active:
                    return user
                raise serializers.ValidationError("User account is disabled")
            raise serializers.ValidationError("Invalid username or password")
        raise serializers.ValidationError("Must include username and password")


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'phone', 'address', 'date_of_birth', 'created_at']
        read_only_fields = ['id', 'created_at']


class AccountSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True) 
    
    class Meta:
        model = Account
        fields = ['id', 'account_number', 'user', 'user_username', 'account_type', 'balance', 'currency', 'is_active', 'created_at']
        read_only_fields = ['id', 'account_number', 'created_at', 'user']


class TransactionSerializer(serializers.ModelSerializer):
    account_number = serializers.CharField(source='account.account_number', read_only=True)
    recipient_account_number = serializers.CharField(source='recipient_account.account_number', read_only=True)  # NEW

    class Meta:
        model = Transaction
        fields = [
            'id', 'transaction_id', 'account', 'account_number',
            'transaction_type', 'amount', 'balance_after',
            'description', 'status', 'recipient_account', 'recipient_account_number', 'created_at'
        ]
        read_only_fields = [
            'id', 'transaction_id', 'balance_after', 'status', 'created_at', 'recipient_account_number'
        ]



