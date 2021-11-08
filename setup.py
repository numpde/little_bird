import setuptools

# python setup.py sdist bdist_wheel
# twine upload dist/* && rm -rf build dist *.egg-info

setuptools.setup(
    name="little_bird",
    version="0.0.1",
    author="RA",
    author_email="numpde@null.net",
    keywords="python twitter",
    description="Twitter module.",
    long_description="Twitter module. [Info](https://github.com/numpde/little_bird).",
    long_description_content_type="text/markdown",
    url="https://github.com/numpde/little_bird",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=['python-dotenv', 'requests-oauthlib'],

    # Required for includes in MANIFEST.in
    #include_package_data=True,

    test_suite="nose.collector",
    tests_require=["nose"],
)
