from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand
import os
import sys
import multiprocessing # neccessary to keep setuptools quiet in tests

version = '1.1dev'
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
      description="Run OpenOffice as web service.",
      long_description=open("README.rst").read() + "\n\n" +
                       open("CHANGES.txt").read(),
      classifiers=[
          "Development Status :: 3 - Alpha",
          "License :: OSI Approved :: GNU General Public License (GPL)",
          "Programming Language :: Python",
          "Programming Language :: Python :: 2 :: Only",
          "Programming Language :: Python :: 2.6",
          "Programming Language :: Python :: 2.7",
          "Operating System :: POSIX",
          "Framework :: Paste",
          "Environment :: Web Environment",
          "Topic :: Software Development :: Libraries :: Python Modules",
          "Topic :: Internet :: WWW/HTTP",
          "Topic :: Internet :: WWW/HTTP :: WSGI",
          "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
          "Topic :: Internet :: WWW/HTTP :: WSGI :: Middleware",
          "Topic :: Office/Business :: Office Suites",
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
          'argparse',
          'beautifulsoup4',
          'cssutils',
          'htmlmin',
          'Routes',
          'six',
          'WebOb',
          'Paste',
          'PasteDeploy',
      ],
      setup_requires=[],
      extras_require=dict(
          tests = [
              'py-restclient',
              'WebTest',
              'pytest >= 2.0.3',
              'pytest-xdist',
              'pytest-cov',
              ],
          docs = ['Sphinx',
                  ]
          ),
      cmdclass = {'test': PyTest},
      entry_points="""
      [console_scripts]
      oooctl = ulif.openoffice.oooctl:main
      oooclient = ulif.openoffice.client:main
      [ulif.openoffice.processors]
      meta = ulif.openoffice.processor:MetaProcessor
      oocp = ulif.openoffice.processor:OOConvProcessor
      unzip = ulif.openoffice.processor:UnzipProcessor
      zip = ulif.openoffice.processor:ZipProcessor
      tidy = ulif.openoffice.processor:Tidy
      css_cleaner = ulif.openoffice.processor:CSSCleaner
      html_cleaner = ulif.openoffice.processor:HTMLCleaner
      error = ulif.openoffice.processor:Error
      [paste.app_factory]
      docconverter = ulif.openoffice.wsgi:make_docconverter_app
      xmlrpcapp = ulif.openoffice.xmlrpc:make_xmlrpc_app
      [paste.filter_app_factory]
      htaccess = ulif.openoffice.htaccess:make_htaccess
      """,
      )
