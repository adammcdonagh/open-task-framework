from setuptools import setup
setup(
    name="open-task-framework",
    install_requires=[
        "jsonschema",
        "paramiko"
    ],
    packages=["opentaskpy"],
    scripts=["bin/task-run"],
)
