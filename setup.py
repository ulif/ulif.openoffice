from setuptools import setup, find_packages
import os

version = '0.2.1'

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
        "License :: OSI Approved :: Zope Public License",
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
      ],
      setup_requires=["Sphinx-PyPI-upload"],
      extras_require=dict(
        test = [
            'zope.testing',
            'zc.recipe.egg',
            ],
        doc = ['Sphinx',
               'collective.recipe.sphinxbuilder']
        ),
      entry_points="""
      [console_scripts]
      oooctl = ulif.openoffice.oooctl:main
      pyunoctl = ulif.openoffice.pyunoctl:main
      convert = ulif.openoffice.convert:main
      """,
      )
