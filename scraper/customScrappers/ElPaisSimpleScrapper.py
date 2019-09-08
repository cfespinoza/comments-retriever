import json
import logging
import sys
from datetime import date, datetime
from json import JSONDecodeError
from random import random
import time

import requests

from scraper.SimpleBasicScrapper import SimpleScrapper


class ElPaisScrapper(SimpleScrapper):

    def __init__(self):
        self.logger = logging.getLogger("elpais")
        super().__init__()
        self.urlInfoComments = "https://elpais.com/ThreadeskupSimple"
        self.urlGetComments = "https://elpais.com/OuteskupSimple"
        self._urlXpathQuery = "//a/@href"

    def initialize(self, begin="01/01/2019", end="31/08/2019", rootPath=None):
        self.start("https://elpais.com/hemeroteca/elpais/{date}/{partOfDay}/portada.html", "elpais", begin, end,
                   rootPath, "%Y/%m/%d", ["m", "t", "n"])

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
        excludedUrls = [
            "https://www.elpais.com/s/setEspana.html",
            "https://www.elpais.com/s/setAmerica.html",
            "https://www.elpais.com/s/setBrasil.html",
            "https://www.elpais.com/s/setCat.html",
            "https://elpais.com/elpais/inenglish.html",
            "https://elpais.com/internacional/estados_unidos.html",
            "https://elpais.com/internacional/mexico.html",
            "https://elpais.com/elpais/opinion.html",
            "https://elpais.com/ccaa/catalunya.html",
            "https://elpais.com/ccaa/madrid.html",
            "https://elpais.com/economia/vivienda.html",
            "https://elpais.com/elpais/ciencia.html",
            "https://elpais.com/elpais/estilo.html",
            "https://elpais.com/cultura/television.html",
            "https://elpais.com/cultura/babelia.html",
            "https://elpais.com/elpais/ideas.html",
            "https://elpais.com/elpais/planeta_futuro.html",
            "https://elpais.com/elpais/buenavida.html",
            "https://elpais.com/elpais/icon.html",
            "https://elpais.com/elpais/icon_design.html",
            "https://elpais.com/elpais/album.html",
            "https://elpais.com/elpais/especiales.html",
            "https://elpais.com/elpais/blogs.html",
            "https://elpais.com/elpais/escaparate.html",
            "https://elpais.com/suscripciones/elpaismas.html",
            "https://elpais.com/elpais/videos.html",
            "https://cat.elpais.com/",
            "https://elpais.com"
        ]
        filteredLinks = list(dict.fromkeys([link for link in links
                                            if not link.endswith("/")
                                            and not "#comentarios" in link
                                            and not link.endswith("=home")
                                            and not "editor.elpais.int" in link
                                            and link.endswith("html")
                                            and not "#" in link
                                            and self._currentDateKey in link]))
        reformattedLinks = []
        for l in filteredLinks:
            if l.startswith("http"):
                reformattedLinks.append(l)
            elif l.startswith("//"):
                toFormat = l
                if "https://elpais.com" in l:
                    toFormat = l.replace("https://elpais.com", "")
                reformattedLinks.append("https:{}".format(toFormat))
            elif "https://elpais.com" not in l:
                reformattedLinks.append(urlBase.format(l))
            else:
                logging.warning(" \t -> check the urls: {}".format(l))


        urlsToExtractInfo = list(dict.fromkeys([link for link in reformattedLinks
                                   if not link in excludedUrls]))
        self.logger.debug(" \t filtering urls. Total urls as output: {}".format(len(urlsToExtractInfo)))
        return urlsToExtractInfo

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
        time.sleep(1)
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
            totalNumMensajes = 0
            try:
                totalNumMensajes = int(infoComments["perfilesHilos"][perfiloHiloId]["numero_mensajes"])
            except Exception as e:
                logging.error(" \t -> error trying to process numero_messages from response with message: {}".format(str(e)))
                logging.error(" \t -> response:\n {}".format(json.dumps(infoComments)))
                logging.error(" \t -> arguments used in request: \n {}".format(json.dumps(infoArg)))


            if totalNumMensajes > 0:
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
                jsonStr = responseComments.content.decode("utf8")
                try:
                    commentsResponse = json.loads(jsonStr)
                    pageComments = self.extractComments(commentsResponse["mensajes"], url)
                except JSONDecodeError as e:
                    logging.error(" \t -> there was an error trying to process getComment response")
                    logging.error(" \t -> url with status code: {}".format(responseComments.status_code))
                    logging.error(" \t -> url with response text len: {}".format(responseComments.text))
                    logging.error(" \t -> the error was: {}".format(str(e)))
                    logging.error(" \t -> retrying to parse json")
                    try:
                        commentsResponse = json.loads(jsonStr.replace(jsonStr[e.pos], ""))
                        pageComments = self.extractComments(commentsResponse["mensajes"], url)
                    except JSONDecodeError as er:
                        logging.error(" \t -> redecoding has failed, omitting this comments")
                        logging.error(" \t -> the error was: {}".format(str(er)))
                except Exception as e2:
                    logging.error(" \t -> there was an error trying to process getComment response but parsing json has not failed")
                    logging.error(str(e2))

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


scrapper = ElPaisScrapper()
scrapper.initialize(begin="10/05/2019", end="31/08/2019",
                    rootPath="/home/cflores/cflores_workspace/comments-retriever/results")
sys.exit(0)
