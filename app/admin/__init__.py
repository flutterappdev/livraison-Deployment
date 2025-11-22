from .site import CustomAdminSite
from .organisation import OrganisationAdmin
from .candidat import CandidatAdmin
from .user import CustomUserAdmin
from .role import OrganisationRoleAdmin
from .task import ScrapingTaskAdmin

__all__ = [
    'CustomAdminSite',
    'OrganisationAdmin',
    'CandidatAdmin',
    'CustomUserAdmin',
    'OrganisationRoleAdmin',
    'ScrapingTaskAdmin'
]
