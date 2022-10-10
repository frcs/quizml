from setuptools import setup, find_packages

setup(name='bbquiz',
      version='0.1',
      author='Francois Pitie',
      packages=['bbquiz',
                'bbquiz.bbyaml',
                'bbquiz.markdown_export',
                'bbquiz.render',
                'bbquiz.BlackBoardTestPkg'],
      package_dir={'bbquiz': 'bbquiz'},
      package_data={'bbquiz': ['templates/*.tex']},
      install_requires=[
          'markdown','bs4','pyyaml','rich','lxml'
      ],      
      entry_points={
          "console_scripts": [
              "bbquiz = bbquiz.__main__:main"
          ]
      }
      )


