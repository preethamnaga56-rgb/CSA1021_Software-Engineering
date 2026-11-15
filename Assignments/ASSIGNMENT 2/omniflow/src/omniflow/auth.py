"""Server-side identity and role permissions. Role comes from the session, never from the request."""
from dataclasses import dataclass
from .errors import Unauthenticated, Forbidden

PERMISSIONS = {
    "customer":        {"order.place", "order.view_own", "order.cancel_own", "refund.request"},
    "picker":          {"order.pick", "order.dispatch", "picklist.view", "scan.ingest"},
    "support_agent":   {"order.view_masked", "refund.request"},
    "finance_reviewer": {"refund.approve", "refund.reject", "order.view_finance", "refund.view"},
    "store_manager":   {"refund.approve", "refund.reject", "report.view", "stock.correct", "refund.view"},
    "administrator":   {"policy.configure", "report.view"},
}

@dataclass(frozen=True)
class User:
    id: str
    role: str
    region: str
    email: str

def authenticate(conn, token):
    row = conn.execute(
        "SELECT u.id,u.role,u.region,u.email FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=?",
        (token,)).fetchone()
    if row is None:
        raise Unauthenticated("invalid or missing session")
    return User(row["id"], row["role"], row["region"], row["email"])

def require(user, permission):
    if permission not in PERMISSIONS.get(user.role, set()):
        raise Forbidden(f"role {user.role} lacks {permission}")

def mask_email(email):
    if not email or "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    return f"{local[0]}***@{domain[0]}***"
