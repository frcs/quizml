

from ..BlackBoardTestPkg import BlackBoardTestPkg


def bb_multiple_choice(pool, entry, md_dict):
    return

def bb_essay(pool, entry, md_dict):
    return

def bb_matching(pool, entry, md_dict):
    return

def bb_header(pool, entry, md_dict):
    return

def bb_ordering(pool, entry, md_dict):
    return

def correctness(a):
    if a['correct']:
        return 'correct'
    else:
        return 'incorrect'
    
def bb_multiple_answer(pool, entry, md_dict):

    answers = []
    correct = []
    for i, a in enumerate(entry['answers']):
        answers.append(md_dict[a['answer']])
        if correctness(a) == 'correct':
            correct.append(i)

    pool.addMAQ(
        'Q',
        md_dict[entry['question']],
        answers = answers,
        correct = correct,
        positive_feedback="you don't suck",
        negative_feedback="you suck"
    )
    return   

def render(filename, yaml_data, md_dict):

    handlers = {
        'mc': bb_multiple_choice,
        'ma': bb_multiple_answer,
        'essay': bb_essay,
        'matching': bb_matching,
        'header': bb_header,
        'ordering': bb_ordering,
    }

    with BlackBoardTestPkg.Package(filename) as package:        
    
        #If you create hundreds of pools, you might want to organise them into tests, this can be done like so:
        with package.createTest(filename) as test:
            #Note, the pool is created from the test, instead of the
            #package. We also use the optional points_per_q and
            #questions_per_test now
            with test.createPool('Unique questions (in a test)',
                                 description="",
                                 instructions="",
                                 points_per_q=6,
                                 questions_per_test=1) as pool:

                for entry in yaml_data:
                    handlers[entry['type']](pool, entry, md_dict)
        


