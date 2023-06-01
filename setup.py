from setuptools import setup, find_packages

setup(name='bbquiz',
      version='0.2',
      description="A commonand tool for generating quizzes for BlackBoard and Latex",
      author='Francois Pitie',
      author_email='pitief@tcd.ie',
      license='GPLv3',
      packages=['bbquiz', 'bbquiz.bbyaml', 'bbquiz.render', 'bbquiz.markdown'],
      package_dir={'': 'src'},
      package_data={'bbquiz': ['templates/*']},
      install_requires=[
          'markdown','bs4','pyyaml','rich', 'rich-argparse',
          'jinja2', 'colorama', 'watchdog', 'mistletoe', 'appdirs'
      ],      
      entry_points={
          "console_scripts": [
              "bbquiz = bbquiz.cli:main"
          ]
      },
      python_requires='>3.5',
      )


