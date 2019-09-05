import sys
from PyQt5 import QtCore, QtWidgets, QtWebEngineWidgets
from lxml import html as htmlRenderer
import requests
import logging
import json
from random import *
import csv
from datetime import date, datetime, timedelta

urlInfoComments = "https://comments.eu1.gigya.com/comments.getStreamInfo"
urlGetComments = "https://comments.eu1.gigya.com/comments.getComments"

logging.basicConfig(filename="{}-{}.log".format(__name__, datetime.today().strftime("%H%M%S")), level=logging.INFO)

GET_URLS_STATE = "getUrls"
GET_COMMENTS_STATE = "getComments"

def extractComments(commentsObjectList, urlNoticia="", specialCase = False):
    logging.debug(" \t -> parsing comments list with -{}- elements:".format(len(commentsObjectList)))
    parsedComments = []
    listToParse = commentsObjectList[1] if specialCase else commentsObjectList
    for commentObj in listToParse:
        fechaObj = datetime.fromtimestamp(round(commentObj["timestamp"]/1000))
        fechaStr = fechaObj.strftime("%d/%m/%Y-%H:%M:%S")
        fechaArr = fechaStr.split("-")
        parsedComment = {
            "urlNoticia": urlNoticia,
            "fecha": fechaArr[0],
            "hora": fechaArr[1],
            "user": commentObj['sender']['name'],
            "commentario": commentObj['commentText'],
            "negVotes": commentObj["TotalVotes"]-commentObj["posVotes"],
            "posVotes": commentObj["posVotes"]
        }
        parsedComments.append(parsedComment)
        if commentObj.get("replies") != None:
            parsedComments = parsedComments + extractComments(commentObj.get("replies"), urlNoticia)
    return parsedComments


####################################################################################
################################ Auxliary functions ################################
####################################################################################

def generateDates(start=date(2019, 1, 1), end=date(2019, 8, 31), delta=timedelta(days=1), strFormat=""):
    curr = start
    dates = []
    while curr <= end:
        if strFormat == "":
            dates.append(str(curr))
        else:
            dates.append(curr.strftime(strFormat))
        curr += delta
    return dates

## Extraccion de comentarios
def lookupForComments(renderedPage, url):
    streamIDStr = ""

    pageComments = []
    if ".es/noticia/" in url:
        streamIDStr = "noticia-{}".format(url.split("/noticia/")[1].split("/")[0])
    elif "/noticia/" in url:
        auxSplitted = url.split("/noticia/")[1].split("/")[0].split("-")
        streamIDStr = "noticia-{}".format(auxSplitted[len(auxSplitted)-1])

    if (streamIDStr != ""):
        commentElValStreamId = streamIDStr
        logging.debug(" \t-> comment-stream-id to get comments is: {}".format(commentElValStreamId))

        infoArg = {
            "categoryID": "prod",
            "streamID": commentElValStreamId,
            "ctag": "comments_v2",
            "APIKey": "3_Hob3SXLWsBRwjPFz4f4ZEuxPo2PyeElFMWgWO2EXdBYUqwMk8lxNj78Fi_2VW5cH",
            "sourceData": {"categoryID": "prod", "streamID": commentElValStreamId},
            "pageURL": url,
            "cid": "",
            "source": "showCommentsUI",
            "sdk": "js_latest",
            "authMode": "cookie",
            "format": "json",
            "callback": "gigya.callback"
        }
        responseInfoComments = requests.get(urlInfoComments, infoArg)
        infoComments = json.loads(responseInfoComments.text)
        logging.debug(" \t-> getting information for article: {}".format(url))
        logging.debug(" \t-> total of comments for current article: {}".format(infoComments["streamInfo"]["commentCount"]))
        if infoComments["streamInfo"]["commentCount"] > 0:
            # La info dice que hay comentarios, se procede a obtenerlos
            logging.debug(" -> total of comments is greater than 0")
            nextTs = ""
            iterate = True
            while (iterate):
                commentsArgs = {
                    "categoryID": "prod",
                    "streamID": commentElValStreamId,
                    "sourceData": {"categoryID": "prod", "streamID": commentElValStreamId},
                    "pageURL": url,
                    "includeSettings": "true",
                    "threaded": "true",
                    "includeUserOptions": "true",
                    "includeUserHighlighting": "true",
                    "lang": "es",
                    "ctag": "comments_v2",
                    "APIKey": "3_Hob3SXLWsBRwjPFz4f4ZEuxPo2PyeElFMWgWO2EXdBYUqwMk8lxNj78Fi_2VW5cH",
                    "cid": "",
                    "source": "showCommentsUI",
                    "sdk": "js_latest",
                    "authMode": "cookie",
                    "format": "json",
                    "callback": "gigya.callback"
                }
                if nextTs != "":
                    commentsArgs.update({
                        "start": nextTs
                    })
                responseComments = requests.get(urlGetComments, commentsArgs)
                commentsResponse = json.loads(responseComments.text)
                iterate = commentsResponse["hasMore"]
                nextTs = commentsResponse["next"]
                pageComments = pageComments + extractComments(commentsResponse["comments"], url)
            logging.debug(" \t -> retrieved total of {} comments".format(len(pageComments)))
            logging.debug("#############################################################################################")
    return pageComments


def extractContent(renderedPage, url):
    commentsElList = renderedPage.xpath("//div[@class='gtm-article-text']//p")
    contentArr = []
    for p in commentsElList:
        contentArr.append(p.text_content())
    contentStr = "".join([ parrafo for parrafo in contentArr])
    content = {
        "url": url,
        "content": contentStr
    }
    return [content]


def generateHemerotecaUrls(urlBase, dates, extraInfo):
    urlsPerDay = []
    print(" \t Url-Base: {}".format(urlBase))
    for d in dates:
        urlsPerDay = urlsPerDay + [urlBase.format(date=d)]
    return urlsPerDay


def exportDataCSV(data, sufix):
    today = date.today()
    rootPath = "/home/cflores/cflores_workspace/comments-retriever/results"
    fileName = "{}/{}-{}-{}_{}_{}.csv".format(rootPath, sufix, "20minutos", today.day, today.month, today.year)
    with open(fileName, "w") as file:
        csvwriter = csv.writer(file)
        count = 0
        for dataObj in data:
            if count == 0:
                header = dataObj.keys()
                csvwriter.writerow(header)
                count += 1
            csvwriter.writerow(dataObj.values())
    logging.debug(" \t -> exported data fileName: {}".format(fileName))


def exportDataJSON(data, sufix):
    today = date.today()
    rootPath = "/home/cflores/cflores_workspace/comments-retriever/results"
    fileName = "{}/{}-{}-{}_{}_{}.json".format(rootPath, sufix, "20minutos", today.day, today.month, today.year)
    with open(fileName, "w") as file:
        json.dump(data, file)
    logging.debug(" \t -> exported data fileName: {}".format(fileName))


def filterUrls(links, urlBase="https://www.20minutos.es{}"):
    logging.debug(" \t filtering urls. Total urls as input: {}".format(len(links)))
    filteredLinks = list(dict.fromkeys([link for link in links
                                        if not "#social" in link
                                        and not link.startswith("#")]))
    reformattedLinks = []
    for l in filteredLinks:
        if l.startswith("http"):
            reformattedLinks.append(l)
        elif l.startswith("//"):
            reformattedLinks.append("https:{}".format(l))
        else:
            reformattedLinks.append(urlBase.format(l))
    logging.debug(" \t filtering urls. Total urls as output: {}".format(len(reformattedLinks)))
    return reformattedLinks


class WebPage(QtWebEngineWidgets.QWebEnginePage):
    def __init__(self):
        super(WebPage, self).__init__()
        self._newsAndComments = []
        self._newsAndContent = []
        self._processedUrls = []
        self._newsUrls = []
        self._baseUrl = ""
        self._media = ""
        self._period = ""
        self._baseUrls = []
        self._firstPageProcessed = False;
        self._currentStage = GET_URLS_STATE
        self.loadFinished.connect(self.handleLoadFinished)

    def start(self, baseUrls, media, period):
        self._baseUrls = baseUrls
        self._urls = iter(baseUrls)
        self._media =  media
        self._period = period
        self.fetchNext()

    def fetchNext(self):
        try:
            logging.debug(" \t-> Total of processed urls: {}".format(len(self._processedUrls)))
            url = next(self._urls)
            logging.debug(" \t-> next url to process is: {}".format(url))
        except StopIteration:
            if self._currentStage == GET_URLS_STATE:
                logging.debug(" \t-> Stage will change from {} to {}".format(GET_URLS_STATE, GET_COMMENTS_STATE))
                logging.debug(" \t-> All url per day has been processed. Total of: {}".format(len(self._baseUrls)))
                logging.debug(" \t-> Total url to collect comment: {}".format(len(self._newsUrls)))
                auxLinks = list(dict.fromkeys(self._newsUrls))
                self._currentStage = GET_COMMENTS_STATE
                exportDataJSON(auxLinks, "linksNoticiasPorDia")
                self._urls = iter(auxLinks)
                url = next(self._urls)
                logging.debug(" \t-> next url to process is: {}".format(url))
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
                logging.debug(" -> processing base URL: {}".format(url))
                auxLinks = renderedPage.xpath("//ul[@class='normal-list']//a/@href")
                # filter urls
                finalLinks = filterUrls(auxLinks, urlBase="https://www.20minutos.es{}")
                logging.debug(" -> TOtal of url retrieved to extract comments: {}".format(len(finalLinks)))
                logging.debug("==================================================================================================")
                self._newsUrls = self._newsUrls + finalLinks

            elif (self._currentStage == GET_COMMENTS_STATE):
                logging.debug(" -> url will be processed to extract content and comments: {}".format(url))
                logging.debug(" -> url to extract comments: {}".format(url))
                commentsFound = lookupForComments(renderedPage, url)
                if len(commentsFound) > 0:
                    self._newsAndComments = self._newsAndComments + commentsFound
                    logging.debug(" -> url to extract content: {}".format(url))
                    self._newsAndContent = self._newsAndContent + extractContent(renderedPage, url)
                logging.debug(" -> url has been processed: {}".format(url))

            else:
                logging.error(" -> Something went wrong... application will be shutted down.")
                QtWidgets.qApp.quit()
        else:
            logging.warning(" -> Something is wrong. Empty html retrieved from url {}".format(url))

        self._processedUrls.append(url)
        if not self.fetchNext():
            # logging.debug(self._newsAndComments)
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
dateFormat = "%Y/%m/%-d"
initDateStr = "01/01/2019"
endDateStr = "01/01/2019"
totalPeriod = "{}-{}".format(initDateStr.replace("/", ""), endDateStr.replace("/", ""))
media = "20minutos"

initDateArr = initDateStr.split("/")
endDateArr = endDateStr.split("/")

initDateArr.reverse()
endDateArr.reverse()

datesBase = generateDates(
    date(int(initDateArr[0]), int(initDateArr[1]), int(initDateArr[2])),
    date(int(endDateArr[0]), int(endDateArr[1]), int(endDateArr[2])),
    strFormat=dateFormat)

extraDateInfo = []
urlTemplate = "https://www.20minutos.es/archivo/{date}/"

urlsPerDay = generateHemerotecaUrls(urlTemplate, datesBase, extraDateInfo)
logging.debug(" -> total of url per day found {}".format(len(urlsPerDay)))

exportDataJSON(urlsPerDay, "urlPerDay")

app = QtWidgets.QApplication(sys.argv)
webpage = WebPage()
webpage.start(urlsPerDay, media, totalPeriod)
sys.exit(app.exec_())