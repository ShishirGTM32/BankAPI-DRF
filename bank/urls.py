from django.urls import path
from .views import (
    UserRegistrationView, UserLoginView, UserLogoutView, UserProfileView,
    AccountListCreateView, AccountDetailView, TransactionListView,
    DepositView, WithdrawalView, TransferView, BalanceEnquiry, TransactionHTMLView
)

urlpatterns = [
    path('auth/register/', UserRegistrationView.as_view(), name='register'),
    path('auth/login/', UserLoginView.as_view(), name='login'),
    path('auth/logout/', UserLogoutView.as_view(), name='logout'),
    path('auth/profile/', UserProfileView.as_view(), name='profile'),
    
    path('accounts/', AccountListCreateView.as_view(), name='account-list'),
    path('accounts/<int:pk>/', AccountDetailView.as_view(), name='account-detail'),
    path('accounts/<int:account_id>/balance/', BalanceEnquiry.as_view(), name='balance-enquiry'),
  
    path('accounts/<int:account_id>/transactions/', TransactionListView.as_view(), name='transaction-list'),
    path('accounts/<int:account_id>/deposit/', DepositView.as_view(), name='deposit'),
    path('accounts/<int:account_id>/withdraw/', WithdrawalView.as_view(), name='withdraw'),
    path('accounts/<int:account_id>/transfer/', TransferView.as_view(), name='transfer'),
    path("accounts/<int:account_id>/transactions-page/", TransactionHTMLView.as_view()),

]
