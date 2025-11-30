# urls.py
from django.urls import path
from .views import (
    UserRegistrationView, UserLoginView, UserLogoutView, UserProfileView,
    AccountListCreateView, AccountDetailView, TransactionListView,
    DepositView, WithdrawalView, TransferView, BalanceEnquiry, 
    LoanView, LoanInterestView,
    AdminDashboardView, AdminUserManagementView, AdminAccountManagementView,
    AdminLoanManagementView
)

urlpatterns = [
    # Authentication
    path('auth/register/', UserRegistrationView.as_view(), name='register'),
    path('auth/login/', UserLoginView.as_view(), name='login'),
    path('auth/logout/', UserLogoutView.as_view(), name='logout'),
    path('auth/profile/', UserProfileView.as_view(), name='profile'),
    
    # Accounts
    path('accounts/', AccountListCreateView.as_view(), name='account-list'),
    path('accounts/<int:pk>/', AccountDetailView.as_view(), name='account-detail'),
    path('accounts/<int:account_id>/balance/', BalanceEnquiry.as_view(), name='balance-enquiry'),
  
    # Transactions
    path('accounts/<int:account_id>/transactions/', TransactionListView.as_view(), name='transaction-list'),
    path('accounts/<int:account_id>/deposit/', DepositView.as_view(), name='deposit'),  # Admin only
    path('accounts/<int:account_id>/withdraw/', WithdrawalView.as_view(), name='withdraw'),  # Admin only
    path('accounts/<int:account_id>/transfer/', TransferView.as_view(), name='transfer'),  # User
    
    # Loans
    path('loans/', LoanView.as_view(), name='loan-list'),  # Get all user loans
    path('accounts/<int:account_id>/loan/', LoanView.as_view(), name='loan-create'),
    path('accounts/<int:account_id>/loan/<int:loan_id>/payment/', LoanInterestView.as_view(), name="loan-payment"), 
    
    # Admin endpoints
    path('admin/dashboard/', AdminDashboardView.as_view(), name='admin-dashboard'),
    path('admin/users/', AdminUserManagementView.as_view(), name='admin-users'),
    path('admin/users/<int:user_id>/', AdminUserManagementView.as_view(), name='admin-user-detail'),
    path('admin/accounts/', AdminAccountManagementView.as_view(), name='admin-accounts'),
    path('admin/loans/', AdminLoanManagementView.as_view(), name='admin-loans'),
    path('admin/loans/<int:loan_id>/', AdminLoanManagementView.as_view(), name='admin-loan-action'),
]