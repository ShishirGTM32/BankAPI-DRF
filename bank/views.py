from decimal import Decimal
from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView    
from rest_framework.authtoken.models import Token
from django.db import transaction
from django.shortcuts import render
from .models import CustomUser, Account, Transaction
from django.contrib.auth import login
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserSerializer,
    AccountSerializer, TransactionSerializer
)

class UserRegistrationView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            'user': UserSerializer(user).data,
            'token': token.key,
            "created":created
        }, status=status.HTTP_201_CREATED)


class UserLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data

        # Create session login
        login(request, user)  

        # Token for frontend storage
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            'user': UserSerializer(user).data,
            'token': token.key,
            'created': created
        })

class UserLogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        request.user.auth_token.delete()
        return Response({'message': 'Successfully logged out'}, status=status.HTTP_200_OK)


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class AccountListCreateView(generics.ListCreateAPIView):
    serializer_class = AccountSerializer
    permission_classes = [permissions.IsAuthenticated]
    

    def get_queryset(self):
        return Account.objects.filter(user=self.request.user, is_active=True)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AccountDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AccountSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Account.objects.filter(user=self.request.user)


class TransactionListView(generics.ListAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        account_id = self.kwargs.get('account_id')
        queryset = Transaction.objects.filter(account_id=account_id)

        transaction_type = self.request.query_params.get('type')
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type.upper())
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status.upper())
        return queryset
    
class TransactionHTMLView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, account_id):
        transactions = Transaction.objects.filter(account_id=account_id).order_by('-created_at')
        return render(request, "transactions.html", {"transactions": transactions})

class BalanceEnquiry(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AccountSerializer

    def get_object(self):
        account_id = self.kwargs.get('account_id')
        return Account.objects.get(user=self.request.user, id=account_id)

    def retrieve(self, request, *args, **kwargs):
        account = self.get_object()
        return Response({"balance": account.balance}, status=status.HTTP_200_OK)


class DepositView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, account_id):
        try:
            account = Account.objects.select_for_update().get(id=account_id, user=request.user)
        except Account.DoesNotExist:
            return Response({'error': 'Account not found'}, status=status.HTTP_404_NOT_FOUND)

        amount = request.data.get('amount')
        if not amount or float(amount) <= 0:
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)

        account.balance += Decimal(amount)
        account.save()

        trans = Transaction.objects.create(
            account=account,
            transaction_type='DEPOSIT',
            amount=amount,
            balance_after=account.balance,
            description=request.data.get('description', ''),
            status='COMPLETED'
        )

        return Response(TransactionSerializer(trans).data, status=status.HTTP_201_CREATED)


class WithdrawalView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, account_id):
        try:
            account = Account.objects.select_for_update().get(id=account_id, user=request.user)
        except Account.DoesNotExist:
            return Response({'error': 'Account not found'}, status=status.HTTP_404_NOT_FOUND)

        amount = request.data.get('amount')
        if not amount or float(amount) <= 0:
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)

        if account.balance < Decimal(amount):
            return Response({'error': 'Insufficient funds'}, status=status.HTTP_400_BAD_REQUEST)

        account.balance -= Decimal(amount)
        account.save()

        trans = Transaction.objects.create(
            account=account,
            transaction_type='WITHDRAWAL',
            amount=amount,
            balance_after=account.balance,
            description=request.data.get('description', ''),
            status='COMPLETED'
        )
    
        return Response(TransactionSerializer(trans).data, status=status.HTTP_201_CREATED)

class TransferView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    @transaction.atomic
    def post(self, request, account_id):
        try:
            account = Account.objects.select_for_update().get(id=account_id, user=request.user)
        except Account.DoesNotExist:
            return Response({'error': 'Account not found'}, status=status.HTTP_404_NOT_FOUND)
        
        amount = request.data.get('amount')
        recipient_account_number = request.data.get('recipient_account_number')  # Changed
        
        if not amount or float(amount) <= 0:
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)

        if not recipient_account_number:
            return Response({'error': 'Recipient account number is required'}, status=status.HTTP_400_BAD_REQUEST)

        if account.balance < Decimal(amount):
            return Response({'error': 'Insufficient funds'}, status=status.HTTP_400_BAD_REQUEST)
    
        try:
            recipient_account = Account.objects.get(account_number=recipient_account_number)  # Changed
        except Account.DoesNotExist:
            return Response({'error': 'Recipient account not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if account.id == recipient_account.id:
            return Response({'error': 'Cannot transfer to the same account'}, status=status.HTTP_400_BAD_REQUEST)
        
        account.balance -= Decimal(amount)
        account.save()

        recipient_account.balance += Decimal(amount)
        recipient_account.save()

        trans = Transaction.objects.create(
            account=account,
            transaction_type='TRANSFER',
            amount=amount,
            balance_after=account.balance,
            description=request.data.get('description', ''),
            recipient_account=recipient_account,
            status='COMPLETED'
        )

        return Response(TransactionSerializer(trans).data, status=status.HTTP_201_CREATED)
        

