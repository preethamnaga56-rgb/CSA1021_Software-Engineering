"""Versioned regional policy (tax, shipping, refund limit, return window)."""
from .auth import authenticate, require
from .db import tx, audit
from .errors import NotFound, ValidationError

def current_policy(conn, region):
    row = conn.execute("SELECT * FROM regional_policy WHERE region=? ORDER BY version DESC LIMIT 1", (region,)).fetchone()
    if row is None:
        raise NotFound(f"no policy for region {region}")
    return row

def set_policy(conn, token, region, tax_bps, shipping_cents, refund_limit_cents, return_days, now):
    user = authenticate(conn, token)
    require(user, "policy.configure")
    if min(tax_bps, shipping_cents, refund_limit_cents, return_days) < 0:
        raise ValidationError("policy values must be non-negative")
    with tx(conn):
        row = conn.execute("SELECT COALESCE(MAX(version),0) v FROM regional_policy WHERE region=?", (region,)).fetchone()
        version = row["v"] + 1
        conn.execute("INSERT INTO regional_policy VALUES(?,?,?,?,?,?)",
                     (region, version, tax_bps, shipping_cents, refund_limit_cents, return_days))
        audit(conn, now, user.id, f"policy.set v{version}", None, region)
    return version
