#!/bin/bash -e

echo "#########################################################################################"
printf  "\n---> sourcing venv"
source venv/bin/activate
printf " venv activated <---\n"
echo "#########################################################################################"
printf "\n---> building package file"
python setup.py sdist
printf "building package file <---\n"
echo "#########################################################################################"
printf "\n---> locating package files in target folder"
mkdir -p target
mv dist/scraper-*.tar.gz target/scraper.tar.gz
cp requirements.txt target/requirements.txt
cp -p bin/scrapper.sh target/scrapper.sh
printf "locating package files in target folder <---\n"
echo "#########################################################################################"
