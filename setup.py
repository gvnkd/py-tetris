from setuptools import setup

setup(
    name="py-tetris",
    version="1.0.0",
    py_modules=["tetris"],
    entry_points={"console_scripts": ["py-tetris = tetris:main"]},
)
