#!/bin/python
import csv
import getopt
import json
import logging
import os
import sys
from datetime import datetime

# {
#     "media": "",
#     "begin": "",
#     "end": "",
#     "resultsPath": ""
#     "news_file": ""
# }
from scraper.customScrappers.ABCSimpleScrapper import ABCSimpleScrapper
from scraper.customScrappers.ElMundoSimpleScrapper import ElMundoSimpleScrapper
from scraper.customScrappers.ElPaisSimpleScrapper import ElPaisSimpleScrapper
from scraper.customScrappers.LaVanguardiaSimpleScrapper import LaVanguardiaSimpleScrapper
from scraper.customScrappers.VeinteMinutosSimpleScrapper import VeinteMinutosSimpleScrapper

SUPPORTED_MEDIA = ["abc", "elmundo", "elpais", "20minutos", "lavanguardia"]
logging.basicConfig(level=logging.INFO)


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

def _create_results_media_path(results_path, media):
    media_results_path = os.path.join(results_path, media)
    if os.path.isdir(media_results_path):
        logging.info(" {} results media path exists".format(media_results_path))
    else:
        try:
            os.mkdir(media_results_path)
        except FileExistsError:
            logging.info(" {} results media path exists".format(media_results_path))
        except Exception as e:
            logging.error(" something went wrong trying to create results path for media: {}".format(media))
            logging.error(str(e))
            sys.exit(-1)
    return media_results_path


def get_opts(argv):
    config_file = None
    begin = None
    end = None
    media = None
    results_path = None
    config_obj = None

    try:
        opts, args = getopt.getopt(argv, "hc:b:e:m:r:", ["config=", "begin=", "end=", "media=", "resultsPath="])
    except getopt.GetoptError:
        print(
            'scrapper.py -b 01/01/2019 -e 31/01/2019 -m [elmundo|elpais|abc|20minutos|lavanguardia] -r <results_path>')
        print('scrapper.py -c <config_file>')
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            print(
                'scrapper.py -b 01/01/2019 -e 31/01/2019 -m [elmundo|elpais|abc|20minutos|lavanguardia] -r <results_path>')
            print('scrapper.py -c <config_file>')
            sys.exit()
        elif opt in ["-c", "--config"]:
            config_file = arg
        elif opt in ["-b", "--begin"]:
            begin = arg
        elif opt in ["-e", "--end"]:
            end = arg
        elif opt in ["-m", "--media"]:
            media = arg
        elif opt in ["-r", "--resultsPath"]:
            results_path = arg

    logging.info("config_file found: {}".format(config_file))
    logging.info("begin found: {}".format(begin))
    logging.info("end found: {}".format(end))
    logging.info("media found: {}".format(media))
    logging.info("result_path found: {}".format(results_path))

    if config_file:
        with open(config_file, 'r') as file:
            config_obj = json.load(file)
    else:
        if isValidDate(begin) and isValidDate(end) and media in SUPPORTED_MEDIA and os.path.isdir(results_path):
            media_results = _create_results_media_path(results_path, media)
            logging.info(" results path created: {}".format(media_results))
            config_obj = {
                "media": media,
                "begin": begin,
                "end": end,
                "resultsPath": results_path
            }
        else:
            logging.error(" something is wrong with argumnets, it  has been detected that some of them are invalid")
            config_obj = None

    return config_obj


def isValidDate(dateStr):
    isValid = False
    try:
        d = datetime.strptime(dateStr, "%d/%m/%Y")
        logging.info(" {} is formatted correctly".format(dateStr))
        isValid = True
    except Exception as e:
        logging.error(" {} is not formatted correctly".format(dateStr))
        logging.error(" an correct example looks like: 01/01/2019 (day/month/year)")
        logging.error(str(e))
        isValid = False

    return isValid


def main(argv):
    # config_file = get_opts(argv)
    config_obj = get_opts(argv)
    scrapper = None
    if config_obj:
        media = config_obj["media"]
        if media == "abc":
            scrapper = ABCSimpleScrapper()
        elif media == "elmundo":
            scrapper = ElMundoSimpleScrapper()
        elif media == "elpais":
            scrapper = ElPaisSimpleScrapper()
        elif media == "20minutos":
            scrapper = VeinteMinutosSimpleScrapper()
        elif media == "lavanguardia":
            scrapper = LaVanguardiaSimpleScrapper()
        else:
            logging.error("{} media is not supported".format(media))
            sys.exit(-1)

        # assuming the date is set in correct format
        try:
            scrapper.initialize(begin=config_obj["begin"], end=config_obj["end"], rootPath=config_obj["resultsPath"])
            comments_file, contents_file = unify(config_obj["begin"], config_obj["end"], config_obj["media"],
                                                 config_obj["resultsPath"], scrapper)
            print(" Final comments file generated: - {} -".format(comments_file))
            print(" Final contents file generated: - {} -".format(contents_file))
            logging.info(" Final comments file generated: - {} -".format(comments_file))
            logging.info(" Final contents file generated: - {} -".format(contents_file))
        except Exception as e:
            logging.error("Execution has failed...")
            e.with_traceback()
            logging.error(str(e))
    else:
        print(" Something went wrong trying to parse arguments, check logs.")
        sys.exit(-1)


if __name__ == "__main__":
    main(sys.argv[1:])
