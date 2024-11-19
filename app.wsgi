import sys
import os

sys.path.insert(0, '/var/www/pnpserver')
os.chdir('/var/www/pnpserver')

from main import app as application