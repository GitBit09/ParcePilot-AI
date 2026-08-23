"""
Mock Authentication Module
Provides JWT-style tokens for customer and staff roles.
In production, replace with real OAuth2/JWT.
"""

from typing import Optional
from pydantic import BaseModel

# Mock user database
MOCK_USERS = {
    # Customer tokens — scoped to their own account
    "token-northstar-001": {
        "user_id": "northstar_user",
        "account_id": "ACCT-001",
        "account_name": "Northstar Logistics",
        "role": "customer",
        "display_name": "Northstar User",
    },
    "token-lumenworks-002": {
        "user_id": "lumenworks_user",
        "account_id": "ACCT-002",
        "account_name": "LumenWorks",
        "role": "customer",
        "display_name": "LumenWorks User",
    },
    "token-beacon-003": {
        "user_id": "beacon_user",
        "account_id": "ACCT-003",
        "account_name": "Beacon Retail",
        "role": "customer",
        "display_name": "Beacon Retail User",
    },
    "token-axislabs-004": {
        "user_id": "axis_user",
        "account_id": "ACCT-004",
        "account_name": "Axis Labs",
        "role": "customer",
        "display_name": "Axis Labs User",
    },
    # Staff tokens — full access
    "token-staff-rohit": {
        "user_id": "rohit",
        "account_id": None,
        "account_name": None,
        "role": "staff",
        "display_name": "Rohit (Support Agent)",
    },
    "token-staff-maya": {
        "user_id": "maya",
        "account_id": None,
        "account_name": None,
        "role": "staff",
        "display_name": "Maya (Support Agent)",
    },
    "token-staff-priya": {
        "user_id": "priya",
        "account_id": None,
        "account_name": None,
        "role": "staff",
        "display_name": "Priya Mehta (CSM)",
    },
}

# Login credentials for mock login page
LOGIN_CREDENTIALS = {
    "northstar@parcelPilot.com": {"password": "northstar123", "token": "token-northstar-001"},
    "lumenworks@parcelPilot.com": {"password": "lumenworks123", "token": "token-lumenworks-002"},
    "beacon@parcelPilot.com": {"password": "beacon123", "token": "token-beacon-003"},
    "axislabs@parcelPilot.com": {"password": "axislabs123", "token": "token-axislabs-004"},
    "rohit@parcelPilot.com": {"password": "staff123", "token": "token-staff-rohit"},
    "maya@parcelPilot.com": {"password": "staff123", "token": "token-staff-maya"},
    "priya@parcelPilot.com": {"password": "staff123", "token": "token-staff-priya"},
}


class AuthUser(BaseModel):
    user_id: str
    account_id: Optional[str]
    account_name: Optional[str]
    role: str  # "customer" or "staff"
    display_name: str


def authenticate(token: str) -> Optional[AuthUser]:
    """Validate a bearer token and return user info."""
    user_data = MOCK_USERS.get(token)
    if not user_data:
        return None
    return AuthUser(**user_data)


import hashlib

def login(email: str, password: str) -> Optional[dict]:
    """Mock login: returns token on success. If unknown email, creates a guest customer."""
    creds = LOGIN_CREDENTIALS.get(email)
    if creds:
        if creds["password"] != password:
            return None
        token = creds["token"]
        user = MOCK_USERS[token]
        return {"token": token, "user": user}
        
    # Auto-provision guest user for any other email
    token = f"token-guest-{hashlib.md5(email.encode()).hexdigest()[:8]}"
    
    if token not in MOCK_USERS:
        MOCK_USERS[token] = {
            "user_id": email,
            "account_id": "ACCT-GUEST",
            "account_name": "Guest Account",
            "role": "customer",
            "display_name": email.split('@')[0],
        }
        
    user = MOCK_USERS[token]
    return {"token": token, "user": user}


def is_staff(user: AuthUser) -> bool:
    return user.role == "staff"


def is_customer(user: AuthUser) -> bool:
    return user.role == "customer"
