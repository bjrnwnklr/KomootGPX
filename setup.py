from setuptools import setup, find_packages

setup(
    name="komootgpx",
    version="0.1.0",
    description="Download Komoot tracks and highlights as GPX files with metadata.",
    long_description="""Download Komoot tracks and highlights as GPX files with
    metadata.
    Original repository by Tim Schneeberger. This fork maintained by Bjoern Winkler.
    """,
    author="Tim Schneeberger; Bjoern Winkler",
    author_email="bjoern@bjoern-winkler.de",
    url="https://github.com/bjrnwnklr/KomootGPX",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3 :: Only",
    ],
    packages=find_packages(include=["komootgpx"]),
    python_requires=">=3.9",
    install_requires=[
        "certifi>=2020.12.5",
        "chardet>=4.0.0",
        "colorama>=0.4.4",
        "gpxpy>=1.4.2",
        "idna>=2.10",
        "requests>=2.25.1",
        "urllib3>=1.26.3",
    ],
    extras_require={"interactive": ["jupyter"]},
    setup_requires=["pytest", "flake8", "black"],
    tests_require=["pytest"],
)
