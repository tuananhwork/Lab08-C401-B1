"""
tests/conftest.py — Pytest configuration cho Day 09 Lab
"""

import pytest


def pytest_configure(config):
    """Register custom marks."""
    config.addinivalue_line(
        "markers",
        "integration: marks tests that require ChromaDB index (deselect with '-m \"not integration\"')",
    )
