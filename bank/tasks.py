import time, os
from celery import shared_task
from django.core.mail import EmailMessage
from django.conf import settings
from .models import CustomUser, Transaction, Account, Loan, LoanInterest
from django.template.loader import render_to_string
from django.db.models.functions import TruncDate
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from weasyprint import HTML
from datetime import timedelta

def load_email_template(filename):
    path = os.path.join(settings.BASE_DIR, filename)
    with open(path) as f:
        return f.read()

@shared_task
def welcome_user(email):
    user = CustomUser.objects.get(email=email)
    from_email = settings.EMAIL_HOST_USER
    subject = "Thanks for registration"
    content  = load_email_template("welcome.html").format(
        user=user.username
    )
    email = EmailMessage(
        subject,
        content,
        from_email,
        [email]
    )
    email.content_subtype = "html"
    email.send()

@shared_task
def send_transaction_email(username, amount, transaction_type, description):
    user = CustomUser.objects.get(username=username)
    to = [user.email]
    from_email = settings.EMAIL_HOST_USER
    html_content = load_email_template("email.html").format(
        uname = user.username,
        amt=amount,
        transaction = transaction_type,
        des = description
    )
    subject="Completion of Taransaction"
    email = EmailMessage(
        subject, html_content, from_email, to
    )
    email.content_subtype = "html"
    email.send()


@shared_task
def send_transfer_email(amount, transaction_type, transfer, deposit, description):
    transfer = CustomUser.objects.get(username=transfer)
    deposit = CustomUser.objects.get(username=deposit)
    from_email = settings.EMAIL_HOST_USER
    html_content = load_email_template("send_transfer.html").format(
        uname = transfer.username,
        reciever = deposit.username,
        amt=amount,
        transaction = transaction_type,
        des = description
    )
    subject1="Transfer Succeed"
    email = EmailMessage(
        subject1, html_content, from_email, [transfer.email]
    )
    email.content_subtype = "html"
    email.send()
    html_content2 = load_email_template("recieve_transfer.html").format(
        uname = deposit.username,
        sender = transfer.username,
        amt=amount,
        transaction = transaction_type,
        des = description
    )
    subject2="Recieved Payment"
    email = EmailMessage(
        subject2, html_content2, from_email, [deposit.email]
    )
    email.content_subtype = "html"
    email.send()


@shared_task
def generate_transaction_pdf(user_id):
    user = CustomUser.objects.get(id=user_id)
    one_mth = timezone.now() - relativedelta(month=1)
    transactions = Transaction.objects.filter(account__user__username=user.username, created_at__gte=one_mth)
    html_string = "<h2>Transactions</h2><table><tr><th>Date&nbsp&nbsp&nbsp&nbsp</th><th>Time&nbsp&nbsp&nbsp&nbsp</th><th>Type&nbsp&nbsp&nbsp&nbsp</th><th>Amount&nbsp&nbsp&nbsp&nbsp</th><th>Balance</th></tr>"
    for tx in transactions:
        html_string += f"""
                        <tr>
                            <td>{tx.created_at.date()}&nbsp&nbsp&nbsp&nbsp</td>
                            <td>{tx.created_at.strftime("%H:%M")}&nbsp&nbsp&nbsp&nbsp</td>
                            <td> {tx.transaction_type}&nbsp&nbsp&nbsp&nbsp</td>
                            <td>{tx.amount}&nbsp&nbsp&nbsp&nbsp</td>
                            <td>{tx.balance_after}</td>
                        </tr>
                        """
        
    html_string += "</table>"
    pdf_file = HTML(string=html_string).write_pdf()
    filename = f"statement_{user.id}.pdf"
    with open(filename, "wb") as f:
        f.write(pdf_file)
    return filename


@shared_task
def loan_accepted(loan, user):
    user = CustomUser.objects.get(username=user)
    loan = Loan.objects.get(borrower__user__username=user.username, loan_id=loan)
    if loan.is_accepted:
        subject = "Loan Accepted"
        from_email = settings.EMAIL_HOST_USER
        to = [user.email]
        content = f"Your Loan for the amount {loan.loan_amount} is accepted. Please pay your monthly intrest payment of {loan.monthly_payment} for {loan.loan_term_months} months."
        email = EmailMessage(
            subject, 
            content,
            from_email,
            to
        )
        email.content_subtype = "Plain"
        email.send()
    
    elif loan.status == "PENDING":
        subject = "Recieved Loan Interest"
        from_email = settings.EMAIL_HOST_USER
        to = [user.email]
        content = f"Your Loan for the amount {loan.loan_amount} is being processed. Please wait for approval of the loan."
        email = EmailMessage(
            subject, 
            content,
            from_email,
            to
        )
        email.content_subtype = "Plain"
        email.send()
    else:
        subject = "Loan Rejected"
        from_email = settings.EMAIL_HOST_USER
        to = [user.email]
        content = f"Your Loan for the amount {loan.loan_amount} is rejected. Please apply afterwrds for another if known."
        email = EmailMessage(
            subject, 
            content,
            from_email,
            to
        )
        email.content_subtype = "Plain"
        email.send()

@shared_task
def loan_payment_due():
    loans = Loan.objects.filter(status="ACCEPTED")
    payment_due = timezone.now().date() + timedelta(days=28)
    for loan in loans:
        if (loan.next_payment_date - payment_due).days <= 2 :
            content = load_email_template("payment_due.html").format(
                uname = loan.borrower.user.username,
                date = loan.next_payment_date,
                amt = loan.monthly_payment
            )

            subject = "Loan Payment Due"
            from_email = settings.EMAIL_HOST_USER
            to = [loan.borrower.user.email]
            email = EmailMessage(
                subject,
                content,
                from_email,
                to
            )

            email.content_subtype = "html"
            email.send()

@shared_task
def loan_paid():
    today = timezone.now().date()
    loans = Loan.objects.filter(last_payment_date=today, status="PAID")
    from_email = settings.EMAIL_HOST_USER
    subject = "Loan Successfully Paid"
    for loan in loans:
        to = [loan.borrower.user.email]
        content = load_email_template("loan_paid.html").format(
            user = loan.borrower.user.username,
            amt = loan.loan_amount
        )
        email = EmailMessage(
            subject,
            content,
            from_email,
            to
        )
        email.content_subtype = "html"
        email.send()

@shared_task
def loan_payment_interest(loan, int_id):
    loan = Loan.objects.get(loan_id=loan)
    loanint = LoanInterest.objects.get(id=int_id)
    remaining = loan.remaining_amount()
    content = load_email_template("loan_interest.html").format(
        uname=loan.borrower.user.username,
        loanid = loan.loan_id,
        ant = loan.loan_amount,
        amt= loanint.amount,
        remain = remaining,
        due = loan.next_payment_date
    )
    subject = "Loan Interest Recieved"
    to = [loan.borrower.user.email]
    from_email = settings.EMAIL_HOST_USER
    email = EmailMessage(
        subject,
        content,
        from_email,
        to
    )
    email.content_subtype= "html"
    email.send()
    