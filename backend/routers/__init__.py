from routers.auth import router as auth_router
from routers.companies import router as companies_router
from routers.mailboxes import router as mailboxes_router
from routers.warmup import router as warmup_router
from routers.dashboard import router as dashboard_router
from routers.external_contacts import router as external_contacts_router
from routers.access_requests import router as access_requests_router

# Also expose as module-level attributes for `from routers import x` style
from routers import auth, companies, mailboxes, warmup, dashboard, external_contacts, access_requests

__all__ = [
    "auth_router", "companies_router", "mailboxes_router",
    "warmup_router", "dashboard_router",
    "external_contacts_router", "access_requests_router",
]
