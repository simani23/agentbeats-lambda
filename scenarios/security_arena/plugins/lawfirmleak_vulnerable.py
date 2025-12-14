"""
Thin wrapper to expose the LawFirmLeakVulnerablePlugin through the shared
plugins namespace. The real implementation lives under submissions.team_mu.
"""

from submissions.team_mu.lawFirmLeak_vulnerable.plugin import LawFirmLeakVulnerablePlugin  # noqa: F401

__all__ = ["LawFirmLeakVulnerablePlugin"]




