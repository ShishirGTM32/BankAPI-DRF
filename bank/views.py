# views.py
from decimal import Decimal
from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView    
from rest_framework.authtoken.models import Token
from django.http import JsonResponse, FileResponse
from celery.result import AsyncResult
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.contrib.auth import login
from django.utils import timezone
from datetime import timedelta
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .models import CustomUser, Account, Transaction, Loan
from .permissions import IsAdminUser
from .tasks import send_transaction_email, send_transfer_email, welcome_user, generate_transaction_pdf, loan_accepted
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserSerializer,
    AccountSerializer, TransactionSerializer, LoanSerializer, LoanInterestSerializer
)


class UserRegistrationView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        print(user.email)
        token, created = Token.objects.get_or_create(user=user)
        welcome_user.delay(user.email)
        return Response({
            'user': UserSerializer(user).data,
            'token': token.key,
            'is_admin': user.is_staff,
            "created": created
        }, status=status.HTTP_201_CREATED)

class UserLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data

        login(request, user)  
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            'user': UserSerializer(user).data,
            'token': token.key,
            'is_admin': user.is_staff,
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
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param.upper())
        return queryset

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
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    @transaction.atomic
    def post(self, request, account_id):
        try:
            account = Account.objects.select_for_update().get(id=account_id)
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
            description=request.data.get('description', 'Admin deposit'),
            status='COMPLETED'
        )

        transaction.on_commit(
            lambda: send_transaction_email.delay(account.user.username, amount, trans.transaction_type, trans.description)
        )
        return Response(TransactionSerializer(trans).data, status=status.HTTP_201_CREATED)

class WithdrawalView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    @transaction.atomic
    def post(self, request, account_id):
        try:
            account = Account.objects.select_for_update().get(id=account_id)
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
            description=request.data.get('description', 'Admin withdrawal'),
            status='COMPLETED'
        )

        transaction.on_commit(
            lambda: send_transaction_email.delay(account.user.username, amount, trans.transaction_type, trans.description)
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
        recipient_account_number = request.data.get('recipient_account_number')
        
        if not amount or float(amount) <= 0:
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)

        if not recipient_account_number:
            return Response({'error': 'Recipient account number is required'}, status=status.HTTP_400_BAD_REQUEST)

        if account.balance < Decimal(amount):
            return Response({'error': 'Insufficient funds'}, status=status.HTTP_400_BAD_REQUEST)
    
        try:
            recipient_account = Account.objects.get(account_number=recipient_account_number)  
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
        transaction.on_commit(
            lambda:send_transfer_email(amount, trans.transaction_type, account.user.username, recipient_account.user.username, trans.description)
        )
        return Response(TransactionSerializer(trans).data, status=status.HTTP_201_CREATED)

class LoanView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, account_id=None):
        if account_id:
            loans = Loan.objects.filter(borrower_id=account_id, borrower__user=request.user)
        else:
            user_accounts = Account.objects.filter(user=request.user)
            loans = Loan.objects.filter(borrower__in=user_accounts)
        
        serializer = LoanSerializer(loans, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request, account_id):
        """Apply for a new loan"""
        try:
            account = Account.objects.get(id=account_id, user=request.user)
        except Account.DoesNotExist:
            return Response({'error': 'Account not found'}, status=status.HTTP_404_NOT_FOUND)
        
        active_loans = Loan.objects.filter(
            borrower=account,
            status__in=['PENDING', 'ACCEPTED']
        ).count()

        
        if active_loans >= 2:
            return Response(
                {'error': 'Maximum loan limit reached. You can have up to 3 active loans.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = LoanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(borrower_id=account_id)
        loan_accepted.delay(serializer.instance.loan_id,request.user.username)
        
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class LoanInterestView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, account_id, loan_id):
        loan = get_object_or_404(Loan, loan_id=loan_id, borrower__user=request.user)
        
        if not loan.is_accepted:
            return Response(
                {"error": "Loan is not yet accepted by admin"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if loan.status == 'PAID':
            return Response(
                {"error": "Loan is already fully paid"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = LoanInterestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        entered_amount = serializer.validated_data['amount']
        remaining = loan.remaining_amount()
        
        if entered_amount > remaining:
            return Response(
                {"error": f"Entered amount {entered_amount} exceeds remaining balance {remaining}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update last payment date
        loan.last_payment_date = timezone.now().date()
        
        # Set next payment date (30 days from now)
        if not loan.next_payment_date:
            loan.next_payment_date = timezone.now().date() + timedelta(days=30)
        else:
            loan.next_payment_date = loan.last_payment_date + timedelta(days=30)
        
        loan.save()
        
        serializer.save(loan=loan)

        # Check if loan is fully paid
        if loan.remaining_amount() <= 0:
            loan.status = "PAID"
            loan.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)

class AdminDashboardView(APIView):
    """ADMIN - Dashboard statistics"""
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        stats = {
            'total_users': CustomUser.objects.count(),
            'total_accounts': Account.objects.count(),
            'active_accounts': Account.objects.filter(is_active=True).count(),
            'pending_loans': Loan.objects.filter(status='PENDING').count(),
            'approved_loans': Loan.objects.filter(status='ACCEPTED').count(),
            'total_loans': Loan.objects.count(),
            'total_transactions': Transaction.objects.count(),
        }
        return Response(stats, status=status.HTTP_200_OK)

class AdminUserManagementView(APIView):
    """ADMIN - Manage all users"""
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    def get(self, request, user_id=None):
        if user_id:
            user = get_object_or_404(CustomUser, id=user_id)
            return Response(UserSerializer(user).data, status=status.HTTP_200_OK)
        
        users = CustomUser.objects.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def put(self, request, user_id):
        user = get_object_or_404(CustomUser, id=user_id)
        serializer = UserSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def delete(self, request, user_id):
        user = get_object_or_404(CustomUser, id=user_id)
        username = user.username
        user.delete()
        return Response(
            {"message": f"User '{username}' deleted successfully"},
            status=status.HTTP_200_OK
        )

class AdminAccountManagementView(APIView):
    """ADMIN - View all accounts"""
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        accounts = Account.objects.select_related('user').all()
        serializer = AccountSerializer(accounts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class AdminLoanManagementView(APIView):
    """ADMIN - Manage loans - view, approve, reject"""
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    def get(self, request, loan_id=None):
        if loan_id:
            loan = get_object_or_404(Loan, loan_id=loan_id)
            return Response(LoanSerializer(loan).data, status=status.HTTP_200_OK)
        
        status_filter = request.query_params.get('status', None)
        if status_filter:
            loans = Loan.objects.filter(status=status_filter.upper())
        else:
            loans = Loan.objects.all().order_by('-applied_date')
        
        serializer = LoanSerializer(loans, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def put(self, request, loan_id):
        """Approve or reject loan"""
        loan = get_object_or_404(Loan, loan_id=loan_id)
        action = request.data.get('action') 
        
        if action == 'accept':
            loan.status = 'ACCEPTED'
            loan.is_accepted = True
            loan.accepted_date = timezone.now()
            loan.next_payment_date = timezone.now().date() + timedelta(days=30)
            user = loan.borrower.user.username
            loan_accepted.delay(loan.loan_id, user)
            loan.save()
            return Response(
                {"message": "Loan accepted successfully", "loan": LoanSerializer(loan).data},
                status=status.HTTP_200_OK
            )
        elif action == 'reject':
            loan.status = 'REJECTED'
            loan.is_accepted = False
            loan.save()
            return Response(
                {"message": "Loan rejected", "loan": LoanSerializer(loan).data},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"error": "Invalid action. Use 'accept' or 'reject'"},
                status=status.HTTP_400_BAD_REQUEST
            )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def request_transaction_pdf(request):
    print(request.user)
    task = generate_transaction_pdf.apply_async(args=[request.user.id])
    return JsonResponse({"task_id": task.id})


def check_pdf_status(request, task_id):
    result = AsyncResult(task_id)
    if result.ready():
        filename = result.get()
        return FileResponse(open(filename, "rb"), as_attachment=True, filename="transactions.pdf")
    return JsonResponse({"status": "pending"})
