
# dealing with the fixture imports

import sys
import os


# While in development run tests off of dev code vs packaged code
devPath = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
print(f'devPath: {devPath}')
sys.path.insert(0, devPath)

from tests.fixtures.bcdc_fixtures import *
