"""Shared models for the deployable backend framework."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class ComponentDescriptor:
    """Describe one logical backend role inside the deployable framework."""

    id: str
    name: str
    role: str
    responsibilities: List[str]
    deployment_unit: str = "single-fastapi-service"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "responsibilities": self.responsibilities,
            "deployment_unit": self.deployment_unit,
        }
