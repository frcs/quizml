
from quizml.utils import filter_yaml

def test_filter_yaml():
    
    yaml = [{ 'A': '\n  \n item 1\n\n',
              'B': [{'BA': '\n  \n item B1\n\n',
                     'BB': '\n  \n item B2\n\n'}],
              'C': '\n  \n item 3\n\n'},
           { 'F': '   item 4 \n'}]

    yaml0 = [{ 'A': 'item 1',
               'B': [{'BA': 'item B1',
                      'BB': 'item B2'}],
               'C': 'item 3'},
             { 'F': 'item 4'}]
    
    f = lambda a : a.strip() if isinstance(a, str) else a
    
    yaml1 = filter_yaml(yaml, f)
    assert(yaml0 == yaml1)
    
