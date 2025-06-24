from setuptools import setup, find_packages

setup(
    name="calendar-extractor",
    version="1.0.0",
    description="Calendar event extractor and Base44 sync tool",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "pandas>=1.5.0",
        "boto3>=1.26.0",
        "python-dateutil>=2.8.2",
        "python-dotenv>=1.0.0",
        "hubspot-api-client>=8.0.0",
        "sqlalchemy>=2.0.0",
        "psycopg2-binary>=2.9.10",
    ],
    entry_points={
        "console_scripts": [
            "calendar-extractor=core.main:main",
        ],
    },
    python_requires=">=3.8",
) 