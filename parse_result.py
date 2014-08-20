import sys
from lxml import etree as ET

def filter_by_tests(doc, value_list = ["process-returncode"]):
    elem = doc.xpath("/testsuite/testcase[@name='process-returncode']")
    root = doc.getroot()
    tests = int(root.get('tests'))
    failures = int(root.get('failures'))
    for el in elem:
        root.remove(el)
        tests -= 1
        failures -= 1
    root.set('failures',str(failures))
    root.set('tests',str(tests))
    return doc

def write_to_a_file(file):
    with open(file, 'w') as the_file:
        the_file.write(ET.tostring(doc))

files = sys.argv[1:] 
for file in files:
    doc = ET.parse(file)
    filter_by_tests(doc)
    write_to_a_file(file)

