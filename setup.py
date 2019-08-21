# ----------------------------------------------------------------------------
# Copyright (c) 2017-, LabControl development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from setuptools import setup, find_packages
from glob import glob
import versioneer

classes = """
    Development Status :: 3 - Alpha
    License :: OSI Approved :: BSD License
    Topic :: Scientific/Engineering :: Bio-Informatics
    Topic :: Software Development :: Libraries :: Application Frameworks
    Topic :: Software Development :: Libraries :: Python Modules
    Programming Language :: Python
    Programming Language :: Python :: 3.5
    Operating System :: POSIX :: Linux
    Operating System :: MacOS :: MacOS X
"""

# show description
with open('README.md') as f:
    long_description = f.read()

classifiers = [s.strip() for s in classes.split('\n') if s]

setup(name='labcontrol',
      long_description=long_description,
      version=versioneer.get_version(),
      cmdclass=versioneer.get_cmdclass(),
      license='BSD',
      description='A lab manager for plate maps and sequence flows',
      author='Jeff DeReus',
      author_email='jdereus@ucsd.edu',
      url='https://github.com/biocore/LabControl',
      test_suite='nose.collector',
      packages=find_packages(),
      include_package_data=True,
      package_data={
        'labcontrol.db': [
            'support_files/*',
            'support_files/patches/*'],
        'labcontrol.gui': [
            'handlers/*',
            'handlers/composition_handlers/*',
            'handlers/composition_handlers/test/*',
            'handlers/process_handlers/*',
            'handlers/process_handlers/test/*',
            'js_tests/*',
            'js_tests/qunit/*',
            'static/*',
            'static/css/*',
            'static/img/*',
            'static/js/*',
            'static/vendor/*',
            'static/vendor/css/*',
            'static/vendor/css/images/*',
            'static/vendor/fonts/*',
            'static/vendor/js/*',
            'static/vendor/js/slickgrid.plugins/*',
            'static/vendor/licenses/*',
            'templates/*',
            'test/*', ]},
      scripts=glob('scripts/*'),
      extras_require={'test': ['nose >= 0.10.1', 'pep8', 'mock',
                               'qiita_client']},
      install_requires=['click', 'tornado < 6', 'psycopg2', 'bcrypt', 'numpy',
                        'pandas', 'natsort', 'versioneer'],
      classifiers=classifiers
      )
