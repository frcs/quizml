#!/usr/bin/env python3

# massively borrowed from BlackboardQuizMaker
# https://github.com/toastedcrumpets/BlackboardQuizMaker
# 

from lxml import etree
import lxml.html as html
import time
import zipfile
import re
import os
import uuid
from xml.sax.saxutils import escape, unescape
from PIL import Image
from io import StringIO
from io import BytesIO
import itertools
#import scipy.stats
#import sympy
import random

import zlib


from bs4 import BeautifulSoup


BBKPGINFO = """
#Bb PackageInfo Property File
#Tue Mar 24 00:01:23 GMT 2020
cx.config.learn.site.id=20fc3687-607e-41e9-81b8-11a72be9fe5f
db.product.version=9.6.15
cx.config.full.value=CxConfig{operation\\=EXPORT, courseid\\=EX3502_20, package\\=/usr/local/blackboard/apps/tomcat/temp/plugins/bb-assessment/b071a637-db66-4e7d-b4e4-1d5cde75ff6f/Pool_ExportFile_EX3502_20_TestPool.zip, logger\\=CxLogger{logs\\=[Log{name\\=/usr/local/blackboard/apps/tomcat/temp/plugins/bb-assessment/b071a637-db66-4e7d-b4e4-1d5cde75ff6f/Pool_ExportFile_EX3502_20_TestPool.log, verbosity\\=default}, Log{name\\=STDOUT, verbosity\\=default}], logHooks\\=[]}, resource_type_inclusions\\=[], area_inclusions\\=[ALIGNMENTS, RUBRIC], area_exclusions\\=[ALL], object_inclusions\\={POOL\\=[_1191882_1]}, object_exclusions\\={}, features\\={BypassDiskQuotaCheck\\=false, ArchiveUserPasswords\\=false, CreateOrg\\=false, AlternateAssessmentCsLinks\\=false, ImportCourseStructure\\=false, Bb5LinkToBrokenImageFix\\=true}, strHostName\\=null, isCommandLineRequest\\=false, isCourseConversion\\=false, eventHandlers\\=[], primaryNode\\=null, nodes\\=[], title\\=null, packageVersion\\=null, archiveCSItems\\=true, archiveECSItems\\=false, archiveOnlyReferencedPpg\\=true, commonCartridge\\=false, qti21Package\\=false, createChildFolder\\=false, csDir\\=, excludedCsFolderIds\\=null, homeDir\\=, includeGradeHistoryInArchive\\=false, isExportPackage\\=false, logDetailRubricInfo\\=false, taskId\\=null, useDefaultLog\\=true}
cx.config.learn.installation.id=03e915a9e8534aed8065ae8bb44a0527
java.version=11.0.4
os.arch=amd64
cx.config.package.name=/usr/local/blackboard/apps/tomcat/temp/plugins/bb-assessment/b071a637-db66-4e7d-b4e4-1d5cde75ff6f/Pool_ExportFile_EX3502_20_TestPool.zip
java.class.path=/usr/local/blackboard/apps/service-wrapper/lib/wrapper.jar\\:/usr/lib/jvm/java-11-amazon-corretto/lib/tools.jar\\:/usr/local/blackboard/apps/tomcat/lib/bb-tomcat-bootstrap.jar\\:/usr/local/blackboard/apps/tomcat/bin/bootstrap.jar\\:/usr/local/blackboard/apps/tomcat/bin/tomcat-juli.jar
app.release.number=3800.4.0-rel.40+d78544e
cx.package.info.version=6.0
java.home=/usr/lib/jvm/java-11-amazon-corretto
os.version=4.4.0-1073-aws
java.default.locale=en
db.product.name=PostgreSQL
cx.config.operation=blackboard.apps.cx.CxConfig$Operation\\:EXPORT
cx.config.logs=[Log{name\\=/usr/local/blackboard/apps/tomcat/temp/plugins/bb-assessment/b071a637-db66-4e7d-b4e4-1d5cde75ff6f/Pool_ExportFile_EX3502_20_TestPool.log, verbosity\\=default}, Log{name\\=STDOUT, verbosity\\=default}]
cx.config.course.id=EX3502_20
java.vendor=Amazon.com Inc.
cx.config.file.references=false
cx.config.package.identifier=237f3445fd1c4d80b9f5a04daca35cef
db.driver.name=PostgreSQL JDBC Driver
os.name=Linux
db.driver.version=42.2.5
"""


                      
def flow_mat(node, classname, text):
    e = etree.SubElement(e, 'flow_mat', {'class': classname})
    material(e, text)

def material(node, text):
    e = etree.SubElement(node, 'flow_mat', {'class': classname})
    e = etree.SubElement(e, 'material')
    e = etree.SubElement(e, 'mat_extension')
    e = etree.SubElement(e, 'mat_formattedtext', {'type':'HTML'})
    e.text = text
       
def formatted_text_html(node, text):
    e = etree.SubElement(node, 'flow', {'class': "FORMATTED_TEXT_BLOCK"})
    flow_mat(e, text)
    

    
def metadata(node, name, metadata):
    md = etree.SubElement(node, name.lower()+'metadata')
    
    default = {
        'bbmd_asi_object_id' : None,
        'bbmd_asitype' : None,
        'bbmd_assessmenttype' : None,
        'bbmd_sectiontype' : None,
        'bbmd_questiontype' : None,
        'bbmd_is_from_cartridge' : 'false',
        'bbmd_is_disabled' : 'false',
        'bbmd_negative_points_ind' : 'N',
        'bbmd_canvas_fullcrdt_ind' : 'false',
        'bbmd_all_fullcredit_ind' : 'false',
        'bbmd_numbertype' : 'none',
        'bbmd_partialcredit' : 'false',
        'bbmd_orientationtype' : 'vertical',
        'bbmd_is_extracredit' : 'false',
        'qmd_absolutescore_max' :'10.000',
        'qmd_weighting' : '1',
        'qmd_instructornotes' = ''
    }

    for key, val in default:
        etree.SubElement(md, key).text = metadata[key] if key in metadata else val


def addMAQ(
        section,
        bbid = ''
        question_id = 'Q1',
        title = '',
        question = '',
        answers = [''],
        correct = [0],
        positive_feedback = "Good work",
        negative_feedback = "That's not correct",
        instructor_notes =  "",
        shuffle_ans = False,
        weight = 0,
        marks = 10
):
    
    # Set sensible default weights if not specified
    if weights is None:
        na = len(answers)
        nc = len(correct)
        wc = +100/nc
        wi = -100/(na-nc)
        weights = [(wc if i in correct else wi) for i in range(na)]
    else:
        assert len(weights)==len(answers)
        
    #Add the question to the list of questions
    elt_item = etree.SubElement(elt_section, 'item', {'title':title, 'maxattempts':'0'})

    metadata(elt_item, 'item',
             {'bbmd_asi_object_id': bbid,
              'bbmd_asitype': 'Item',
              'bbmd_sectiontype': 'Subsection',
              'bbmd_questiontype': 'Multiple Answer',
              'qmd_absolutescore_max': str(marks),
              'qmd_weighting': str(weight),
              'qmd_instructornotes': instructor_notes
              })
        
    elt_presentation = etree.SubElement(elt_item, 'presentation')
    elt_flowBlock = etree.SubElement(
        elt_presentation, 'flow',
        {'class':'Block'})

    # Question Block
    e = etree.SubElement(elt_flowBlock, 'flow', {'class':'QUESTION_BLOCK'})
    formatted_text_html(e, question)

    # Response Block
    elt_responseBlock = etree.SubElement(
        elt_flowBlock, 'flow',
        {'class':'RESPONSE_BLOCK'})
    elt_response_lid = etree.SubElement(
        elt_responseBlock, 'response_lid',
        {'ident':'response',
         'rcardinality':'Multiple',
         'rtiming':'No'})
    elt_render_choice = etree.SubElement(
        elt_response_lid, 'render_choice',
        {'shuffle':'Yes' if shuffle_ans else 'No',
         'minnumber':'0',
         'maxnumber':'0'})

    a_uuids = []
    for idx, answer_text in enumerate(answers):
        elt_flow_label = etree.SubElement(
            elt_render_choice, 'flow_label',
            {'class':'Block'})
        
        a_uuids.append(uuid.uuid4().hex)
            
        elt_response_label = etree.SubElement(
            elt_flow_label,
            'response_label',
            {'ident':a_uuids[-1],
             'shuffle':'Yes',
             'rarea':'Ellipse',
             'rrange':'Exact'})

        formatted_text_html(elt_response_label, answer_text)
        classname = "correct" if idx in correct else "incorrect"

    # Reprocessing Block
            
    elt_resprocessing = etree.SubElement(
        elt_item,
        'resprocessing',
        {'scoremodel':'SumOfScores'})
    elt_outcomes = etree.SubElement(elt_resprocessing, 'outcomes', {})
    elt_decvar = etree.SubElement(
        elt_outcomes, 'decvar',
        {'varname':'SCORE',
         'vartype':'Decimal',
         'defaultval':'0',
         'minvalue':'0'
         'maxvalue': marks})
        
    elt_respcondition = etree.SubElement(
        elt_resprocessing,
        'respcondition',
        {'title':'correct'})

    elt_conditionvar = etree.SubElement(elt_respcondition, 'conditionvar')
    elt_and = etree.SubElement(elt_conditionvar, 'and')

    for i in range(len(answers)):
        if i in correct:
            etree.SubElement(
                elt_and, 'varequal',
                {'respident':'response',
                 'case':'No'}).text = a_uuids[i]
        else:
            elt_not = etree.SubElement(elt_and, 'not')
            etree.SubElement(
                elt_not,
                'varequal',
                {'respident':'response',
                 'case':'No'}).text = a_uuids[i]
            
    etree.SubElement(
        respcondition, 'setvar',
        {'variablename':'SCORE',
         'action':'Set'}).text = 'SCORE.max'
    
    etree.SubElement(
        respcondition, 'displayfeedback',
        {'linkrefid':'correct',
         'feedbacktype':'Response'})
    
    elt_respcondition = etree.SubElement(
        elt_resprocessing, 'respcondition',
        {'title':'incorrect'})
        
    elt_conditionvar = etree.SubElement(elt_respcondition, 'conditionvar')
    etree.SubElement(elt_conditionvar, 'other')
        
    etree.SubElement(
        elt_respcondition, 'setvar',
        {'variablename':'SCORE',
         'action':'Set'}).text = '0'
        
    etree.SubElement(
        elt_respcondition, 'displayfeedback',
        {'linkrefid':'incorrect',
         'feedbacktype':'Response'})
        
    for idx, luuid in enumerate(a_uuids):
        elt_respcondition = etree.SubElement(
            elt_resprocessing, 'respcondition')
        elt_conditionvar = etree.SubElement(
            elt_respcondition, 'conditionvar')
        etree.SubElement(
            elt_conditionvar, 'varequal',
            {'respident':luuid,
             'case':'No'})
        etree.SubElement(
            elt_respcondition, 'setvar',
            {'variablename':'SCORE',
             'action':'Set'}).text = '{:.3f}'.format(weights[idx])            
        
    elt_itemfeedback = etree.SubElement(
        elt_item, 'itemfeedback',
        {'ident':'correct',
         'view':'All'})

    flow_mat(elt_itemfeedback, positive_feedback)
              
    elt_itemfeedback = etree.SubElement(
        elt_item, 'itemfeedback',
        {'ident':'incorrect',
         'view':'All'})
        
    flow_mat(elt_itemfeedback, negative_feedback)

    for idx, luuid in enumerate(a_uuids):
        elt_itemfeedback = etree.SubElement(
            elt_item, 'itemfeedback',
            {'ident':luuid, 'view':'All'})
        elt_solution = etree.SubElement(
            itemfeedback, 'solution',
            {'view':'All',
             'feedbackstyle':'Complete'})            
        elt_solutionmaterial = etree.SubElement(
            elt_solution, 'solutionmaterial')
        
        flow_mat(solutionmaterial, '')
        
    print("Added MAQ " + repr(title))
    

class BlackBoardObject:
    pass   
              
class Pool(BlackBoardObject):
    def __init__(
            self,
            pool_name,
            package,
            description  = "",
            instructions = "",
            preview=False,
            test=None,
            points_per_q=10,
            questions_per_test=1
    ):
        """Initialises a question pool
        """
        self.package = package
        self.pool_name = pool_name
        self.question_counter = 0
        self.test = test
        self.points_per_q = points_per_q
        self.questions_per_test = questions_per_test
        
        #Create the question data file
        self.questestinterop = etree.Element("questestinterop")
        assessment = etree.SubElement(self.questestinterop, 'assessment', {'title':self.pool_name})

        self.metadata(assessment, 'Assessment', 'Pool', weight=0)
        
        rubric = etree.SubElement(assessment, 'rubric', {'view':'All'})
        flow_mat = etree.SubElement(rubric, 'flow_mat', {'class':'Block'})
        self.material(flow_mat, instructions)

        presentation_material = etree.SubElement(assessment, 'presentation_material')
        flow_mat = etree.SubElement(presentation_material, 'flow_mat', {'class':'Block'})
        self.material(flow_mat, description)

        self.section = etree.SubElement(assessment, 'section')
        
        self.metadata(self.section, 'Section', 'Pool', weight=0)
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close(self):
        content = '<?xml version="1.0" encoding="UTF-8"?>\n' \
            + etree.tostring(self.questestinterop,
                             pretty_print=False).decode('utf-8')
        
        ref = self.package.embed_resource(self.pool_name, content)

        if self.test is not None:
            self.test.add_pool(self, ref)
             
            
    def addSRQ(self, title, text, answer='', positive_feedback="Good work", negative_feedback="That's not correct", rows=3, maxchars=0):
        # BH: added this, need thorough testing...
        # answers - an optional sample answer
        # rows - number of lines/rows to provide for text entry
        # maxchars - limit the number of characters (0 means no limit)
        
        self.question_counter += 1
        question_id = 'q'+str(self.question_counter)
        #Add the question to the list of questions
        item = etree.SubElement(self.section, 'item', {'title':title, 'maxattempts':'0'})
        md = etree.SubElement(item, 'itemmetadata')
        for key, val in [
                ('bbmd_asi_object_id', '_'+str(self.package.bbid())+'_1'),
                ('bbmd_asitype', 'Item'),
                ('bbmd_assessmenttype', 'Pool'),
                ('bbmd_sectiontype', 'Subsection'),
                ('bbmd_questiontype', 'Short Response'),
                ('bbmd_is_from_cartridge', 'false'),
                ('bbmd_is_disabled', 'false'),
                ('bbmd_negative_points_ind', 'N'),
                ('bbmd_canvas_fullcrdt_ind', 'false'),
                ('bbmd_all_fullcredit_ind', 'false'),
                ('bbmd_numbertype', 'none'),
                ('bbmd_partialcredit', 'false'),
                ('bbmd_orientationtype', 'vertical'),
                ('bbmd_is_extracredit', 'false'),
                ('qmd_absolutescore_max', '-1.0'),
                ('qmd_weighting', '0'),
                ('qmd_instructornotes', ''),
        ]:
            etree.SubElement(md, key).text = val
        
        presentation = etree.SubElement(item, 'presentation')
        flow1 = etree.SubElement(presentation, 'flow', {'class':'Block'})
        flow2 = etree.SubElement(flow1, 'flow', {'class':'QUESTION_BLOCK'})
        flow3 = etree.SubElement(flow2, 'flow', {'class':'FORMATTED_TEXT_BLOCK'})

        bb_question_text, html_question_text = self.package.process_string(text)

        self.material(flow3, bb_question_text)

        flow2 = etree.SubElement(flow1, 'flow', {'class':'RESPONSE_BLOCK'})
        response_str = etree.SubElement(
            flow2,
            'response_str',
            {'ident':'response',
             'rcardinality':'Single',
             'rtiming':'No'}
        )
        render_fib = etree.SubElement(
            response_str, 'render_fib',
            {'charset':'us-ascii',
             'encoding':'UTF_8',
             'rows':'{:d}'.format(rows),
             'columns':'127',
             'maxchars':'{:d}'.format(maxchars),
             'prompt':'Box',
             'fibtype':'String',
             'minnumber':'0',
             'maxnumber':'0'}
        )
            
        resprocessing = etree.SubElement(item, 'resprocessing', {'scoremodel':'SumOfScores'})
        outcomes = etree.SubElement(resprocessing, 'outcomes', {})
        decvar = etree.SubElement(outcomes, 'decvar', {'varname':'SCORE', 'vartype':'Decimal', 'defaultval':'0', 'minvalue':'0'})
        
        respcondition = etree.SubElement(resprocessing, 'respcondition', {'title':'correct'})
        conditionvar = etree.SubElement(respcondition, 'conditionvar')
        etree.SubElement(respcondition, 'setvar', {'variablename':'SCORE', 'action':'Set'}).text = 'SCORE.max'
        etree.SubElement(respcondition, 'displayfeedback', {'linkrefid':'correct', 'feedbacktype':'Response'})
        respcondition = etree.SubElement(resprocessing, 'respcondition', {'title':'incorrect'})
        conditionvar = etree.SubElement(respcondition, 'conditionvar')
        etree.SubElement(conditionvar, 'other')
        etree.SubElement(respcondition, 'setvar', {'variablename':'SCORE', 'action':'Set'}).text = '0'
        etree.SubElement(respcondition, 'displayfeedback', {'linkrefid':'incorrect', 'feedbacktype':'Response'})
        
        itemfeedback = etree.SubElement(item, 'itemfeedback', {'ident':'correct', 'view':'All'})
        bb_pos_feedback_text, html_pos_feedback_text = self.package.process_string(positive_feedback)
        self.flow_mat2(itemfeedback, bb_pos_feedback_text)
        
        itemfeedback = etree.SubElement(item, 'itemfeedback', {'ident':'incorrect', 'view':'All'})
        bb_neg_feedback_text, html_neg_feedback_text = self.package.process_string(negative_feedback)
        self.flow_mat2(itemfeedback, bb_neg_feedback_text)
        
        itemfeedback = etree.SubElement(item, 'itemfeedback', {'ident':'solution', 'view':'All'})
        solution = etree.SubElement(itemfeedback, 'solution', {'view':'All', 'feedbackstyle':'Complete'})
        solutionmaterial = etree.SubElement(solution, 'solutionmaterial')
        flow = etree.SubElement(solutionmaterial, 'flow_mat', {'class':'Block'})
        bb_answer_text, html_answer_text = self.package.process_string(answer)
        self.material(flow,bb_answer_text)
        print("Added SRQ "+repr(title)) ## changed
            
    def addTFQ(self, title, text, istrue=True, positive_feedback="Good work", negative_feedback="That's not correct"):
        # BH: added this, need thorough testing...
        
        self.question_counter += 1
        question_id = 'q'+str(self.question_counter)
        #Add the question to the list of questions
        item = etree.SubElement(self.section, 'item', {'title':title, 'maxattempts':'0'})
        md = etree.SubElement(item, 'itemmetadata')
        for key, val in [
                ('bbmd_asi_object_id', '_'+str(self.package.bbid())+'_1'),
                ('bbmd_asitype', 'Item'),
                ('bbmd_assessmenttype', 'Pool'),
                ('bbmd_sectiontype', 'Subsection'),
                ('bbmd_questiontype', 'True/False'),
                ('bbmd_is_from_cartridge', 'false'),
                ('bbmd_is_disabled', 'false'),
                ('bbmd_negative_points_ind', 'N'),
                ('bbmd_canvas_fullcrdt_ind', 'false'),
                ('bbmd_all_fullcredit_ind', 'false'),
                ('bbmd_numbertype', 'none'),
                ('bbmd_partialcredit', 'false'),
                ('bbmd_orientationtype', 'vertical'),
                ('bbmd_is_extracredit', 'false'),
                ('qmd_absolutescore_max', '-1.0'),
                ('qmd_weighting', '0'),
                ('qmd_instructornotes', ''),
        ]:
            etree.SubElement(md, key).text = val
        
        presentation = etree.SubElement(item, 'presentation')
        flow1 = etree.SubElement(presentation, 'flow', {'class':'Block'})
        flow2 = etree.SubElement(flow1, 'flow', {'class':'QUESTION_BLOCK'})
        flow3 = etree.SubElement(flow2, 'flow', {'class':'FORMATTED_TEXT_BLOCK'})

        bb_question_text, html_question_text = self.package.process_string(text)
#        self.htmlfile += '<li>'+html_question_text+'<ul>'
        self.material(flow3, bb_question_text)

        flow2 = etree.SubElement(flow1, 'flow', {'class':'RESPONSE_BLOCK'})
        response_lid = etree.SubElement(flow2, 'response_lid', {'ident':'response', 'rcardinality':'Single', 'rtiming':'No'})
        render_choice = etree.SubElement(response_lid, 'render_choice', {'shuffle':'No', 'minnumber':'0', 'maxnumber':'0'})
        flow_label = etree.SubElement(render_choice, 'flow_label', {'class':'Block'})
        for response in ['true','false']:
            response_label = etree.SubElement(flow_label, 'response_label', {'ident':response, 'shuffle':'Yes', 'rarea':'Ellipse', 'rrange':'Exact'})
            flow_mat = etree.SubElement(response_label, 'flow_mat', {'class':'Block'})
            material = etree.SubElement(flow_mat, 'material')
            #mattext = etree.SubElement(material, 'mattext', {'charset':'us-ascii', 'texttype':'text/plain', 'xml:space':'default'}).text = response # 'xml:space' is an invalid attribute name, seems okay to omit though
            mattext = etree.SubElement(material, 'mattext', {'charset':'us-ascii', 'texttype':'text/plain'}).text = response
        
        resprocessing = etree.SubElement(item, 'resprocessing', {'scoremodel':'SumOfScores'})
        outcomes = etree.SubElement(resprocessing, 'outcomes', {})
        decvar = etree.SubElement(outcomes, 'decvar', {'varname':'SCORE', 'vartype':'Decimal', 'defaultval':'0', 'minvalue':'0'})
        
        respcondition = etree.SubElement(resprocessing, 'respcondition', {'title':'correct'})
        conditionvar = etree.SubElement(respcondition, 'conditionvar')
        etree.SubElement(conditionvar, 'varequal', {'respident':'response', 'case':'No'}).text = 'true' if istrue else 'false'
        etree.SubElement(respcondition, 'setvar', {'variablename':'SCORE', 'action':'Set'}).text = 'SCORE.max'
        etree.SubElement(respcondition, 'displayfeedback', {'linkrefid':'correct', 'feedbacktype':'Response'})
        respcondition = etree.SubElement(resprocessing, 'respcondition', {'title':'incorrect'})
        conditionvar = etree.SubElement(respcondition, 'conditionvar')
        etree.SubElement(conditionvar, 'other')
        etree.SubElement(respcondition, 'setvar', {'variablename':'SCORE', 'action':'Set'}).text = '0'
        etree.SubElement(respcondition, 'displayfeedback', {'linkrefid':'incorrect', 'feedbacktype':'Response'})
        
        itemfeedback = etree.SubElement(item, 'itemfeedback', {'ident':'correct', 'view':'All'})
        bb_pos_feedback_text, html_pos_feedback_text = self.package.process_string(positive_feedback)
        self.flow_mat2(itemfeedback, bb_pos_feedback_text)
        
        itemfeedback = etree.SubElement(item, 'itemfeedback', {'ident':'incorrect', 'view':'All'})
        bb_neg_feedback_text, html_neg_feedback_text = self.package.process_string(negative_feedback)
        self.flow_mat2(itemfeedback, bb_neg_feedback_text)
                
        print("Added TFQ "+repr(title)) ## changed
    
            
    def flow_mat2(self, node, text):
        flow = etree.SubElement(node, 'flow_mat', {'class':'Block'})
        self.flow_mat1(flow, text)

    def flow_mat1(self, node, text):
        flow = etree.SubElement(node, 'flow_mat', {'class':'FORMATTED_TEXT_BLOCK'})
        self.material(flow, text)
        
class Test(BlackBoardObject):
    def __init__(self, test_name, package, description="Created by BlackboardQuiz!", instructions="", preview=True):
        """Initialises a question pool
        """
        self.package = package
        self.test_name = test_name
        self.preview = preview
        self.question_counter = 0
        
        #Create the question data file
        self.elt_questestinterop = etree.Element("questestinterop")
        elt_assessment = etree.SubElement(
            self.questestinterop, 'assessment',
            {'title': self.test_name})


        ## ??? defaults ???
        metadata(
            self.section, 'Assessment',
            {'bbmd_sectiontype': 'Test',
             'qmd_absolutescore_max': '100'})
        ##
        
        elt_rubric = etree.SubElement(
            elt_assessment, 'rubric',
            {'view':'All'})
    
        flow_mat(elt_rubric, 'Block', instructions)

        elt_presentation_material = etree.SubElement(
            elt_assessment, 'presentation_material')
        flow_mat(elt_presentation_material, 'Block', description)
        

        self.section = etree.SubElement(assessment, 'section')
        metadata(
            self.section, 'Section',
            {'bbmd_sectiontype': 'Test',
             'qmd_absolutescore_max': '20'})
                               
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close(self):

        content_str = '<?xml version="1.0" encoding="UTF-8"?>\n' \
            + etree.tostring(self.questestinterop, pretty_print=False).decode('utf-8')
        
        self.package.embed_resource(
            self.test_name,
            "assessment/x-bb-qti-test",
            content_str)
        

    def add_pool(self, pool, pool_ref):
        subsec = etree.SubElement(self.section, 'section')
        self.metadata(subsec, 'Section', 'Test', sectiontype='Random Block', scoremax=pool.questions_per_test * pool.points_per_q, weight=pool.points_per_q)
        selection_ordering = etree.SubElement(subsec, 'selection_ordering')
        selection = etree.SubElement(selection_ordering, 'selection', {'seltype':'All'})
        etree.SubElement(selection, 'selection_number', {}).text = str(pool.questions_per_test)
        etree.SubElement(selection, 'sourcebank_ref', ).text = pool_ref
        
        

    def createPool(self, pool_name, *args, **kwargs):
        kwargs['test'] = self
        return Pool(pool_name, self.package, *args, **kwargs)
        
class Package:
    def __init__(self, courseID="IMPORT"):
        """Initialises a Blackboard package
        """
        self.courseID = courseID
        self.embedded_files = {}
        try:
            compression = zipfile.ZIP_DEFLATED
        except:
            compression = zipfile.ZIP_STORED
        self.zf = zipfile.ZipFile(self.courseID+'.zip', mode='w', compression=compression)
        self.next_xid = 1000000
        self.equation_counter = 0
        self.resource_counter = 0
        self.embedded_paths = {}
        #Create the manifest file
        self.xmlNS = "http://www.w3.org/XML/1998/namespace"
        self.bbNS = 'http://www.blackboard.com/content-packaging/'
        self.manifest = etree.Element("manifest", {'identifier':'man00001'}, nsmap={'bb':self.bbNS})
        organisations = etree.SubElement(self.manifest, "organizations")
        self.resources = etree.SubElement(self.manifest, 'resources')

        self.idcntr = 3191882
        self.latex_kwargs = dict()
        self.latex_cache = {}
        
    def bbid(self):
        self.idcntr += 1
        return self.idcntr

    
    def close(self):
        #Write additional data to implement the course name
        parentContext = etree.Element("parentContextInfo")
        etree.SubElement(parentContext, "parentContextId").text = self.courseID
        self.embed_resource(self.courseID, "resource/x-mhhe-course-cx", '<?xml version="1.0" encoding="utf-8"?>\n'+etree.tostring(parentContext, pretty_print=False).decode('utf-8'))

        #Finally, write the manifest file
        self.zf.writestr('imsmanifest.xml', '<?xml version="1.0" encoding="utf-8"?>\n'+etree.tostring(self.manifest, pretty_print=False).decode('utf-8'))
        self.zf.writestr('.bb-package-info', BBKPGINFO)
        self.zf.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def createTest(self, test_name, *args, **kwargs):
        return Test(test_name, self, *args, **kwargs)

    def createPool(self, pool_name, *args, **kwargs):
        return Pool(pool_name, self, *args, **kwargs)

    def embed_resource(self, title, type, content):
        self.resource_counter += 1
        name = 'res'+format(self.resource_counter, '05')
        resource = etree.SubElement(self.resources, 'resource', {'identifier':name, 'type':type})
        resource.attrib[etree.QName(self.xmlNS, 'base')] = name
        resource.attrib[etree.QName(self.bbNS, 'file')] = name+'.dat'
        resource.attrib[etree.QName(self.bbNS, 'title')] = title
        self.zf.writestr(name+'.dat', content)
        return name
        
    def embed_file_data(self, name, content):
        """Embeds a file (given a name and content) to the quiz and returns the
        unique id of the file, and the path to the file in the zip
        """                

        #First, we need to process the path of the file, and embed xid
        #descriptors for each directory/subdirectory
        
        #Split the name into filename and path
        path, filename = os.path.split(name)

        #Simplify the path (remove any ./ items and simplify ../ items to come at the start)
        if (path != ""):
            path = os.path.relpath(path)
        
        #Split the path up into its components
        def rec_split(s):
            rest, tail = os.path.split(s)
            if rest in ('', os.path.sep):
                return [tail]
            return rec_split(s) + [tail]

        path = rec_split(path)
        root, ext = os.path.splitext(filename)

        def processDirectories(path, embedded_paths, i=0):
            #Keep processing until the whole path is processed
            if i >= len(path):
                return path

            #Slice any useless entries from the path
            if i==0 and (path[0] == ".." or path[0] == '/' or path[0] == ''):
                path = path[1:]
                return processDirectories(path, embedded_paths, i)

            #Check if the path is already processed
            if path[i] in embedded_paths:
                new_e_paths = embedded_paths[path[i]][1]
                path[i] = embedded_paths[path[i]][0]
            else:
                #Path not processed, add it
                descriptor_node = etree.Element("lom") #attrib = {'xmlns':, 'xmlns:xsi':'http://www.w3.org/2001/XMLSchema-instance', 'xsi:schemaLocation':'http://www.imsglobal.org/xsd/imsmd_rootv1p2p1 imsmd_rootv1p2p1.xsd'}
                relation = etree.SubElement(descriptor_node, 'relation')
                resource = etree.SubElement(relation, 'resource')

                self.next_xid += 1
                transformed_path = path[i]+'__xid-'+str(self.next_xid)+'_1'
                etree.SubElement(resource, 'identifier').text = str(self.next_xid)+'_1' + '#' + '/courses/'+self.courseID+'/' + os.path.join(*(path[:i+1]))
                embedded_paths[path[i]] = [transformed_path, {}]
                new_e_paths = embedded_paths[path[i]][1]

                path[i] = transformed_path
                
                self.zf.writestr(os.path.join('csfiles/home_dir', *(path[:i+1]))+'.xml', '<?xml version="1.0" encoding="UTF-8"?>\n'+etree.tostring(descriptor_node, pretty_print=False).decode('utf-8'))

            return processDirectories(path, new_e_paths, i+1)

        processDirectories(path, self.embedded_paths)
        
        #Finally, assign a xid to the file itself
        self.next_xid += 1
        filename = root + '__xid-'+str(self.next_xid)+'_1' + ext

        #Merge the path pieces and filename
        path = path + [filename]
        path = os.path.join(*path)
        filepath = os.path.join('csfiles/home_dir/', path)
        self.zf.writestr(filepath, content)
        
        descriptor_node = etree.Element("lom") #attrib = {'xmlns':, 'xmlns:xsi':'http://www.w3.org/2001/XMLSchema-instance', 'xsi:schemaLocation':'http://www.imsglobal.org/xsd/imsmd_rootv1p2p1 imsmd_rootv1p2p1.xsd'}
        relation = etree.SubElement(descriptor_node, 'relation')
        resource = etree.SubElement(relation, 'resource')
        etree.SubElement(resource, 'identifier').text = str(self.next_xid) + '#' + '/courses/'+self.courseID+'/'+path
        self.zf.writestr(filepath+'.xml', '<?xml version="1.0" encoding="UTF-8"?>\n'+etree.tostring(descriptor_node, pretty_print=False).decode('utf-8'))
        return str(self.next_xid)+'_1', filepath

    def embed_file(self, filename, file_data=None, attrib={}):
        """Embeds a file, and returns an img tag for use in blackboard, and an equivalent for html.
        """
        #Grab the file data
        if file_data == None:
            with open(filename, mode='rb') as file:
                file_data = file.read()
            
        #Check if this file has already been embedded
        if filename not in  self.embedded_files:
            xid, path = self.embed_file_data(filename, file_data)
            self.embedded_files[filename] = (xid, path)
            return xid, path
            
        #Hmm something already exists with that name, check the data
        xid, path = self.embedded_files[filename]
        fz = self.zf.open(path)
        if file_data == fz.read():
            #It is the same file! return the existing link
            return xid, path
        fz.close()
        
        #Try generating a new filename, checking if that already exists in the store too
        count=-1
        fbase, ext = os.path.splitext(filename)
        while True:
            count += 1 
            fname = fbase + '_'+str(count)+ext
            if fname in self.embedded_files:
                xid, path = self.embedded_files[fname]
                fz = self.zf.open(path)
                if file_data == fz.read():
                    return xid, path
                else:
                    continue
            break
        #OK we have a new unique name, fname. Use this to embed the file
        xid, path = self.embed_file_data(fname, file_data)
        self.embedded_files[fname] = (xid, path)
        return xid, path
        

    def process_string(self, in_string):
        return in_string, in_string

