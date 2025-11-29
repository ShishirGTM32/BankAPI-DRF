// ===== CONFIG =====
const API_URL = 'http://localhost:8000/api';

let authToken = null;
let currentAccount = null;
let currentTransactionType = null;
let allTransactions = [];
let currentFilterDays = 7;
let currentFilterType = '';

window.onload = function () {
    const storedToken = localStorage.getItem("authToken");
    if (storedToken) {
        authToken = storedToken;
        document.getElementById('mainNav').style.display = 'flex';
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
            localStorage.setItem("authToken", authToken);
            document.getElementById('mainNav').style.display = 'flex';
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
            localStorage.setItem("authToken", authToken);
            document.getElementById('mainNav').style.display = 'flex';
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
    } catch (err) {}
    localStorage.removeItem("authToken");
    authToken = null;
    currentAccount = null;
    document.getElementById('mainNav').style.display = 'none';
    showPage('login');
}

// --- Dashboard ---
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
                // Use recipient_account_number if backend returns object
                if (t.recipient_account && typeof t.recipient_account === 'object') {
                    t.recipient_account_number = t.recipient_account.account_number || '';
                }
                return t;
            });
            renderTransactions();
        } else {
            document.getElementById("dashboardTransactionsList").innerHTML = "<p>No transactions</p>";
        }
    } catch (err) {
        console.error(err);
        document.getElementById("dashboardTransactionsList").innerHTML = "<p>Error loading transactions</p>";
    }
}

function renderTransactions() {
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
                ${t.transaction_type === 'DEPOSIT' ? '+' : '-'}${parseFloat(t.amount).toFixed(2)}
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
        currency: document.getElementById('accountCurrency').value
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
