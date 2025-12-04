// ===== CONFIG =====
const API_URL = 'http://localhost:8000/api';

let authToken = null;
let currentAccount = null;
let currentTransactionType = null;
let allTransactions = [];
let currentFilterDays = 7;
let currentFilterType = '';
let isAdmin = false;
let adminTransactionAccountId = null;
let adminTransactionType = null;


window.onload = function () {
    const storedToken = localStorage.getItem("authToken");
    const storedIsAdmin = localStorage.getItem("isAdmin") === 'true';

    if (storedToken) {
        authToken = storedToken;
        isAdmin = storedIsAdmin;
        document.getElementById('mainNav').style.display = 'flex';

        if (isAdmin) {
            document.getElementById('adminNavBtn').style.display = 'block';
        }

        showPage('dashboard');
    } else {
        showPage('login');
    }
};

// --- Utility ---
function showMessage(elementId, message, type) {
    const el = document.getElementById(elementId);
    el.innerHTML = `<div class="message ${type}">${message}</div>`;
    setTimeout(() => el.innerHTML = '', 5000);
}

function showPage(pageName) {
    document.querySelectorAll('.page').forEach(page => page.classList.remove('active'));
    document.getElementById(pageName + 'Page').classList.add('active');

    if (pageName === 'dashboard') loadDashboard();
    if (pageName === 'profile') loadProfile();
    if (pageName === 'loans') loadUserLoans();
    if (pageName === 'admin') loadAdminDashboard();
}


// --- Authentication ---
async function handleRegister(e) {
    e.preventDefault();
    const data = {
        username: document.getElementById('regUsername').value,
        email: document.getElementById('regEmail').value,
        password: document.getElementById('regPassword').value,
        password_confirm: document.getElementById('regPasswordConfirm').value,
        first_name: document.getElementById('regFirstName').value,
        last_name: document.getElementById('regLastName').value,
        phone: document.getElementById('regPhone').value,
        address: document.getElementById('regAddress').value,
        date_of_birth: document.getElementById('regDob').value || null
    };

    try {
        const res = await fetch(`${API_URL}/auth/register/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await res.json();
        if (res.ok) {
            authToken = result.token;
            isAdmin = result.is_admin || false;
            localStorage.setItem("authToken", authToken);
            localStorage.setItem("isAdmin", isAdmin);
            document.getElementById('mainNav').style.display = 'flex';

            if (isAdmin) {
                document.getElementById('adminNavBtn').style.display = 'block';
            }

            showMessage('registerMessage', 'Registration successful!', 'success');
            setTimeout(() => showPage('createAccount'), 1000);
        } else {
            const errorMsg = typeof result === 'object' ? Object.values(result).flat().join(', ') : 'Registration failed';
            showMessage('registerMessage', errorMsg, 'error');
        }
    } catch (err) {
        showMessage('registerMessage', 'Registration failed', 'error');
    }
}

async function handleLogin(e) {
    e.preventDefault();
    const data = {
        username: document.getElementById('loginUsername').value,
        password: document.getElementById('loginPassword').value
    };
    try {
        const res = await fetch(`${API_URL}/auth/login/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await res.json();
        if (res.ok) {
            authToken = result.token;
            isAdmin = result.is_admin || false;
            localStorage.setItem("authToken", authToken);
            localStorage.setItem("isAdmin", isAdmin);
            document.getElementById('mainNav').style.display = 'flex';

            if (isAdmin) {
                document.getElementById('adminNavBtn').style.display = 'block';
            }

            showPage('dashboard');
        } else {
            showMessage('loginMessage', 'Invalid credentials', 'error');
        }
    } catch (err) {
        showMessage('loginMessage', 'Login failed', 'error');
    }
}

async function logout() {
    try {
        await fetch(`${API_URL}/auth/logout/`, {
            method: 'POST',
            headers: { 'Authorization': `Token ${authToken}` }
        });
    } catch (err) { }
    localStorage.removeItem("authToken");
    localStorage.removeItem("isAdmin");
    authToken = null;
    currentAccount = null;
    isAdmin = false;
    document.getElementById('mainNav').style.display = 'none';
    document.getElementById('adminNavBtn').style.display = 'none';
    showPage('login');
}

async function loadDashboard() {
    if (!authToken) return;
    try {
        const res = await fetch(`${API_URL}/accounts/`, { headers: { 'Authorization': `Token ${authToken}` } });
        const accounts = await res.json();
        if (!Array.isArray(accounts) || accounts.length === 0) {
            document.getElementById('noAccountView').style.display = 'block';
            document.getElementById('accountView').style.display = 'none';
        } else {
            currentAccount = accounts[0];
            document.getElementById('noAccountView').style.display = 'none';
            document.getElementById('accountView').style.display = 'block';
            displayAccountDetails(currentAccount);
            await loadTransactions(currentAccount.id);
        }
    } catch (err) {
        console.error(err);
    }
}

function displayAccountDetails(account) {
    const card = document.getElementById('accountDetailsCard');
    card.innerHTML = `
        <div class="info-row">
            <span class="info-label">Account Number</span>
            <span class="info-value selectable">${account.account_number}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Account Type</span>
            <span class="info-value">${account.account_type}</span>
        </div>
        <div class="info-row balance-row">
            <span class="info-label">Current Balance</span>
            <span class="info-value balance">${account.currency} ${parseFloat(account.balance).toFixed(2)}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Currency</span>
            <span class="info-value">${account.currency}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Status</span>
            <span class="info-value status-active">Active</span>
        </div>
    `;
}

// --- Transactions ---
async function loadTransactions(accountId) {
    if (!authToken) return;
    try {
        const res = await fetch(`${API_URL}/accounts/${accountId}/transactions/`, {
            headers: { 'Authorization': `Token ${authToken}` }
        });
        const data = await res.json();
        if (res.ok) {
            allTransactions = data.map(t => {
                if (t.recipient_account && typeof t.recipient_account === 'object') {
                    t.recipient_account_number = t.recipient_account.account_number || '';
                }
                return t;
            });
            renderTransactions(accountId);
        } else {
            document.getElementById("dashboardTransactionsList").innerHTML = "<p>No transactions</p>";
        }
    } catch (err) {
        console.error(err);
        document.getElementById("dashboardTransactionsList").innerHTML = "<p>Error loading transactions</p>";
    }
}

function renderTransactions(accountId) {
    let filtered = allTransactions;

    if (currentFilterDays > 0) {
        const cutoff = new Date();
        cutoff.setDate(cutoff.getDate() - currentFilterDays);
        filtered = filtered.filter(t => new Date(t.created_at) >= cutoff);
    }

    if (currentFilterType) filtered = filtered.filter(t => t.transaction_type === currentFilterType);

    const container = document.getElementById("dashboardTransactionsList");
    if (!filtered.length) return container.innerHTML = "<div class='empty-message'>No transactions</div>";

    container.innerHTML = filtered.map(t => {
        let recipientInfo = '';
        if (t.transaction_type === 'TRANSFER' && t.recipient_account_number) {
            recipientInfo = `<div class="transaction-desc">To: ${t.recipient_account_number}</div>`;
        }
        return `
        <div class="transaction-item">
            <div class="transaction-info">
                <div class="transaction-type">${t.transaction_type}</div>
                <div class="transaction-desc">${t.description || 'No description'}</div>
                ${recipientInfo}
                <div class="transaction-desc">${new Date(t.created_at).toLocaleString()}</div>
            </div>
            <div class="transaction-amount ${t.transaction_type.toLowerCase()}">
                ${t.transaction_type === 'DEPOSIT' ? '+' : t.transaction_type === 'TRANSFER' ? (t.recipient_account === accountId ? '+' : '-') : '-'}${parseFloat(t.amount).toFixed(2)}
            </div>
        </div>
        `;
    }).join('');
}

// --- Filters ---
function filterTransactions(days) {
    currentFilterDays = days;
    document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
    renderTransactions();
}

function filterByTypeDropdown() {
    const dropdown = document.getElementById('transactionTypeFilter');
    currentFilterType = dropdown.value;
    renderTransactions();
}

// --- Transaction Form ---
function showTransactionForm(type) {
    currentTransactionType = type;
    const formArea = document.getElementById('transactionFormArea');
    const title = document.getElementById('transactionFormTitle');
    const fields = document.getElementById('transactionFormFields');

    title.textContent = type.charAt(0).toUpperCase() + type.slice(1);

    let fieldsHTML = '';
    if (type === 'transfer') {
        fieldsHTML += `
            <div class="form-group">
                <label>Recipient Account Number</label>
                <input type="text" id="recipientAccountNumber" placeholder="Enter account number" required>
            </div>
        `;
    }

    fieldsHTML += `
        <div class="form-group">
            <label>Amount</label>
            <input type="number" id="transactionAmount" step="0.01" placeholder="0.00" required>
        </div>
        <div class="form-group">
            <label>Description (Optional)</label>
            <textarea id="transactionDescription" rows="3" placeholder="Add a note..."></textarea>
        </div>
    `;
    fields.innerHTML = fieldsHTML;
    formArea.style.display = 'block';
    document.getElementById('transactionMessage').innerHTML = '';
}

function hideTransactionForm() {
    document.getElementById('transactionFormArea').style.display = 'none';
    document.getElementById('transactionForm').reset();
    currentTransactionType = null;
}

async function handleTransaction(e) {
    e.preventDefault();
    if (!currentTransactionType) return;

    const amount = document.getElementById('transactionAmount').value;
    const description = document.getElementById('transactionDescription').value;
    const payload = { amount, description };

    if (currentTransactionType === 'transfer') {
        payload.recipient_account_number = document.getElementById('recipientAccountNumber').value;
    }

    let endpoint = '';
    if (currentTransactionType === 'deposit') endpoint = 'deposit';
    else if (currentTransactionType === 'withdraw') endpoint = 'withdraw';
    else if (currentTransactionType === 'transfer') endpoint = 'transfer';
    else return;

    try {
        const res = await fetch(`${API_URL}/accounts/${currentAccount.id}/${endpoint}/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Token ${authToken}` },
            body: JSON.stringify(payload)
        });
        const result = await res.json();
        if (res.ok) {
            hideTransactionForm();
            await loadDashboard();
            showMessage('transactionMessage', 'Transaction successful', 'success');
        } else {
            const errorMsg = typeof result === 'object' ? Object.values(result).flat().join(', ') : 'Transaction failed';
            showMessage('transactionMessage', errorMsg, 'error');
        }
    } catch (err) {
        console.error(err);
        showMessage('transactionMessage', 'Transaction failed', 'error');
    }
}

// --- Account Creation ---
async function handleCreateAccount(e) {
    e.preventDefault();
    const data = {
        account_type: document.getElementById('accountType').value,
        currency: document.getElementById('accountCurrency').value,
        balance: document.getElementById('accountBalance').value
    };
    try {
        const res = await fetch(`${API_URL}/accounts/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Token ${authToken}` },
            body: JSON.stringify(data)
        });
        const result = await res.json();
        if (res.ok) {
            showMessage('createAccountMessage', 'Account created successfully!', 'success');
            await loadDashboard();
        } else {
            const errorMsg = typeof result === 'object' ? Object.values(result).flat().join(', ') : 'Failed to create account';
            showMessage('createAccountMessage', errorMsg, 'error');
        }
    } catch (err) {
        showMessage('createAccountMessage', 'Failed to create account', 'error');
    }
}

// --- Profile ---
async function loadProfile() {
    try {
        const res = await fetch(`${API_URL}/auth/profile/`, { headers: { 'Authorization': `Token ${authToken}` } });
        const profile = await res.json();
        const content = document.getElementById('profileContent');
        const accountInfo = document.getElementById('profileAccountInfo');
        content.innerHTML = `
            <div class="profile-row"><span class="profile-label">Username</span><span class="profile-value">${profile.username}</span></div>
            <div class="profile-row"><span class="profile-label">Email</span><span class="profile-value">${profile.email}</span></div>
            <div class="profile-row"><span class="profile-label">First Name</span><span class="profile-value">${profile.first_name || '-'}</span></div>
            <div class="profile-row"><span class="profile-label">Last Name</span><span class="profile-value">${profile.last_name || '-'}</span></div>
            <div class="profile-row"><span class="profile-label">Phone</span><span class="profile-value">${profile.phone || '-'}</span></div>
            <div class="profile-row"><span class="profile-label">Address</span><span class="profile-value">${profile.address || '-'}</span></div>
            <div class="profile-row"><span class="profile-label">DOB</span><span class="profile-value">${profile.date_of_birth || '-'}</span></div>
        `;
        if (currentAccount) {
            accountInfo.innerHTML = `
                <div class="profile-row"><span class="profile-label">Account Number</span><span class="profile-value">${currentAccount.account_number}</span></div>
                <div class="profile-row"><span class="profile-label">Account Type</span><span class="profile-value">${currentAccount.account_type}</span></div>
                <div class="profile-row"><span class="profile-label">Balance</span><span class="profile-value">${currentAccount.currency} ${parseFloat(currentAccount.balance).toFixed(2)}</span></div>
            `;
        }
    } catch (err) {
        console.error(err);
    }
}


function showLoanApplicationForm() {
    document.getElementById('loanApplicationForm').style.display = 'block';
}

function hideLoanApplicationForm() {
    document.getElementById('loanApplicationForm').style.display = 'none';
    document.getElementById('loanApplicationMessage').innerHTML = '';
}

async function handleLoanApplication(e) {
    e.preventDefault();

    if (!currentAccount) {
        showMessage('loanApplicationMessage', 'No account found. Please create an account first.', 'error');
        return;
    }

    // Parse values to ensure correct types
    const loanAmount = parseFloat(document.getElementById('loanAmount').value);
    const interestRate = parseFloat(document.getElementById('loanInterestRate').value);
    const loanTermMonths = parseInt(document.getElementById('loanTerm').value);
    const purpose = document.getElementById('loanPurpose').value.trim();

    // Validate ranges
    if (loanAmount < 10000 || loanAmount > 5000000) {
        showMessage('loanApplicationMessage', 'Loan amount must be between NPR 10,000 and NPR 50,00,000', 'error');
        return;
    }

    if (interestRate < 5 || interestRate > 25) {
        showMessage('loanApplicationMessage', 'Interest rate must be between 5% and 25%', 'error');
        return;
    }

    if (loanTermMonths < 6 || loanTermMonths > 120) {
        showMessage('loanApplicationMessage', 'Loan term must be between 6 and 120 months', 'error');
        return;
    }

    const data = {
        loan_amount: loanAmount.toString(),
        interest_rate: interestRate.toString(),
        loan_term_months: loanTermMonths,
        purpose: purpose || ''
    };

    console.log('Submitting loan application:', data);

    try {
        const res = await fetch(`${API_URL}/accounts/${currentAccount.id}/loan/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Token ${authToken}`
            },
            body: JSON.stringify(data)
        });

        const result = await res.json();
        console.log('Loan application response:', result);

        if (res.ok) {
            showMessage('loanApplicationMessage', 'Loan application submitted successfully!', 'success');
            document.getElementById('loanAmount').value = '';
            document.getElementById('loanInterestRate').value = '12';
            document.getElementById('loanTerm').value = '';
            document.getElementById('loanPurpose').value = '';
            setTimeout(() => {
                hideLoanApplicationForm();
                loadUserLoans();
            }, 1500);
        } else {
            console.error('Loan application error:', result);
            const errorMsg = typeof result === 'object' ? Object.values(result).flat().join(', ') : 'Application failed';
            showMessage('loanApplicationMessage', errorMsg, 'error');
        }
    } catch (err) {
        console.error('Loan application exception:', err);
        showMessage('loanApplicationMessage', 'Failed to submit application', 'error');
    }
}


async function loadUserLoans() {
    if (!authToken) return;

    try {
        const res = await fetch(`${API_URL}/loans/`, {
            headers: { 'Authorization': `Token ${authToken}` }
        });

        const loans = await res.json();
        const container = document.getElementById('loansList');

        if (!loans || loans.length === 0) {
            container.innerHTML = '<div class="empty-message">No loans found. Apply for your first loan!</div>';
            return;
        }

        container.innerHTML = loans.map(loan => {
            const statusClass = loan.status.toLowerCase();

            return `
                <div class="account-details-section" style="margin-bottom: 20px;">
                    <div class="info-row">
                        <span class="info-label">Loan ID</span>
                        <span class="info-value">#${loan.loan_id}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Loan Amount</span>
                        <span class="info-value">NPR ${parseFloat(loan.loan_amount).toFixed(2)}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Interest Rate</span>
                        <span class="info-value">${loan.interest_rate}% per annum</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Term</span>
                        <span class="info-value">${loan.loan_term_months} months</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Monthly Payment</span>
                        <span class="info-value">NPR ${parseFloat(loan.monthly_payment).toFixed(2)}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Total Payable</span>
                        <span class="info-value">NPR ${parseFloat(loan.total_payable).toFixed(2)}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Total Paid</span>
                        <span class="info-value">NPR ${parseFloat(loan.total_paid).toFixed(2)}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Remaining Amount</span>
                        <span class="info-value">NPR ${parseFloat(loan.remaining_amount).toFixed(2)}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Status</span>
                        <span class="info-value status-${statusClass}">${loan.status}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Applied Date</span>
                        <span class="info-value">${new Date(loan.applied_date).toLocaleDateString()}</span>
                    </div>
                    ${loan.purpose ? `
                        <div class="info-row">
                            <span class="info-label">Purpose</span>
                            <span class="info-value">${loan.purpose}</span>
                        </div>
                    ` : ''}
                    ${loan.is_accepted && loan.status !== 'PAID' ? `
                        <div class="info-row">
                            <span class="info-label">Next Payment Date</span>
                            <span class="info-value">${loan.next_payment_date || 'Not set'}</span>
                        </div>
                        <button class="btn btn-small" onclick="showLoanPaymentForm(${loan.loan_id}, ${loan.remaining_amount})">Make Payment</button>
                    ` : ''}
                    ${loan.status === 'PENDING' ? '<p style="color: #888; margin-top: 10px;">Waiting for admin approval...</p>' : ''}
                    ${loan.status === 'REJECTED' ? '<p style="color: #c55; margin-top: 10px;">This loan application was rejected.</p>' : ''}
                    ${loan.status === 'PAID' ? '<p style="color: #4a4; margin-top: 10px;">This loan has been fully paid!</p>' : ''}
                </div>
            `;
        }).join('');
    } catch (err) {
        console.error(err);
        document.getElementById('loansList').innerHTML = '<div class="empty-message">Error loading loans</div>';
    }
}
function showLoanPaymentForm(loanId, remainingAmount) {
    const amount = prompt(`Enter payment amount (NPR):\nRemaining balance: NPR ${parseFloat(remainingAmount).toFixed(2)}`);
    if (amount && parseFloat(amount) > 0) {
        makeLoanPayment(loanId, amount);
    }
}

async function makeLoanPayment(loanId, amount) {
    if (!currentAccount) return;

    try {
        const res = await fetch(`${API_URL}/accounts/${currentAccount.id}/loan/${loanId}/payment/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Token ${authToken}`
            },
            body: JSON.stringify({
                amount: amount,
                payment_method: 'Online Transfer'
            })
        });

        const result = await res.json();

        if (res.ok) {
            alert('Payment successful!');
            loadUserLoans();
        } else {
            const errorMsg = typeof result === 'object' ? Object.values(result).flat().join(', ') : 'Payment failed';
            alert(errorMsg);
        }
    } catch (err) {
        alert('Payment failed');
    }
}

document.getElementById("downloadTransactionsBtn").addEventListener("click", async () => {
    try {
        const res = await fetch(`${API_URL}/download-pdf/`, {
            headers: { 'Authorization': `Token ${authToken}` }
        });
        const { task_id } = await res.json();
        let status;
        do {
            const check = await fetch(`${API_URL}/check-pdf-status/${task_id}/`, {
                headers: { 'Authorization': `Token ${authToken}` }
            });

            if (check.headers.get("Content-Type") === "application/pdf") {
                window.location.href = `${API_URL}/check-pdf-status/${task_id}/`;
                break;
            }

            const data = await check.json();
            status = data.status;
            await new Promise(r => setTimeout(r, 3000));
        } while (status === "pending");
    } catch (err) {
        console.error("Download failed", err);
    }
});


async function loadAdminDashboard() {
    if (!isAdmin) {
        showPage('dashboard');
        return;
    }

    // Show dashboard, hide sections
    document.getElementById('adminDashboard').style.display = 'block';
    document.getElementById('adminUsersSection').style.display = 'none';
    document.getElementById('adminAccountsSection').style.display = 'none';
    document.getElementById('adminLoansSection').style.display = 'none';
    document.getElementById('adminTransactionForm').style.display = 'none';

    try {
        const res = await fetch(`${API_URL}/admin/dashboard/`, {
            headers: { 'Authorization': `Token ${authToken}` }
        });

        const stats = await res.json();

        document.getElementById('adminStats').innerHTML = `
            <div class="info-row">
                <span class="info-label">Total Users</span>
                <span class="info-value">${stats.total_users}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Total Accounts</span>
                <span class="info-value">${stats.total_accounts}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Active Accounts</span>
                <span class="info-value">${stats.active_accounts}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Pending Loans</span>
                <span class="info-value">${stats.pending_loans}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Approved Loans</span>
                <span class="info-value">${stats.approved_loans}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Total Transactions</span>
                <span class="info-value">${stats.total_transactions}</span>
            </div>
        `;
    } catch (err) {
        console.error(err);
    }
}

function backToAdminDashboard() {
    loadAdminDashboard();
}

async function showAdminSection(section) {
    document.getElementById('adminDashboard').style.display = 'none';

    if (section === 'users') {
        document.getElementById('adminUsersSection').style.display = 'block';
        loadAdminUsers();
    } else if (section === 'accounts') {
        document.getElementById('adminAccountsSection').style.display = 'block';
        loadAdminAccounts();
    } else if (section === 'loans') {
        document.getElementById('adminLoansSection').style.display = 'block';
        loadAdminLoans('all');
    }
}

async function loadAdminUsers() {
    try {
        const res = await fetch(`${API_URL}/admin/users/`, {
            headers: { 'Authorization': `Token ${authToken}` }
        });

        const users = await res.json();
        const container = document.getElementById('adminUsersList');

        container.innerHTML = users.map(user => `
            <div class="account-details-section" style="margin-bottom: 15px;">
                <div class="info-row">
                    <span class="info-label">ID</span>
                    <span class="info-value">${user.id}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Username</span>
                    <span class="info-value">${user.username}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Email</span>
                    <span class="info-value">${user.email}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Name</span>
                    <span class="info-value">${user.first_name} ${user.last_name}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Admin</span>
                    <span class="info-value">${user.is_staff ? 'Yes' : 'No'}</span>
                </div>
            </div>
        `).join('');
    } catch (err) {
        console.error(err);
    }
}

async function loadAdminAccounts() {
    try {
        const res = await fetch(`${API_URL}/admin/accounts/`, {
            headers: { 'Authorization': `Token ${authToken}` }
        });

        const accounts = await res.json();
        const container = document.getElementById('adminAccountsList');

        container.innerHTML = accounts.map(account => `
            <div class="account-details-section" style="margin-bottom: 15px;">
                <div class="info-row">
                    <span class="info-label">Account Number</span>
                    <span class="info-value">${account.account_number}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Owner</span>
                    <span class="info-value">${account.user ? account.user.username : 'N/A'}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Type</span>
                    <span class="info-value">${account.account_type}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Balance</span>
                    <span class="info-value">${account.currency} ${parseFloat(account.balance).toFixed(2)}</span>
                </div>
                <div style="display: flex; gap: 10px; margin-top: 10px;">
                    <button class="btn btn-small btn-success" onclick="showAdminTransactionForm('deposit', ${account.id}, '${account.account_number}')">Deposit</button>
                    <button class="btn btn-small btn-danger" onclick="showAdminTransactionForm('withdraw', ${account.id}, '${account.account_number}')">Withdraw</button>
                </div>
            </div>
        `).join('');
    } catch (err) {
        console.error(err);
    }
}

function showAdminTransactionForm(type, accountId, accountNumber) {
    adminTransactionAccountId = accountId;
    adminTransactionType = type;

    document.getElementById('adminAccountsSection').style.display = 'none';
    document.getElementById('adminTransactionForm').style.display = 'block';
    document.getElementById('adminTransactionTitle').textContent = type === 'deposit' ? 'Deposit Money' : 'Withdraw Money';
    document.getElementById('adminTransactionAccount').value = accountNumber;
    document.getElementById('adminTransactionMessage').innerHTML = '';
}

function hideAdminTransactionForm() {
    document.getElementById('adminTransactionForm').style.display = 'none';
    document.getElementById('adminAccountsSection').style.display = 'block';
    document.getElementById('adminTransactionAmount').value = '';
    document.getElementById('adminTransactionDescription').value = '';
}

async function handleAdminTransaction(e) {
    e.preventDefault();

    const amount = document.getElementById('adminTransactionAmount').value;
    const description = document.getElementById('adminTransactionDescription').value;

    const endpoint = adminTransactionType === 'deposit' ? 'deposit' : 'withdraw';

    try {
        const res = await fetch(`${API_URL}/accounts/${adminTransactionAccountId}/${endpoint}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Token ${authToken}`
            },
            body: JSON.stringify({ amount, description })
        });

        const result = await res.json();

        if (res.ok) {
            showMessage('adminTransactionMessage', 'Transaction successful!', 'success');
            setTimeout(() => {
                hideAdminTransactionForm();
                loadAdminAccounts();
            }, 1500);
        } else {
            const errorMsg = typeof result === 'object' ? Object.values(result).flat().join(', ') : 'Transaction failed';
            showMessage('adminTransactionMessage', errorMsg, 'error');
        }
    } catch (err) {
        showMessage('adminTransactionMessage', 'Transaction failed', 'error');
    }
}

async function loadAdminLoans(statusFilter) {
    try {
        let url = `${API_URL}/admin/loans/`;
        if (statusFilter && statusFilter !== 'all') {
            url += `?status=${statusFilter}`;
        }

        const res = await fetch(url, {
            headers: { 'Authorization': `Token ${authToken}` }
        });

        const loans = await res.json();
        const container = document.getElementById('adminLoansList');

        if (!loans || loans.length === 0) {
            container.innerHTML = '<div class="empty-message">No loans found</div>';
            return;
        }

        container.innerHTML = loans.map(loan => `
            <div class="account-details-section" style="margin-bottom: 20px;">
                <div class="info-row">
                    <span class="info-label">Loan ID</span>
                    <span class="info-value">#${loan.loan_id}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Borrower</span>
                    <span class="info-value">${loan.borrower_name || 'N/A'}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Account ID</span>
                    <span class="info-value">${loan.borrower}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Loan Amount</span>
                    <span class="info-value">NPR ${parseFloat(loan.loan_amount).toFixed(2)}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Interest Rate</span>
                    <span class="info-value">${loan.interest_rate}% per annum</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Term</span>
                    <span class="info-value">${loan.loan_term_months} months</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Monthly Payment</span>
                    <span class="info-value">NPR ${parseFloat(loan.monthly_payment).toFixed(2)}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Total Payable</span>
                    <span class="info-value">NPR ${parseFloat(loan.total_payable).toFixed(2)}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Total Paid</span>
                    <span class="info-value">NPR ${parseFloat(loan.total_paid).toFixed(2)}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Remaining</span>
                    <span class="info-value">NPR ${parseFloat(loan.remaining_amount).toFixed(2)}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Status</span>
                    <span class="info-value">${loan.status}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Applied Date</span>
                    <span class="info-value">${new Date(loan.applied_date).toLocaleString()}</span>
                </div>
                ${loan.accepted_date ? `
                    <div class="info-row">
                        <span class="info-label">Accepted Date</span>
                        <span class="info-value">${new Date(loan.accepted_date).toLocaleString()}</span>
                    </div>
                ` : ''}
                ${loan.purpose ? `
                    <div class="info-row">
                        <span class="info-label">Purpose</span>
                        <span class="info-value">${loan.purpose}</span>
                    </div>
                ` : ''}
                ${loan.status === 'PENDING' ? `
                    <div style="display: flex; gap: 10px; margin-top: 10px;">
                        <button class="btn btn-small btn-success" onclick="handleLoanAction(${loan.loan_id}, 'accept')">Accept</button>
                        <button class="btn btn-small btn-danger" onclick="handleLoanAction(${loan.loan_id}, 'reject')">Reject</button>
                    </div>
                ` : ''}
            </div>
        `).join('');
    } catch (err) {
        console.error(err);
    }
}


async function handleLoanAction(loanId, action) {
    const confirmMsg = action === 'accept' ?
        'Are you sure you want to approve this loan?' :
        'Are you sure you want to reject this loan?';

    if (!confirm(confirmMsg)) return;

    try {
        const res = await fetch(`${API_URL}/admin/loans/${loanId}/`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Token ${authToken}`
            },
            body: JSON.stringify({ action })
        });

        const result = await res.json();

        if (res.ok) {
            alert(result.message);
            loadAdminLoans('all');
        } else {
            alert('Action failed: ' + (result.error || 'Unknown error'));
        }
    } catch (err) {
        alert('Action failed');
    }
}

function filterAdminLoans(status) {
    // Update active button
    document.querySelectorAll('#adminLoansSection .filter-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');

    loadAdminLoans(status);
}