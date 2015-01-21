import re
import json
from nested_dict import *
from optparse import OptionParser # Deprecated since version 2.7

class createConfig():
    ''' class to create config file based on template'''
    def __init__(self):
        ''' constructor '''
        pass

    @staticmethod
    def create(tmplFileName, iniFileName, dict):
        ''' create config file'''
        with open(tmplFileName, 'r') as tmplFile:
            with open(iniFileName, 'w') as iniFile:
                section = ""
                for line in tmplFile:
                    m = re.match(r'^\[\s*(?P<section>\S*)\s*\](\s*$|\s*#.*)', line)
                    if m:
                        section = m.group('section')
                    elif section in dict:
                        for key in dict[section]:
                            m = re.match(r'\s*(?P<key>\w[\S|\s]*\S)\s*=\s*(?P<value>[\S| ]*\S)(\s*$|\s*#.*)', line)
                            if m and str(key) == m.group('key'):
                                if None == dict[section][key]:
                                    line = '\n'
                                else:
                                    line = '%s = %s\n' %(str(key), str(dict[section][key]))
                                break

                    iniFile.write(line)

def make_config():
    ''' make four config file base on tmpl.ini'''
    # parse command line
    usage = 'usage: %prog [options] component'
    parser = OptionParser(usage=usage)
    parser.add_option('-f', '--file', dest='file', default='conf/iniChanges.json',
                      help='override json file')
    parser.add_option('-t', '--template', dest='template', default='conf/tmpl.ini',
                      help='template configuration file')
    parser.add_option('-d', '--dest', dest='destination', default='conf',
                      help='destination folder')
    (options, args) = parser.parse_args()

    if len(args) < 1:
        parser.print_usage()
        exit(1)

    component = args[0]
    fext = options.template.rsplit('.', 1)[-1]

    with open(options.file, 'r') as f:
        configDict = json.loads(f.read())
        
        for env, settings in configDict[component].items():
            iniFilename = '%s/%s.%s' % (options.destination, env, fext)
            createConfig.create(options.template, iniFilename, settings)

if __name__ == '__main__':
    make_config()
