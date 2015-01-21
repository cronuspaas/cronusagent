#pylint: disable=W0622,W0105

""" agent lib """
import os, re, sys

import logging
LOG = logging.getLogger(__name__)

# library paths
LIB = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'lib')
for entry in os.listdir(LIB):
    file = os.path.join(LIB, entry)
    if os.path.exists(file) and re.search(r".*\.(zip|egg|tar\.gz|tgz)$", file):
        LOG.info("...appending library %s to sys.path" % file)
        sys.path.append(file)
