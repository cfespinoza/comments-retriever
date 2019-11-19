import argparse
import getopt
import json
import logging
import os
import sys
from datetime import datetime

from scraper.customScrappers.ABCSimpleScrapper import ABCSimpleScrapper
from scraper.customScrappers.ElMundoSimpleScrapper import ElMundoSimpleScrapper
from scraper.customScrappers.ElPaisSimpleScrapper import ElPaisSimpleScrapper
from scraper.customScrappers.LaVanguardiaSimpleScrapper import LaVanguardiaSimpleScrapper
from scraper.customScrappers.VeinteMinutosSimpleScrapper import VeinteMinutosSimpleScrapper
from scraper.unifier import unify

SUPPORTED_MEDIA = ["abc", "elmundo", "elpais", "20minutos", "lavanguardia"]


def _create_results_media_path(results_path, media, LOGGER):
    today = datetime.now().strftime("%d-%m-%Y")
    result_root_path = os.path.join(results_path, today)
    media_results_path = os.path.join(result_root_path, media)
    if os.path.isdir(media_results_path):
        LOGGER.info(" {} results media path exists".format(media_results_path))
    else:
        try:
            os.makedirs(media_results_path)
        except FileExistsError:
            LOGGER.info(" {} results media path exists".format(media_results_path))
        except Exception as e:
            LOGGER.error(" something went wrong trying to create results path for media: {}".format(media))
            LOGGER.error(str(e))
            sys.exit(-1)
    return result_root_path


def get_config_obj(config_file=None, begin=None, end=None, media=None, results_path=None, LOGGER=None):
    config_obj = None
    LOGGER.info("config_file found: {}".format(config_file))
    LOGGER.info("begin found: {}".format(begin))
    LOGGER.info("end found: {}".format(end))
    LOGGER.info("media found: {}".format(media))
    LOGGER.info("result_path found: {}".format(results_path))

    if config_file:
        with open(config_file, 'r') as file:
            config_obj = json.load(file)
    else:
        if isValidDate(begin, LOGGER) and isValidDate(end, LOGGER) and media in SUPPORTED_MEDIA and os.path.isdir(results_path):
            media_results = _create_results_media_path(results_path, media, LOGGER)
            LOGGER.info(" results path created: {}".format(media_results))
            config_obj = {
                "media": media,
                "begin": begin,
                "end": end,
                "resultsPath": media_results
            }
        else:
            LOGGER.error(" something is wrong with argumnets, it  has been detected that some of them are invalid")
            config_obj = None

    return config_obj


def get_opts(argv):
    config_file = None
    begin = None
    end = None
    media = None
    results_path = None

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
                'scrapper.py -b 01/01/2019 -e 31/01/2019 -m [elmundo|elpais|abc|20minutos|lavanguardia] -r '
                '<results_path>')
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

    return get_config_obj(config_file, begin, end, media, results_path)


def isValidDate(dateStr, LOGGER):
    isValid = False
    try:
        d = datetime.strptime(dateStr, "%d/%m/%Y")
        LOGGER.info(" {} is formatted correctly".format(dateStr))
        isValid = True
    except Exception as e:
        LOGGER.error(" {} is not formatted correctly".format(dateStr))
        LOGGER.error(" an correct example looks like: 01/01/2019 (day/month/year)")
        LOGGER.error(str(e))
        isValid = False

    return isValid


def execute(config_obj=None, LOGGER=None):
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
            LOGGER.error("{} media is not supported".format(media))
            sys.exit(-1)

        # assuming the date is set in correct format
        try:
            scrapper.initialize(begin=config_obj["begin"], end=config_obj["end"], rootPath=config_obj["resultsPath"])
            comments_file, contents_file = unify(config_obj["begin"], config_obj["end"], config_obj["media"],
                                                 config_obj["resultsPath"], scrapper)
            print(" Final comments file generated: - {} -".format(comments_file))
            print(" Final contents file generated: - {} -".format(contents_file))
            LOGGER.info(" Final comments file generated: - {} -".format(comments_file))
            LOGGER.info(" Final contents file generated: - {} -".format(contents_file))
            LOGGER.info("scrapping process has finished sucessfully")
        except Exception as e:
            LOGGER.error("Execution has failed...")
            e.with_traceback()
            LOGGER.error(str(e))
    else:
        print(" Something went wrong trying to parse arguments, check logs.")
        sys.exit(-1)


def _main(argv):
    # config_file = get_opts(argv)
    config_obj = get_opts(argv)
    LOGGER = get_logger(config_obj)
    execute(config_obj, LOGGER)


def get_logger(config):
    begin_prefix = config["begin"].replace("/", "")
    end_prefix = config["end"].replace("/", "")
    today = datetime.now().strftime("%d%m%Y")
    log_file_name = "{today}-{media}-{init}-{end}.log".format(today=today, media=config["media"], init=begin_prefix, end=end_prefix)
    log_file = os.path.join(config["results_path"], log_file_name)
    print("\t -> log file: {}".format(log_file))
    logging.basicConfig(filename=log_file,
                        level=logging.DEBUG,
                        datefmt="%d-%m-%Y %H:%M:%S",
                        format="[%(asctime)s] [%(levelname)8s] --- %(message)s (%(filename)s:%(lineno)d)")

    return logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        prog='Scrapper',
        usage='scrapper -b 01/01/2019 -e 31/01/2019 -m [elmundo|elpais|abc|20minutos|lavanguardia] -r <results_path>'
    )

    parser.add_argument('-b', '--begin', nargs='?', help='begin date of period to retrieve commments and contents')
    parser.add_argument('-e', '--end', nargs='?', help='end date of period to retrieve commments and contents')
    parser.add_argument('-m', '--media', nargs='?', help='media where comments and contents will be retrieved from')
    parser.add_argument('-r', '--results_path', nargs='?', help='local path where result will be stored. the program '
                                                                'will create folder for each media')

    args = parser.parse_args()

    collected_inputs = {
        'begin': args.begin,
        'end': args.end,
        'media': args.media,
        'results_path': args.results_path
    }

    LOGGER = get_logger(collected_inputs)
    collected_inputs["LOGGER"] = LOGGER
    config_obj = get_config_obj(**collected_inputs)
    execute(config_obj, LOGGER)


if __name__ == "__main__":
    _main(sys.argv[1:])
