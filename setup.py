from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand
import os
import sys
import multiprocessing # neccessary to keep setuptools quiet in tests

version = '1.0dev'
tests_path = os.path.join(os.path.dirname(__file__), 'tests')
class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        args = sys.argv[sys.argv.index('test')+1:]
        self.test_args = args
        self.test_suite = True
    def run_tests(self):
        #import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.test_args)
        sys.exit(errno)

setup(name='ulif.openoffice',
      version=version,
      description="Helpers to bridge different Python envs and OpenOffice.org.",
      long_description=open("README.txt").read() + "\n\n" +
                       open(os.path.join("doc", "source", "intro.txt"
                                         )).read() + "\n\n" +
                       open(os.path.join("doc", "source", "install.txt"
                                         )).read() + "\n\n" +
                       open(os.path.join("doc", "source", "usage.txt"
                                         )).read() + "\n\n" +
                       open(os.path.join("src", "ulif", "openoffice",
                                         "README.txt")).read() + "\n\n" +
                       open("CHANGES.txt").read(),
      classifiers=[
        "Development Status :: 3 - Alpha",
        "Framework :: Buildout",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        ],
      keywords='openoffice pyuno uno openoffice.org libreoffice',
      author='Uli Fouquet',
      author_email='uli at gnufix.de',
      url='http://pypi.python.org/pypi/ulif.openoffice',
      license='GPL',
      packages=find_packages('src', exclude=['ez_setup']),
      package_dir = {'': 'src'},
      namespace_packages=['ulif', ],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          'zc.buildout<2.0',
          'CherryPy>=3.2.0',
          'beautifulsoup4',
          'cssutils',
      ],
      setup_requires=[],
      extras_require=dict(
        tests = [
            #'zope.testing',
            #'zc.recipe.egg',
            #'twill',
            'py-restclient',
            'WebTest',
            'pytest >= 2.0.3',
            'pytest-xdist',
            #'unittest2',
            #'nose >= 1.0.0',
            ],
        docs = ['Sphinx',
               'collective.recipe.sphinxbuilder']
        ),
      cmdclass = {'test': PyTest},
      entry_points="""
      [nopytest11]
      buildout-doctest = ulif.openoffice.testing_buildout
      mydoctest = ulif.openoffice.pytest_doctest
      [console_scripts]
      oooctl = ulif.openoffice.oooctl:main
      pyunoctl = ulif.openoffice.pyunoctl:main
      restserver = ulif.openoffice.restserver:main
      [ulif.openoffice.processors]
      oocp = ulif.openoffice.processor:OOConvProcessor
      unzip = ulif.openoffice.processor:UnzipProcessor
      zip = ulif.openoffice.processor:ZipProcessor
      tidy = ulif.openoffice.processor:Tidy
      css_cleaner = ulif.openoffice.processor:CSSCleaner
      html_cleaner = ulif.openoffice.processor:HTMLCleaner
      error = ulif.openoffice.processor:Error
      """,
      )
