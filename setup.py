from setuptools import setup, find_packages

setup(name='bbquiz',
      version='0.1',
      author='Francois Pitie',
      packages=find_packages(),
      # packages=['bbquiz',
      #           'bbquiz.bbyaml',
      #           'bbquiz.markdown_export',
      #           'bbquiz.render'],
      package_dir={'bbquiz': 'bbquiz'},
      package_data={'bbquiz': ['templates/*']},
      install_requires=[
          'markdown','bs4','pyyaml','rich', 'jinja2', 'colorama', 'watchdog'
      ],      
      entry_points={
          "console_scripts": [
              "bbquiz = bbquiz.cli:main"
          ]
      }
      )


