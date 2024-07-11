from setuptools import setup, find_packages

# Link package dependencies with requirements.txt
# Note: This may be bad design for deployment. 
# TODO: Finalize dependency versioning and add a fixed list to install_requires.
with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name="termite",
    version="0.1",
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    install_requires=requirements
)