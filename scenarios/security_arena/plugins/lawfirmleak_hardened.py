"""
Thin wrapper to expose the LawFirmLeakHardenedPlugin through the shared
plugins namespace. The real implementation lives under submissions.team_mu.
"""

from submissions.team_mu.lawFirmLeak_hardened.plugin import LawFirmLeakHardenedPlugin  # noqa: F401

__all__ = ["LawFirmLeakHardenedPlugin"]



