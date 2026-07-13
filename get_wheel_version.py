import re
import sys

full_name = sys.argv[1]

pattern = r'(.*)-(\d+\.\d+\.\d+)-(.*)-(.*)-(.*).whl'

match = re.search(pattern, full_name)

print(match.group(2))
