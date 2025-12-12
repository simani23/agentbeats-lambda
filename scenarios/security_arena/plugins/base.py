#!/usr/bin/env python3
"""
Fixed base classes for scenario plugins (participant-friendly version)

This version removes the 5 unused abstract methods that exist in the current
repo but are never called by the orchestrator. It allows custom scenarios
to work without modifying the framework.

Use this file temporarily until the upstream repo fixes base.py.
"""

from abc import ABC, abstractmethod
from typing import Any, List, Dict


class ScenarioPlugin(ABC):
    """
    Base class for scenario plugins (fixed version).

    Only includes methods actually used by the orchestrator.
    """

    def __init__(self, config: dict[str, Any]):
        self.config = config

    # === Attacker Instructions (REQUIRED) ===

    @abstractmethod
    def get_attack_objective(self) -> str:
        """What the attacker should try to achieve."""
        pass

    @abstractmethod
    def get_domain_description(self) -> str:
        """Describe the domain/system being attacked."""
        pass

    @abstractmethod
    def get_attacker_goal(self) -> str:
        """Specific success condition for the attacker."""
        pass

    @abstractmethod
    def get_attack_constraints(self) -> str:
        """Rules the attacker must follow."""
        pass

    # === Defender Instructions (REQUIRED) ===

    @abstractmethod
    def get_defender_role(self) -> str:
        """Who the defender is (e.g., 'You are a legal discovery AI...')"""
        pass

    @abstractmethod
    def get_defender_task_description(self) -> str:
        """What the defender should do with input."""
        pass

    @abstractmethod
    def get_output_format(self) -> str:
        """How the defender should format its response."""
        pass

    @abstractmethod
    def get_security_guidelines(self) -> str:
        """Hardening instructions to resist attacks."""
        pass

    # === Success Detection (REQUIRED) ===

    @abstractmethod
    def check_success(
        self,
        defender_response: str,
        original_input: str,
        modified_input: str,
    ) -> tuple[bool, Any]:
        """Return (success: bool, extracted_value: Any)"""
        pass

    # === Baseline Test (REQUIRED) ===

    @abstractmethod
    def get_baseline_tasks(self) -> List[Dict[str, Any]]:
        """Return list of clean inputs for baseline testing."""
        pass

    @abstractmethod
    def get_baseline_expected_value(self) -> Any:
        """What should be extracted from clean baseline runs."""
        pass

    # === Optional overrides ===

    def format_current_input(self, input_data: str) -> str:
        """Optional: format input before showing to agents."""
        return input_data

    def get_scenario_name(self) -> str:
        """Human-readable name for logs/results."""
        return self.__class__.__name__.replace("Plugin", "")