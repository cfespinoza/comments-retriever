import json
import logging
import sys, getopt

from scraper.customScrappers.LaVanguardiaSimpleScrapper import LaVanguardiaSimpleScrapper
from scraper.customScrappers.ElMundoSimpleScrapper import ElMundoSimpleScrapper
from scraper.customScrappers.ABCSimpleScrapper import ABCSimpleScrapper
from scraper.customScrappers.ElPaisSimpleScrapper import ElPaisSimpleScrapper
from scraper.customScrappers.VeinteMinutosSimpleScrapper import VeinteMinutosSimpleScrapper

# {
#     "media": "",
#     "begin": "",
#     "end": "",
#     "resultsPath": ""
#     "news_file": ""
# }

def get_opts(argv):
    config_file = ''
    try:
        opts, args = getopt.getopt(argv, "hc:", ["config="])
    except getopt.GetoptError:
        print('scrapper.py -c <config_file>')
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            print('scrapper.py -c <config_file>')
            sys.exit()
        elif opt in ["-c", "--config"]:
            config_file = arg
    logging.info("config_file path is {}".format(config_file))
    return config_file

def main(argv):
    config_file = get_opts(argv)
    config_obj = json.loads(config_file)
    scrapper = None
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

    # TODO call to start scrapping

if __name__ == "__main__":
    main(sys.argv[1:])
