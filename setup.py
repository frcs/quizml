from setuptools import setup, find_packages


setup(name='bbquiz',
      version='0.3',
      description="A commonand tool for generating quizzes for BlackBoard and Latex",
      author='Francois Pitie',
      author_email='pitief@tcd.ie',
      license='GPLv3',
      package_dir={'': 'src'},
      package_data={'bbquiz': ['templates/*']},
      packages=['bbquiz', 'bbquiz.bbyaml', 'bbquiz.render', 'bbquiz.markdown'],

      install_requires=[
          'bs4',
          'strictyaml==1.7.3',
          'rich',
          'rich-argparse',
          'jinja2',
          'colorama',
          'watchdog',
          'mistletoe==1.2',
          'appdirs'
      ],      
      entry_points={
          "console_scripts": [
              "bbquiz = bbquiz.cli:main"
          ]
      },
      python_requires='>3.5',
      )


