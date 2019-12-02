from setuptools import setup, find_packages

setup(name='ease-test',
      version='0.1.1',
      description='pytest plugin for run/report settings',
      author='YangHuawei',
      author_email='yanghuawei@hujiang.com',
      url='http://qa.yeshj.com',
      packages=find_packages(),
      keywords='requests api test easy pytest plugin',
      entry_points={
          'console_scripts': ['pycodegen=scripts.py_codegen.py_codegen_v2:main'],
          'pytest11': ['salt=pytest_salt.plugin']
      },
      install_requires=['pytest>=4.0',
                        'requests',
                        'jsondiff',
                        'peewee',
                        'autopep8'
                        ],
      classifiers=[
          'Operating System :: POSIX',
          'Operating System :: Microsoft :: Windows',
          'Operating System :: MacOS :: MacOS X',
          'Topic :: Software Development :: Quality Assurance',
          'Topic :: Software Development :: Testing',
          'Topic :: Utilities',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7',
          'Programming Language :: Python :: 3.8',
      ])
