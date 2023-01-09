"""Setup function for opentaskpy package."""
from setuptools import setup
setup(
    name="open-task-framework",
    install_requires=[
        "jsonschema",
        "paramiko",
        "jinja2"
    ],
    packages=["opentaskpy"],
    scripts=["bin/task-run"],
)
