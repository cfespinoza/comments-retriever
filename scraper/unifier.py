import csv
import json
import os

from scraper.customScrappers.LaVanguardiaSimpleScrapper import LaVanguardiaSimpleScrapper
from scraper.customScrappers.ABCSimpleScrapper import ABCSimpleScrapper
from scraper.customScrappers.ElMundoSimpleScrapper import ElMundoSimpleScrapper
from scraper.customScrappers.ElPaisSimpleScrapper import ElPaisSimpleScrapper
from scraper.customScrappers.VeinteMinutosSimpleScrapper import VeinteMinutosSimpleScrapper

############################ commons params ######################################################
# resultPath = "/home/cflores/cflores_workspace/comments-retriever/results"
# begin = "01/01/2019"
# end = "15/09/2019"
##################################################################################################

#######################################  20minutos ###############################################
# scrapper = VeinteMinutosSimpleScrapper()
# media = "20minutos"
# dateFormat = "%Y-%m-%-d"
##################################################################################################

########################################  ElMundo ################################################
# scrapper = ElMundoSimpleScrapper()
# media = "elmundo"
# dateFormat = "%Y-%m-%d"
##################################################################################################

########################################  ElPais ################################################
# scrapper = ElPaisSimpleScrapper()
# media = "elpais"
# dateFormat = "%Y-%m-%d"
##################################################################################################

##########################################  ABC ##################################################
# scrapper = ABCSimpleScrapper()
# media = "abc"
# dateFormat = "%d-%m-%Y"
##################################################################################################

#####################################  LaVanguardia ##############################################
# scrapper = LaVanguardiaSimpleScrapper()
# media = "lavanguardia"
# dateFormat = "%Y%m%d"
##################################################################################################

DATE_FORMATS = {
    "20minutos": "%Y-%m-%-d",
    "elmundo": "%Y-%m-%d",
    "elpais": "%Y-%m-%d",
    "abc": "%d-%m-%Y",
    "lavanguardia": "%Y%m%d"
}


def export(fileName, data):
    with open(fileName, "w") as file:
        csvwriter = csv.writer(file)
        count = 0
        for dataObj in data:
            if count == 0:
                header = dataObj.keys()
                csvwriter.writerow(header)
                count += 1
            csvwriter.writerow(dataObj.values())


def loadJsons(files):
    all = []
    for f in files:
        if os.path.isfile(f):
            with open(f) as file:
                all = all + json.load(file)
        else:
            print(" \t -> file -{}- not found.".format(f))
    return all


def unify(begin, end, media, resultPath, scrapper):
    date_format = DATE_FORMATS[media]
    dates = scrapper.generateDates(start=begin, end=end, dateFormat=date_format)
    period = "{}-{}".format(begin.replace("/", ""), end.replace("/", ""))

    commentsFilesNames = ["{rootPath}/{media}/{date}-comments.json".format(rootPath=resultPath, media=media, date=d) for
                          d in dates]
    contentsFilesNames = ["{rootPath}/{media}/{date}-contents.json".format(rootPath=resultPath, media=media, date=d) for
                          d in dates]

    totalCommentsArr = loadJsons(commentsFilesNames)
    totalContentsArr = loadJsons(contentsFilesNames)

    comments_file_unified = "{rootPath}/{media}/{media}-{period}-comments.csv".format(rootPath=resultPath, media=media,
                                                                                      period=period)
    contents_file_unified = "{rootPath}/{media}/{media}-{period}-contents.csv".format(rootPath=resultPath, media=media,
                                                                                      period=period)
    export(comments_file_unified, totalCommentsArr)
    export(contents_file_unified, totalContentsArr)

    return comments_file_unified, contents_file_unified
