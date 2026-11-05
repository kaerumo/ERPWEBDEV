const escapeOperationHTML = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);

const operationRequest = (path, options) => ERPApi.request(path, options);
const operationJson = (value) => ({ "Content-Type": "application/json", body: JSON.stringify(value) });
const approvalTypeLabels = {
  equipment_borrowing: "Equipment borrowing",
};

async function loadOperations() {
  const error = document.getElementById("operationsError");
  error.hidden = true;
  if (!ERPApi.enabled) {
    error.textContent = "Backend mode is required for Operations. Configure itpc_api_url first.";
    error.hidden = false;
    return;
  }
  try {
    const [equipment, borrowing, approvals, notifications, suppliers, purchases, expenses, budgets, users] = await Promise.all([
      operationRequest("/api/equipment"), operationRequest("/api/borrowing-requests"),
      operationRequest("/api/approvals"), operationRequest("/api/notifications"),
      operationRequest("/api/suppliers"), operationRequest("/api/purchases"),
      operationRequest("/api/expenses"),
      operationRequest("/api/budgets"),
      operationRequest("/api/users").catch(() => ({ users: [] })),
    ]);
    renderOperations(equipment, borrowing, approvals, notifications, suppliers, purchases, expenses, budgets, users);
  } catch (requestError) {
    error.textContent = requestError.message;
    error.hidden = false;
  }
}

function renderOperations(equipment, borrowing, approvals, notifications, suppliers, purchases, expenses, budgets, users) {
  const requests = borrowing.requests || [];
  const requestsById = new Map(requests.map((item) => [String(item.id), item]));
  const unread = (notifications.notifications || []).filter((item) => !item.read).length;
  document.getElementById("operationsStats").innerHTML = [
    ["Equipment", (equipment.equipment || []).length],
    ["Active requests", requests.filter((item) => !["returned", "rejected"].includes(item.status)).length],
    ["Pending approvals", (approvals.approvals || []).filter((item) => item.status === "pending").length],
    ["Unread alerts", unread],
  ].map(([label, value]) => `<div class="stat-card"><small>${label}</small><div class="stat-value">${value}</div></div>`).join("");
  document.getElementById("borrowEquipment").innerHTML = `<option value="">Select equipment</option>` +
    (equipment.equipment || []).filter((item) => item.status === "available")
      .map((item) => `<option value="${item.id}">${escapeOperationHTML(item.name)} (${escapeOperationHTML(item.assetTag)})</option>`).join("");
  document.getElementById("purchaseSupplier").innerHTML = `<option value="">Select supplier</option>` +
    (suppliers.suppliers || []).map((item) => `<option value="${item.id}">${escapeOperationHTML(item.name)}</option>`).join("");
  document.getElementById("borrowingList").innerHTML = renderList(requests, (item) =>
    `<strong>${escapeOperationHTML(item.equipment)}</strong><span>${escapeOperationHTML(operationStatusLabel(item.status))} · return by ${escapeOperationHTML(item.dueDate)}</span>${item.overdue ? "<em>Overdue — return required</em>" : ""}${item.status === "approved" ? `<button class="btn btn-secondary operation-action" data-return-id="${item.id}">Record return</button>` : ""}`);
  document.getElementById("approvalList").innerHTML = renderList(approvals.approvals || [], (item) =>
    renderApproval(item, requestsById.get(String(item.referenceId))));
  document.getElementById("notificationList").innerHTML = renderList(notifications.notifications || [], (item) =>
    `<strong>${escapeOperationHTML(item.title)}</strong><span>${escapeOperationHTML(item.message)}</span>${!item.read ? `<button class="btn btn-secondary operation-action" data-notification-id="${item.id}">Mark read</button>` : ""}`);
  document.getElementById("supplierList").innerHTML = renderList(suppliers.suppliers || [], (item) =>
    `<strong>${escapeOperationHTML(item.name)}</strong><span>${escapeOperationHTML(item.email || item.phone)}</span>`);
  document.getElementById("purchaseList").innerHTML = renderList(purchases.purchases || [], (item) =>
    `<strong>${escapeOperationHTML(item.description)}</strong><span>${Number(item.amount).toFixed(2)} · ${escapeOperationHTML(item.purchaseDate)}</span>`);
  document.getElementById("expenseList").innerHTML = renderList(expenses.expenses || [], (item) =>
    `<strong>${escapeOperationHTML(item.description)}</strong><span>${Number(item.amount).toFixed(2)} · ${escapeOperationHTML(item.status)}</span>`);
  document.getElementById("budgetList").innerHTML = renderList(budgets.budgets || [], (item) =>
    `<strong>${escapeOperationHTML(item.name)}</strong><span>${Number(item.amount).toFixed(2)} · ${escapeOperationHTML(item.status)}</span>`);
  document.getElementById("userList").innerHTML = renderList(users.users || [], (item) =>
    `<strong>${escapeOperationHTML(item.displayName)}</strong><span>${escapeOperationHTML(item.username)} · ${escapeOperationHTML(item.role)} · ${escapeOperationHTML(item.status)}</span>`);
}

function renderList(items, template) {
  return items.length ? items.map((item) => `<div class="operation-row">${template(item)}</div>`).join("") : '<p class="empty-state">No records yet.</p>';
}

function operationStatusLabel(status) {
  return {
    pending: "Pending",
    approved: "Approved",
    rejected: "Rejected",
    returned: "Returned",
  }[status] || status;
}

function operationDateLabel(value) {
  if (!value) return "Not provided";
  return new Date(`${value}T00:00:00`).toLocaleDateString([], {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function renderApproval(approval, request) {
  const title = approvalTypeLabels[approval.type] || approval.type;
  const details = request
    ? `<div class="approval-details">
        <div><small>Equipment</small><strong>${escapeOperationHTML(request.equipment)}</strong></div>
        <div><small>Purpose</small><span>${escapeOperationHTML(request.purpose)}</span></div>
        <div><small>Borrowing date</small><span>${escapeOperationHTML(operationDateLabel(request.requestedFrom))}</span></div>
        <div><small>Return date</small><span>${escapeOperationHTML(operationDateLabel(request.dueDate))}</span></div>
        <div><small>Requested by</small><span>User #${escapeOperationHTML(request.borrowerId)}</span></div>
      </div>`
    : `<span>Request details are unavailable.</span>`;
  const actions = approval.status === "pending"
    ? `<span><button class="btn btn-secondary operation-action" data-approval-id="${approval.id}" data-approval-status="approved">Approve</button> <button class="btn btn-secondary operation-action" data-approval-id="${approval.id}" data-approval-status="rejected">Reject</button></span>`
    : "";
  return `<strong>${escapeOperationHTML(title)}</strong><span>${escapeOperationHTML(operationStatusLabel(approval.status))} · request #${approval.referenceId}</span>${details}${actions}`;
}

async function submitOperation(form, path, payload) {
  try { await operationRequest(path, { method: "POST", ...operationJson(payload) }); form.reset(); await loadOperations(); }
  catch (error) { const target = document.getElementById("operationsError"); target.textContent = error.message; target.hidden = false; }
}

document.getElementById("borrowForm").addEventListener("submit", (event) => {
  event.preventDefault();
  const from = document.getElementById("borrowFrom").value;
  const due = document.getElementById("borrowDue").value;
  if (from && due && due < from) {
    const target = document.getElementById("operationsError");
    target.textContent = "The due date must be on or after the requested start date.";
    target.hidden = false;
    document.getElementById("borrowDue").focus();
    return;
  }
  submitOperation(event.currentTarget, "/api/borrowing-requests", {
    equipmentId: Number(document.getElementById("borrowEquipment").value),
    purpose: document.getElementById("borrowPurpose").value,
    requestedFrom: document.getElementById("borrowFrom").value,
    dueDate: document.getElementById("borrowDue").value,
  });
});
document.getElementById("borrowFrom").addEventListener("change", (event) => {
  const due = document.getElementById("borrowDue");
  due.min = event.target.value;
  if (due.value && due.value < event.target.value) due.value = event.target.value;
});
document.getElementById("supplierForm").addEventListener("submit", (event) => {
  event.preventDefault();
  submitOperation(event.currentTarget, "/api/suppliers", {
    name: document.getElementById("supplierName").value,
    email: document.getElementById("supplierEmail").value,
    phone: document.getElementById("supplierPhone").value,
  });
});
document.getElementById("purchaseForm").addEventListener("submit", (event) => {
  event.preventDefault();
  submitOperation(event.currentTarget, "/api/purchases", {
    supplierId: Number(document.getElementById("purchaseSupplier").value),
    description: document.getElementById("purchaseDescription").value,
    amount: document.getElementById("purchaseAmount").value,
    purchaseDate: document.getElementById("purchaseDate").value,
  });
});
document.getElementById("expenseForm").addEventListener("submit", (event) => {
  event.preventDefault();
  submitOperation(event.currentTarget, "/api/expenses", {
    category: document.getElementById("expenseCategory").value,
    description: document.getElementById("expenseDescription").value,
    amount: document.getElementById("expenseAmount").value,
    expenseDate: document.getElementById("expenseDate").value,
  });
});
document.getElementById("budgetForm").addEventListener("submit", (event) => {
  event.preventDefault();
  submitOperation(event.currentTarget, "/api/budgets", {
    name: document.getElementById("budgetName").value,
    category: document.getElementById("budgetCategory").value,
    amount: document.getElementById("budgetAmount").value,
    periodStart: document.getElementById("budgetStart").value,
    periodEnd: document.getElementById("budgetEnd").value,
  });
});
document.getElementById("userForm").addEventListener("submit", (event) => {
  event.preventDefault();
  submitOperation(event.currentTarget, "/api/users", {
    username: document.getElementById("userUsername").value,
    displayName: document.getElementById("userDisplayName").value,
    password: document.getElementById("userPassword").value,
    role: document.getElementById("userRole").value,
  });
});
document.getElementById("refreshOperations").addEventListener("click", loadOperations);
document.addEventListener("click", async (event) => {
  const action = event.target.closest(".operation-action");
  if (!action) return;
  try {
    if (action.dataset.approvalId) {
      await operationRequest(`/api/approvals/${action.dataset.approvalId}`, { method: "PATCH", ...operationJson({ status: action.dataset.approvalStatus }) });
    } else if (action.dataset.returnId) {
      await operationRequest(`/api/borrowing-requests/${action.dataset.returnId}/return`, { method: "POST", ...operationJson({ condition: "good" }) });
    } else if (action.dataset.notificationId) {
      await operationRequest(`/api/notifications/${action.dataset.notificationId}/read`, { method: "PATCH" });
    }
    await loadOperations();
  } catch (error) {
    const target = document.getElementById("operationsError");
    target.textContent = error.message;
    target.hidden = false;
  }
});
loadOperations();
