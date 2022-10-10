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
        'qmd_weighting' : '0',
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
    

class BlackBoardObject:
    pass   
                          
        
class Test(BlackBoardObject):
    def __init__(
            self,
            test_name,
            package,
            description = "",
            instructions=""):
  
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
             'qmd_absolutescore_max': '100.00'})
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
             'qmd_absolutescore_max': '100.00'})
                               
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close(self):

        content_str = '<?xml version="1.0" encoding="UTF-8"?>\n' \
            + etree.tostring(self.questestinterop,
                             pretty_print=False).decode('utf-8')
        
        self.package.embed_resource(
            self.test_name,
            "assessment/x-bb-qti-test",
            content_str)
        
        
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
        self.zf = zipfile.ZipFile(
            self.courseID+'.zip',
            mode='w',
            compression=compression)
        self.next_xid = 1000000
        self.equation_counter = 0
        self.resource_counter = 0
        self.embedded_paths = {}
        #Create the manifest file
        self.xmlNS = "http://www.w3.org/XML/1998/namespace"
        self.bbNS = 'http://www.blackboard.com/content-packaging/'
        self.manifest = etree.Element(
            "manifest",
            {'identifier':'man00001'},
            nsmap={'bb':self.bbNS})
        organisations = etree.SubElement(
            self.manifest, "organizations")
        self.resources = etree.SubElement(
            self.manifest, 'resources')

        self.idcntr = 3191882
        self.latex_kwargs = dict()
        self.latex_cache = {}
        
    def bbid(self):
        self.idcntr += 1
        return self.idcntr

    
    def close(self):
        elt_parentContext = etree.Element("parentContextInfo")
        etree.SubElement(
            elt_parentContext, "parentContextId").text = self.courseID

        resource_content = '<?xml version="1.0" encoding="utf-8"?>\n'\
            + etree.tostring(parentContext,
                             pretty_print=False).decode('utf-8')

        self.embed_resource(
            self.courseID, "resource/x-mhhe-course-cx",
            resource_content)

        #Finally, write the manifest file
        manifest  =  '<?xml version="1.0" encoding="utf-8"?>\n'\
            + etree.tostring(self.manifest,
                             pretty_print=False).decode('utf-8')
        self.zf.writestr('imsmanifest.xml', manifest)
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

    def embed_resource(self, title, typename, content):
        self.resource_counter += 1
        name = 'res' + format(self.resource_counter, '05')
        resource = etree.SubElement(
            self.resources, 'resource',
            {'identifier' : name,
             'type' : typename})
        resource.attrib[etree.QName(self.xmlNS, 'base')] = name
        resource.attrib[etree.QName(self.bbNS,  'file')] = name + '.dat'
        resource.attrib[etree.QName(self.bbNS, 'title')] = title
        self.zf.writestr(name + '.dat', content)
        return name
        

