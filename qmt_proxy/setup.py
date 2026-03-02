"""Setup configuration for qmt_proxy package."""

from setuptools import find_packages, setup

setup(
    name="qmt-proxy",
    version="0.1.0",
    description="Trading message relay between Trading Initiator and Trading Executor",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        "fastapi>=0.104.0",
        "uvicorn[standard]>=0.24.0",
        "pydantic>=2.0.0",
    ],
    python_requires=">=3.10",
)
