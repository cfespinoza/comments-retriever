import json
import logging
import time
from datetime import date, datetime
from json import JSONDecodeError
from random import random

import requests

from scraper.SimpleBasicScrapper import SimpleScrapper


class ElPaisSimpleScrapper(SimpleScrapper):

    def __init__(self):
        super().__init__()
        self.urlInfoComments = "https://elpais.com/ThreadeskupSimple"
        self.urlGetComments = "https://elpais.com/OuteskupSimple"
        self._urlXpathQuery = "//a/@href"
        self.logger = logging.getLogger(self.__class__.__name__)

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
        self.logger.info("Url-Base: {}".format(urlBase))
        for d in dates:
            partOfDayUrls = [urlBase.format(date=d, partOfDay=p) for p in extraInfo]
            urlsPerDay[d] = partOfDayUrls
        self.logger.info("urlsPerDay length: {}".format(len(urlsPerDay)))
        return urlsPerDay

    def filterUrls(self, links=[], urlBase="https://www.elpais.com{}"):
        self.logger.debug("filtering urls. Total urls as input: {}".format(len(links)))
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
                self.logger.warning("check the urls: {}".format(l))

        urlsToExtractInfo = list(dict.fromkeys([link for link in reformattedLinks
                                                if not link in excludedUrls]))
        self.logger.debug("filtering urls. Total urls as output: {}".format(len(urlsToExtractInfo)))
        return urlsToExtractInfo

    def extractComments(self, commentsList=None, urlNoticia=None, specialCase=False):
        self.logger.info("parsing comments list with -{}- elements:".format(len(commentsList)))
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
        time.sleep(2)
        commentElList = renderedPageHtml.xpath("//span[@class='boton-contador']")
        pageComments = []
        if (len(commentElList) > 0):
            commentEl = commentElList[0]
            commentElVal = commentEl.get("id").split("_")
            commentElValStreamId = commentElVal[len(commentElVal) - 1]
            perfiloHiloId = "_{}".format(commentElValStreamId)
            self.logger.info("comment-stream-id to get comments is: {}".format(commentElValStreamId))
            rnd = random()
            infoArg = {
                "action": "info",
                "th": commentElValStreamId,
                "rnd": rnd
            }
            responseInfoComments = requests.get(self.urlInfoComments, infoArg)
            infoComments = json.loads(responseInfoComments.text)
            self.logger.info("getting information for article: {}".format(url))
            self.logger.info("total of comments for current article: {}".format(
                infoComments["perfilesHilos"][perfiloHiloId]["numero_mensajes"]))
            totalNumMensajes = 0
            try:
                totalNumMensajes = int(infoComments["perfilesHilos"][perfiloHiloId]["numero_mensajes"])
            except Exception as e:
                self.logger.error(
                    "error trying to process numero_messages from response with message: {}".format(str(e)))
                self.logger.error("response:\n {}".format(json.dumps(infoComments)))
                self.logger.error("arguments used in request: \n {}".format(json.dumps(infoArg)))

            if totalNumMensajes > 0:
                # La info dice que hay comentarios, se procede a obtenerlos
                self.logger.info(" total of comments is greater than 0")
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
                    self.logger.error("there was an error trying to process getComment response")
                    self.logger.error("url with status code: {}".format(responseComments.status_code))
                    self.logger.error("url with response text len: {}".format(responseComments.text))
                    self.logger.error("the error was: {}".format(str(e)))
                    self.logger.error("retrying to parse json")
                    try:
                        commentsResponse = json.loads(jsonStr.replace(jsonStr[e.pos], ""))
                        pageComments = self.extractComments(commentsResponse["mensajes"], url)
                    except JSONDecodeError as er:
                        self.logger.error("redecoding has failed, omitting this comments")
                        self.logger.error("the error was: {}".format(str(er)))
                except Exception as e2:
                    self.logger.error(
                        "there was an error trying to process getComment response but parsing json has not failed")
                    self.logger.error(str(e2))

                self.logger.info("retrieved total of {} comments".format(len(pageComments)))
                self.logger.info(
                    "#############################################################################################")
            else:
                self.logger.warning("no comments retrieved from api for url: {}".format(url))
        else:
            self.logger.warning("comments htmlEl has not been found in url: {}".format(url))
        return pageComments

    def getTitle(self, renderedPage=None, url=None):
        queries_xpath = ["//span[@class='titular']",
                         "//h1[@class='titular']",
                         "//h1[@class='titular principal']",
                         "//h1[@id='articulo-titulo']"]
        title = url
        for q in queries_xpath:
            el = renderedPage.xpath(q)
            if len(el) > 0:
                title = el[0].text if el[0].text != None else el[0].text_content()
                break
        if title == url:
            self.logger.warning("title not found for url {}".format(url))
        return title

    def extractContent(self, renderedPage=None, url=None):
        queries_xpath = ["//div[@class='articulo-cuerpo'][@id='cuerpo_noticia']//p",
                         "//span[@class='cuerpo-texto ']//p",
                         "//span[@class='cuerpo-texto  unreg']/p",
                         "//span[@class='cuerpo-texto']/p"]
        contentStr = ""
        for q in queries_xpath:
            commentsElList = renderedPage.xpath(q)
            if len(commentsElList) > 0:
                contentArr = []
                for p in commentsElList:
                    contentArr.append(p.text_content())
                contentStr = "".join([parrafo for parrafo in contentArr])
                break
        if not contentStr:
            self.logger.warning("url has not content found {}".format(url))
        title = self.getTitle(renderedPage, url)
        content = {
            "url": url,
            "content": contentStr,
            "title": title
        }
        return [content]
