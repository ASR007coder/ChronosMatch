
from setuptools import Extension, setup
from Cython.Build import cythonize

extensions = [
    Extension(
        name="backend.engine.cython.matching_core",
        sources=["backend/engine/cython/matching_core.pyx"],
    ),
    Extension(
        name="backend.engine.cython.order_book_core",
        sources=["backend/engine/cython/order_book_core.pyx"],
    ),
]

setup(
    name="chronosmatch-engine",
    ext_modules=cythonize(
        extensions,
        compiler_directives={"language_level": "3"},
    ),
)
