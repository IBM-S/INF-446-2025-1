import sys

with open(sys.argv[1]) as result:
        uniqlines = set(result.readlines())
        with open(sys.argv[2], 'w') as rmdup:
            rmdup.writelines(set(uniqlines))
