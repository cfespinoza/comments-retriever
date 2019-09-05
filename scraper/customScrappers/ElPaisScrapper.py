import sys
from PyQt5 import QtCore, QtWidgets, QtWebEngineWidgets
from scraper import BasicScrapper
import logging
import requests
from datetime import date, datetime, timedelta
import json
import random

class ElPaisScrapper(BasicScrapper.BasicScrapper):

    def __init__(self):
        self.logger = logging.getLogger("elpais")
        super().__init__()
        self.urlInfoComments = "https://elpais.com/ThreadeskupSimple"
        self.urlGetComments = "https://elpais.com/OuteskupSimple"

    def initialize(self, begin="01/01/2019", end="31/08/2019", rootPath=None):
        self.start("https://elpais.com/hemeroteca/elpais/{date}/{partOfDay}/portada.html", "elpais", begin, end, rootPath, "%Y/%m/%-d", ["m", "t", "n"])

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
        urlsPerDay = {}
        logging.info(" \t Url-Base: {}".format(urlBase))
        for d in dates:
            partOfDayUrls = [urlBase.format(date=d, partOfDay=p) for p in extraInfo]
            urlsPerDay[d] = partOfDayUrls
        logging.info(" \t -> urlsPerDay length: {}".format(len(urlsPerDay)))
        return urlsPerDay

    def filterUrls(self, links=[], urlBase="https://www.elpais.com{}"):
        self.logger.debug(" \t filtering urls. Total urls as input: {}".format(len(links)))
        filteredLinks = list(dict.fromkeys([link for link in links
                                            if not link.endswith("/")
                                            and not "#comentarios" in link
                                            and not link.endswith("=home")
                                            and link.endswith("html")
                                            and not "#" in link
                                            and not link in ["https://cat.elpais.com/", "https://elpais.com"]]))
        reformattedLinks = []
        for l in filteredLinks:
            if l.startswith("http"):
                reformattedLinks.append(l)
            elif l.startswith("//"):
                reformattedLinks.append("https:{}".format(l))
            else:
                reformattedLinks.append(urlBase.format(l))
        self.logger.debug(" \t filtering urls. Total urls as output: {}".format(len(reformattedLinks)))
        return reformattedLinks

    def extractComments(self, commentsList=None, urlNoticia=None, specialCase=False):
        logging.info(" \t -> parsing comments list with -{}- elements:".format(len(commentsList)))
        parsedComments = []
        listToParse = commentsList[1] if specialCase else commentsList
        for commentObj in listToParse:
            fechaObj = datetime.fromtimestamp(commentObj["tsMensaje"])
            fechaStr = fechaObj.strftime("%d/%m/%Y-%H:%M:%S")
            fechaArr = fechaStr.split("-")
            parsedComment = {
                "urlNoticia": urlNoticia,
                "fecha": fechaArr[0],
                "hora": fechaArr[1],
                "user": commentObj['usuarioOrigen'],
                "commentario": commentObj['contenido']
            }
            parsedComments.append(parsedComment)
        return parsedComments

    def lookupForComments(self, renderedPageHtml=None, url=None):
        commentElList = renderedPageHtml.xpath("//span[@class='boton-contador']")
        pageComments = []
        if (len(commentElList) > 0):
            commentEl = commentElList[0]
            commentElVal = commentEl.get("id").split("_")
            commentElValStreamId = commentElVal[len(commentElVal) - 1]
            perfiloHiloId = "_{}".format(commentElValStreamId)
            logging.info(" \t-> comment-stream-id to get comments is: {}".format(commentElValStreamId))
            rnd = random()
            infoArg = {
                "action": "info",
                "th": commentElValStreamId,
                "rnd": rnd
            }
            responseInfoComments = requests.get(self.urlInfoComments, infoArg)
            infoComments = json.loads(responseInfoComments.text)
            logging.info(" \t-> getting information for article: {}".format(url))
            logging.info(" \t-> total of comments for current article: {}".format(
                infoComments["perfilesHilos"][perfiloHiloId]["numero_mensajes"]))
            if infoComments["perfilesHilos"][perfiloHiloId]["numero_mensajes"] > 0:
                # La info dice que hay comentarios, se procede a obtenerlos
                logging.info(" -> total of comments is greater than 0")
                rnd = random()
                commentsArgs = {
                    "s": "",
                    "rnd": rnd,
                    "th": 1,
                    "msg": commentElValStreamId,
                    "nummsg": infoComments["perfilesHilos"][perfiloHiloId]["numero_mensajes"],
                    "tt": 1
                }

                responseComments = requests.get(self.urlGetComments, commentsArgs)
                try:
                    commentsResponse = json.loads(responseComments.text)
                    pageComments = self.extractComments(commentsResponse["mensajes"], url)
                except Exception as e:
                    logging.error(" \t -> there was an error trying to process getComment response")
                    logging.error(" \t -> url with status code: {}".format(responseComments.status_code))
                    logging.error(" \t -> url with response text len: {}".format(responseComments.text))
                    logging.error(" \t -> url that fails".format(responseComments.url))

                logging.info(" \t -> retrieved total of {} comments".format(len(pageComments)))
                logging.info(
                    "#############################################################################################")
            else:
                logging.warning(" \t no comments retrieved from api for url: {}".format(url))
        else:
            logging.warning(" \t comments htmlEl has not been found in url: {}".format(url))
        return pageComments

    def extractContent(self, renderedPage=None, url=None):
        commentsElList = renderedPage.xpath("//div[@class='articulo-cuerpo'][@id='cuerpo_noticia']//p")
        contentArr = []
        for p in commentsElList:
            contentArr.append(p.text_content())
        contentStr = "".join([parrafo for parrafo in contentArr])
        content = {
            "url": url,
            "content": contentStr
        }
        return [content]

app = QtWidgets.QApplication(sys.argv)
scrapper = ElPaisScrapper()
scrapper.initialize(end="31/08/2019", rootPath="/home/cflores/cflores_workspace/comments-retriever/results")
sys.exit(app.exec_())
