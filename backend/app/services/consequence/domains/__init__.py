"""__init__.py for domains package."""
from app.services.consequence.domains.base import DomainImpact, DomainModule
from app.services.consequence.domains.flood import FloodModule
from app.services.consequence.domains.mobility import MobilityModule

__all__ = ["DomainModule", "DomainImpact", "FloodModule", "MobilityModule"]
