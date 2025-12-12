"""
Thin wrapper to expose PhonePalProbePlugin via the shared plugins namespace.
Implementation lives under submissions.team_mu.phonePalProbe.
"""

from submissions.team_mu.phonePalProbe.plugin import PhonePalProbePlugin  # noqa: F401

__all__ = ["PhonePalProbePlugin"]



