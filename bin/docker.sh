#!/bin/bash -e
version=${1:?Set version as argument for docker building}

docker build -t scrapper:${version} .