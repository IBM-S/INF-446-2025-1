#/bin/bash

instanceList=$(ls *.dat)


for instance in ${instanceList}; do
    echo "$instance"
    python3 cleaner.py ${instance} ${instance}_clear

done
