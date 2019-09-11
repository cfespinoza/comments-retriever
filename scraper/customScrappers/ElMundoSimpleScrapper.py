import json
import logging
import sys
import time
from datetime import date, datetime
from json import JSONDecodeError

import requests

from scraper.SimpleBasicScrapper import SimpleScrapper


class ElMundoSimpleScrapper(SimpleScrapper):

    def __init__(self):
        super().__init__()
        self.urlGetComments = "https://www.elmundo.es/servicios/noticias/scroll/comentarios/comunidad/listar.html"
        self._urlXpathQuery = "//a/@href"

    def initialize(self, begin="01/01/2019", end="31/08/2019", rootPath=None):
        extraInfoHemeroteca = self.generateHemerotecaExtraInfo()
        logging.basicConfig(filename="{}-{}.log".format("elmundo", datetime.today().strftime("%d%m%Y-%H%M%S")),
                            level=logging.INFO)
        self.start("https://www.elmundo.es/elmundo/hemeroteca/{date}/{partOfDay}.html", "elmundo", begin, end, rootPath,
                   "%Y/%m/%d", extraInfoHemeroteca)

    def generateDates(self, start="", end="", delta=1, dateFormat="%Y/%m/%d"):
        # dateFormat = "%Y/%m/%d"
        # initDateStr = "01/01/2019"
        # endDateStr = "01/01/2019"
        self._period = "{}-{}".format(start.replace("/", ""), end.replace("/", ""))

        initDateArr = start.split("/")
        endDateArr = end.split("/")

        initDateArr.reverse()
        endDateArr.reverse()

        datesBase = self._generateDates(
            date(int(initDateArr[0]), int(initDateArr[1]), int(initDateArr[2])),
            date(int(endDateArr[0]), int(endDateArr[1]), int(endDateArr[2])),
            strFormat=dateFormat)
        return datesBase

    def generateHemerotecaUrls(self, urlBase=None, dates=None, extraInfo=None):
        # https://www.elmundo.es/elmundo/hemeroteca/2019/01/01/m/economia.html
        urlsPerDay = {}
        logging.info(" \t Url-Base: {}".format(urlBase))
        for d in dates:
            partOfDayUrls = [urlBase.format(date=d, partOfDay=p) for p in extraInfo]
            urlsPerDay[d] = partOfDayUrls
        logging.info(" \t -> urlsPerDay length: {}".format(len(urlsPerDay)))
        return urlsPerDay

    def filterUrls(self, links=[], urlBase="https://www.elmundo.es{}"):
        filteredLinks = list(dict.fromkeys([link for link in links
                                            if "elmundo" in link
                                            and "#ancla_comentarios" not in link
                                            and "logo_home" not in link
                                            and "intcmp" not in link
                                            and "menu.html" not in link
                                            and "cgi.elmundo.es" not in link
                                            and "follow=1" not in link
                                            and "?autoplay=true" not in link
                                            and "mailto:?subject" not in link
                                            and ".pdf" not in link
                                            and self._currentDateKey in link]))
        return filteredLinks

    def extractComments(self, commentsList=None, urlNoticia=None, specialCase=None):
        logging.info(" \t -> parsing comments list with -{}- elements:".format(len(commentsList)))
        parsedComments = []
        listToParse = commentsList[1] if specialCase and len(commentsList) > 1 else commentsList
        for commentObj in listToParse:
            parsedComment = {
                "urlNoticia": urlNoticia,
                "fecha": commentObj['date'],
                "hora": commentObj['time'],
                "user": commentObj['user'],
                "commentario": commentObj['body'],
                "order": commentObj["order"]
            }
            parsedComments.append(parsedComment)
        return parsedComments

    def extractContent(self, renderedPage=None, url=None):
        commentsElList = renderedPage.xpath("//div[@data-section='articleBody']//p")
        contentArr = []
        for p in commentsElList:
            contentArr.append(p.text_content())
        contentStr = "".join([parrafo for parrafo in contentArr])
        content = {
            "url": url,
            "content": contentStr
        }
        return [content]

    def lookupForComments(self, renderedPageHtml=None, url=None):
        totalComentarioElList = renderedPageHtml.find_class("js-ueCommentsCounter")  # find("js-ueCommentsCounter")
        pageComments = []
        if (len(totalComentarioElList) > 0):
            totalComentarioEl = totalComentarioElList[0]
            idNoticia = int(totalComentarioEl.get("data-commentid"))
            logging.info(" \t idNoticia found: {}".format(idNoticia))
            params = {"noticia": idNoticia, "version": "v2"}
            response = requests.get(self.urlGetComments, params)
            if response.status_code != 200:
                logging.error(" \t something when wrong retrieving comments from idNoticia {}".format(idNoticia))
                logging.info(" \t retrieving comments from idNoticia {} return status_code {}".format(idNoticia, response.status_code))
                time.sleep(5)
                response = requests.get(self.urlGetComments, params)
            responseDecoded = {}
            try:
                responseDecoded = json.loads(response.text)
            except JSONDecodeError as e:
                logging.error(str(e))

            logging.debug(responseDecoded)
            iterate = responseDecoded["lastPage"]
            total = responseDecoded["total"]
            logging.info(" -> retrieved total of comments: {}".format(total))
            if (total > 0):
                pageComments = self.extractComments(responseDecoded['items'], url)
                while not iterate:
                    logging.info(" - iterating...")
                    logging.info(" -> total of comments: {}".format(len(pageComments)))
                    nextComments = total - len(pageComments)
                    specialCase = False
                    if (nextComments == 1):
                        logging.info(" -> special case, adding extra value in order to avoid wrong behaviour")
                        specialCase = True
                        nextComments = nextComments + 1
                    logging.info(" -> next pagina: {}".format(nextComments))
                    params = {"noticia": idNoticia, "version": "v2", "pagina": nextComments}
                    response = requests.get(self.urlGetComments, params)
                    responseDecoded = json.loads(response.text)
                    pageComments = pageComments + self.extractComments(responseDecoded['items'], url, specialCase)
                    iterate = responseDecoded["lastPage"]
                    logging.info(
                        "---------------------------------------------------------------------------------------------")
                logging.info(" \t -> retrieved total of {} comments".format(len(pageComments)))
                logging.info("#############################################################################################")
        else:
            logging.warning(" \t -> there is something wrong due to commentsEl has not been found")
        return pageComments

    def generateHemerotecaExtraInfo(self):
        partOfDay = ["m", "t", "n"]
        sections = ['espana',
                    "index",
                    'madrid',
                    'andalucia',
                    'baleares',
                    'catalunya',
                    'comunidad-valenciana',
                    'pais-vasco',
                    'opinion',
                    'economia',
                    'internacional',
                    'deportes',
                    'cultura',
                    'television',
                    'ciencia-y-salud',
                    'tecnologia',
                    'loc']
        extraInfo = []
        for s in sections:
            extraInfo = extraInfo + ["{}/{}".format(p, s) for p in partOfDay]

        return extraInfo
