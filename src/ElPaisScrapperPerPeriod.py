import sys
from PyQt5 import QtCore, QtWidgets, QtWebEngineWidgets
from lxml import html as htmlRenderer
import requests
import datetime
from random import *
import logging
import json
import csv
from datetime import date, datetime, timedelta


urlInfoComments = "https://elpais.com/ThreadeskupSimple"
urlGetComments = "https://elpais.com/OuteskupSimple"

logging.basicConfig(level=logging.DEBUG)

GET_URLS_STATE = "getUrls"
GET_COMMENTS_STATE = "getComments"


####################################################################################
################################ Auxliary functions ################################
####################################################################################

def generateDates(start=date(2019, 1, 1), end=date(2019, 8, 31), delta=timedelta(days=1), strFormat=""):
    curr = start
    dates = []
    while curr < end:
        if strFormat == "":
            dates.append(str(curr))
        else:
            dates.append(curr.strftime(strFormat))
        curr += delta
    return dates


def generateHemerotecaUrls(urlBase, dates, extraInfo):
    urlsPerDay = []
    logging.info(" \t Url-Base: {}".format(urlBase))
    for d in dates:
        partOfDayUrls = [urlBase.format(date=d, partOfDay=p) for p in extraInfo]
        urlsPerDay = urlsPerDay + partOfDayUrls
    logging.info(" \t -> urlsPerDay length: {}".format(len(urlsPerDay)))
    return urlsPerDay


def filterUrls(links, urlBase="https://www.elpais.com{}"):
    logging.info(" \t filtering urls. Total urls as input: {}".format(len(links)))
    filteredLinks = list(dict.fromkeys([link for link in links
                                        if not link.endswith("/")
                                        and not "#comentarios" in link
                                        and not link.endswith("=home")
                                        and link.endswith("html")
                                        and not "#" in link
                                        and not link in ["https://cat.elpais.com/", "https://elpais.com"] ]))
    reformattedLinks = []
    for l in filteredLinks:
        if l.startswith("http"):
            reformattedLinks.append(l)
        elif l.startswith("//"):
            reformattedLinks.append("https:{}".format(l))
        else:
            reformattedLinks.append(urlBase.format(l))
    logging.info(" \t filtering urls. Total urls as output: {}".format(len(reformattedLinks)))
    return reformattedLinks

def extractComments(commentsObjectList, urlNoticia="", specialCase = False):
    logging.info(" \t -> parsing comments list with -{}- elements:".format(len(commentsObjectList)))
    parsedComments = []
    listToParse = commentsObjectList[1] if specialCase else commentsObjectList
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


## Extraccion de comentarios
def lookupForComments(renderedPage, url):
    commentElList = renderedPage.xpath("//span[@class='boton-contador']")
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
        responseInfoComments = requests.get(urlInfoComments, infoArg)
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

            responseComments = requests.get(urlGetComments, commentsArgs)
            try:
                commentsResponse = json.loads(responseComments.text)
                pageComments = extractComments(commentsResponse["mensajes"], url)
            except Exception as e:
                logging.error(" \t -> there was an error trying to process getComment response")
                logging.error(" \t -> url with status code: {}".format(responseComments.status_code))
                logging.error(" \t -> url with response text len: {}".format(responseComments.text))
                logging.error(" \t -> url that fails".format(responseComments.url))

            logging.info(" \t -> retrieved total of {} comments".format(len(pageComments)))
            logging.info("#############################################################################################")
        else:
            logging.warning(" \t no comments retrieved from api for url: {}".format(url))
    else:
        logging.warning(" \t comments htmlEl has not been found in url: {}".format(url))
    return pageComments


def extractContent(renderedPage, url):
    commentsElList = renderedPage.xpath("//div[@class='articulo-cuerpo'][@id='cuerpo_noticia']//p")
    contentArr = []
    for p in commentsElList:
        contentArr.append(p.text_content())
    contentStr = "".join([ parrafo for parrafo in contentArr])
    content = {
        "url": url,
        "content": contentStr
    }
    return [content]


def exportDataCSV(data, sufix):
    today = date.today()
    rootPath = "/home/cflores/cflores_workspace/comments-retriever/results"
    fileName = "{}/{}-{}-{}_{}_{}.csv".format(rootPath, sufix, "elpais", today.day, today.month, today.year)
    with open(fileName, "w") as file:
        csvwriter = csv.writer(file)
        count = 0
        for dataObj in data:
            if count == 0:
                header = dataObj.keys()
                csvwriter.writerow(header)
                count += 1
            csvwriter.writerow(dataObj.values())
    logging.info(" \t -> exported data fileName: {}".format(fileName))


def exportDataJSON(data, sufix):
    today = date.today()
    rootPath = "/home/cflores/cflores_workspace/comments-retriever/results"
    fileName = "{}/{}-{}-{}_{}_{}.json".format(rootPath, sufix, "elpais", today.day, today.month, today.year)
    with open(fileName, "w") as file:
        json.dump(data, file)
    logging.info(" \t -> exported data fileName: {}".format(fileName))


class WebPage(QtWebEngineWidgets.QWebEnginePage):
    def __init__(self):
        super(WebPage, self).__init__()
        self._newsAndComments = []
        self._newsAndContent = []
        self._processedUrls = []
        self._newsUrls = []
        self._baseUrl = ""
        self._baseUrls = []
        self._firstPageProcessed = False;
        self._currentStage = GET_URLS_STATE
        self.loadFinished.connect(self.handleLoadFinished)

    def start(self, baseUrls):
        self._baseUrls = baseUrls
        self._urls = iter(baseUrls)
        self.fetchNext()

    def fetchNext(self):
        try:
            logging.info(" \t-> Total of processed urls: {}".format(len(self._processedUrls)))
            url = next(self._urls)
            logging.info(" \t-> next url to process is: {}".format(url))
        except StopIteration:
            if self._currentStage == GET_URLS_STATE:
                logging.info(" \t-> Stage will change from {} to {}".format(GET_URLS_STATE, GET_COMMENTS_STATE))
                logging.info(" \t-> All url per day has been processed. Total of: {}".format(len(self._baseUrls)))
                logging.info(" \t-> Total url to collect comment: {}".format(len(self._newsUrls)))
                auxLinks = list(dict.fromkeys(self._newsUrls))
                self._currentStage = GET_COMMENTS_STATE
                exportDataJSON(auxLinks, "linksNoticiasPorDia")
                self._urls = iter(auxLinks)
                url = next(self._urls)
                logging.info(" \t-> next url to process is: {}".format(url))
                self.load(QtCore.QUrl(url))
            else:
                return False
        else:
            self.load(QtCore.QUrl(url))
        return True

    def processCurrentPage(self, html):
        url = self.url().toString()
        logging.info(" -> trying to render url: {}".format(url))
        if html != "":
            renderedPage = htmlRenderer.fromstring(html)

            if (self._currentStage == GET_URLS_STATE):
                # in this stage the program is trying to extract urls for news
                logging.info(" -> processing base URL: {}".format(url))
                auxLinks = renderedPage.xpath("//a/@href")
                # filter urls
                finalLinks = filterUrls(auxLinks, urlBase="https://www.elpais.com{}")
                logging.info(" -> TOtal of url retrieved to extract comments: {}".format(len(finalLinks)))
                logging.info("==================================================================================================")
                self._newsUrls = self._newsUrls + finalLinks

            elif (self._currentStage == GET_COMMENTS_STATE):
                logging.info(" -> url will be processed to extract content and comments: {}".format(url))
                logging.info(" -> url to extract comments: {}".format(url))
                self._newsAndComments = self._newsAndComments + lookupForComments(renderedPage, url)
                logging.info(" -> url to extract content: {}".format(url))
                self._newsAndContent = self._newsAndContent + extractContent(renderedPage, url)
                logging.info(" -> url has been processed: {}".format(url))

            else:
                logging.error(" -> Something went wrong... application will be shutted down.")
                QtWidgets.qApp.quit()
        else:
            logging.warning(" -> Something is wrong. Empty html retrieved from url {}".format(url))

        self._processedUrls.append(url)
        if not self.fetchNext():
            # logging.info(self._newsAndComments)
            exportDataJSON(self._newsAndComments, "comments")
            exportDataJSON(self._newsAndContent, "contents")
            exportDataCSV(self._newsAndComments, "comments")
            exportDataCSV(self._newsAndContent, "contents")
            QtWidgets.qApp.quit()

    def handleLoadFinished(self):
        self.toHtml(self.processCurrentPage)

####################################################################################
################################## Pre-Processing ##################################
####################################################################################

dateFormat = "%Y/%m/%d"
datesBase = generateDates(date(2019, 8, 1), date(2019, 8, 31), strFormat=dateFormat)
extraDateInfo = ["m", "t", "n"]
urlTemplate = "https://elpais.com/hemeroteca/elpais/{date}/{partOfDay}/portada.html"

urlsPerDay = generateHemerotecaUrls(urlTemplate, datesBase, extraDateInfo)
logging.info(" -> total of url per day found {}".format(len(urlsPerDay)))

exportDataJSON(urlsPerDay, "urlPerDay")

app = QtWidgets.QApplication(sys.argv)
webpage = WebPage()
webpage.start(urlsPerDay)
sys.exit(app.exec_())