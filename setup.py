from setuptools import setup, find_packages
setup(name='notebook-test', version='0.1.0', packages=find_packages(),
    install_requires=['click>=8.0','nbformat>=5.0','nbclient>=0.7'],
    entry_points={'console_scripts':['notebook-test=notebook_test.cli:main']}, python_requires='>=3.9')
