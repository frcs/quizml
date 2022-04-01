#!/usr/bin/env python3

import BlackBoardTestPkg2

from scipy import stats, optimize, interpolate

#You need a package, which is what you'll eventually upload to
#Blackboard/MyAberdeen
with BlackBoardTestPkg.Package("MyQuestionPools") as package:        

    
    #If you create hundreds of pools, you might want to organise them into tests, this can be done like so:
    with package.createTest("Test: Creating using add_pool and per question points etc") as test:
        #Note, the pool is created from the test, instead of the
        #package. We also use the optional points_per_q and
        #questions_per_test now
        with test.createPool(
                'Unique questions (in a test)',
                description="",
                instructions="",
                points_per_q=6,
                questions_per_test=2
        ) as pool:
            pool.addNumQ(
                'Test question 1',
                'What is the number four in arabic numerals?',
                4,
                erramt=0.1,
                positive_feedback="Good!",
                negative_feedback="Duh?"
            )
            pool.addNumQ(
                'Test question 2',
                'What is the number four in arabic numerals?',
                4,
                erramt=0.1,
                positive_feedback="Good!",
                negative_feedback="Duh?"
            )
            pool.addNumQ(
                'Test question 3',
                'What is the number four in arabic numerals?',
                4,
                erramt=0.1,
                positive_feedback="Good!",
                negative_feedback="Duh?"
            )
            pool.addNumQ(
                'Test question 4',
                'What is the number four in arabic numerals?',
                4,
                erramt=0.1,
                positive_feedback="Good!",
                negative_feedback="Duh?"
            )

        
