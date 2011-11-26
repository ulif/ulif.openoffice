from setuptools import setup, find_packages
import os

version = '0.4.1dev'

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
      keywords='openoffice pyuno uno openoffice.org',
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
          'zc.buildout',
          'CherryPy>=3.2.0',
          'BeautifulSoup>=3.2.0',
          'cssutils',
      ],
      setup_requires=["Sphinx-PyPI-upload"],
      extras_require=dict(
        test = [
            'zope.testing',
            'zc.recipe.egg',
            'twill',
            'py-restclient',
            'WebTest',
            'pytest >= 2.0.3',
            'pytest-xdist',
            'unittest2',
            'nose >= 1.0.0',
            ],
        doc = ['Sphinx',
               'collective.recipe.sphinxbuilder']
        ),
      entry_points="""
      [pytest11]
      buildout-doctest = ulif.openoffice.testing_buildout
      mydoctest = ulif.openoffice.pytest_doctest
      [console_scripts]
      oooctl = ulif.openoffice.oooctl:main
      pyunoctl = ulif.openoffice.pyunoctl:main
      convert = ulif.openoffice.convert:main
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
