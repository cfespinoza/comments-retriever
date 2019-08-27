import sys
from PyQt5 import QtCore, QtWidgets, QtWebEngineWidgets
from lxml import html as htmlRenderer
import requests
import json
from datetime import date
import datetime

urlInfoComments = "https://comments.eu1.gigya.com/comments.getStreamInfo"
urlGetComments = "https://comments.eu1.gigya.com/comments.getComments"

def extractComments(commentsObjectList, urlNoticia="", specialCase = False):
    print(" \t -> parsing comments list with -{}- elements:".format(len(commentsObjectList)))
    parsedComments = []
    listToParse = commentsObjectList[1] if specialCase else commentsObjectList
    for commentObj in listToParse:
        fechaObj = datetime.datetime.fromtimestamp(round(commentObj["timestamp"]/1000))
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


class WebPage(QtWebEngineWidgets.QWebEnginePage):
    def __init__(self):
        super(WebPage, self).__init__()
        self._newsAndComments = []
        self._processedUrls = []
        self._baseUrl = ""
        self._firstPageProcessed = False;
        self.loadFinished.connect(self.handleLoadFinished)

    def start(self, baseUrl):
#         self._urls = iter(urls)
#         self.fetchNext()
        self._baseUrl = baseUrl
        self.load(QtCore.QUrl(url))

    def fetchNext(self):
        try:
            print(" \t-> Total of processed urls: {}".format(len(self._processedUrls)))
            url = next(self._urls)
            print(" \t-> next url to process is: {}".format(url))
        except StopIteration:
            return False
        else:
            self.load(QtCore.QUrl(url))
        return True

    def processCurrentPage(self, html):
        url = self.url().toString()
        print(" -> trying to render url: {}".format(url))
        renderedPage = htmlRenderer.fromstring(html)
        if (self._firstPageProcessed):
            streamIDStr = ""

            if "/noticia/" in url:
                streamIDStr = "noticia-{}".format(url.split("/noticia/")[1].split("/")[0])

            if (streamIDStr != ""):
                commentElValStreamId = streamIDStr
                print(" \t-> comment-stream-id to get comments is: {}".format(commentElValStreamId))

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
                print(" \t-> getting information for article: {}".format(url))
                print(" \t-> total of comments for current article: {}".format(infoComments["streamInfo"]["commentCount"]))
                if infoComments["streamInfo"]["commentCount"] > 0:
                    # La info dice que hay comentarios, se procede a obtenerlos
                    print(" -> total of comments is greater than 0")
                    nextTs = ""
                    iterate = True
                    pageComments = []
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
                        pageComments = pageComments + extractComments(commentsResponse["comments"])
                    print(" \t -> retrieved total of {} comments".format(len(pageComments)))
                    print(
                        "#############################################################################################")
                    self._newsAndComments = self._newsAndComments + pageComments
            else:
                print(" \t-> url has not been processed correctly")
            print(" -> url has been processed: {}".format(url))
            self._processedUrls.append(url)
            if not self.fetchNext():
                # print(self._newsAndComments)
                today = date.today()
                rootPath = "/home/cflores/cflores_workspace/comments-retriever/results"
                fileName = "{}/{}-{}_{}_{}.json".format(rootPath, "20minutos", today.day, today.month, today.year)
                with open(fileName, "w") as file:
                    json.dump(self._newsAndComments, file)
                QtWidgets.qApp.quit()
        else:
            print(" -> processing base URL: {}".format(url))
            auxLinks = renderedPage.xpath("//a/@href")
            auxFinalLinks = list(dict.fromkeys([link for link in auxLinks
                                                if not "#social" in link
                                                and not link.startswith("#")]))
            finalLinks = []
            for l in auxFinalLinks:
                if l.startswith("http"):
                    finalLinks.append(l)
                elif l.startswith("//"):
                    finalLinks.append("https:{}".format(l))
                else:
                    finalLinks.append("https://www.20minutos.es{}".format(l))

            print(" -> TOtal of url retrieved to extract comments: {}".format(len(finalLinks)))
            print("==================================================================================================")
            self._urls = iter(finalLinks)
            self._firstPageProcessed = True
            self.fetchNext()

    def handleLoadFinished(self):
        self.toHtml(self.processCurrentPage)



# generate some test urls
urls = []
url = 'https://www.20minutos.es/'

urlObjs = [{
    "name": "elmundo",
    "url": "https://www.elmundo.es",
    "commentsUrl": "https://www.elmundo.es/servicios/noticias/scroll/comentarios/comunidad/listar.html",
    "initParams": {"noticia": "", "version": "v2"},
    "keyParam": "noticia",
    "pageParam": "page"
}]


app = QtWidgets.QApplication(sys.argv)
webpage = WebPage()
webpage.start(url)
sys.exit(app.exec_())