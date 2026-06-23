#!/usr/bin/env python3
"""setup.py for trip-cli (Trip.com CLI)."""

from setuptools import find_packages, setup

setup(
    name="trip-cli",
    version="0.1.0",
    description="Agent-native CLI for Trip.com hotels",
    url="https://github.com/HKUDS/CLI-Anything",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "click>=8.0.0",
        "playwright>=1.40.0",
        "typing_extensions>=4.0.0",
    ],
    extras_require={
        "dev": ["pytest>=7.0.0"],
    },
    # entry_points omitted for Windows robustness (script generation flakiness).
    # Launcher: scripts/trip-cli.cmd  or use `python -m trip_cli`
    # In production Linux/Mac you can re-enable console_scripts: "trip-cli=trip_cli.cli:main"
    package_data={
        "trip_cli": ["data/*.json"],
    },
    include_package_data=True,
    zip_safe=False,
)
