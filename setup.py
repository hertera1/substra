from setuptools import Command, find_packages, setup
from subprocess import call

class RunTests(Command):
    """Run all tests."""
    description = 'run tests'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        """Run all tests!"""
        errno = call(['py.test', '--ignore=tests/e2e'])
        raise SystemExit(errno)

setup(
    name='substra-sdk-py',
    version='0.0.1',
    description='Python SDK for interacting with the substrabac project',
    url='https://github.com/SubstraFoundation/substra-sdk-py',
    author='Guillaume Cisco',
    author_email='guillaumecisco@gmail.com',
    license='MIT',
    packages=['substra_sdk_py'],
    install_requires=[
        'requests',
    ],
    zip_safe=False,
    extras_require={
        'test': ['pytest', 'mock'],
    },
    cmdclass={'test': RunTests}
)
