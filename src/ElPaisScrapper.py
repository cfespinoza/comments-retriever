import sys
from PyQt5 import QtCore, QtWidgets, QtWebEngineWidgets
from lxml import html as htmlRenderer
import requests
import json
from datetime import date
import datetime
from random import *

urlInfoComments = "https://elpais.com/ThreadeskupSimple"
urlGetComments = "https://elpais.com/OuteskupSimple"


def extractComments(commentsObjectList, urlNoticia="", specialCase = False):
    print(" \t -> parsing comments list with -{}- elements:".format(len(commentsObjectList)))
    parsedComments = []
    listToParse = commentsObjectList[1] if specialCase else commentsObjectList
    for commentObj in listToParse:
        fechaObj = datetime.datetime.fromtimestamp(commentObj["tsMensaje"])
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
            commentElList = renderedPage.xpath("//span[@class='boton-contador']") # find("js-ueCommentsCounter")
            if (len(commentElList) > 0):
                commentEl = commentElList[0]
                commentElVal = commentEl.get("id").split("_")
                commentElValStreamId = commentElVal[len(commentElVal)-1]
                perfiloHiloId = "_{}".format(commentElValStreamId)
                print(" \t-> comment-stream-id to get comments is: {}".format(commentElValStreamId))
                rnd = random()
                infoArg = {
                    "action": "info",
                    "th": commentElValStreamId,
                    "rnd": rnd
                }
                responseInfoComments = requests.get(urlInfoComments, infoArg)
                infoComments = json.loads(responseInfoComments.text)
                print(" \t-> getting information for article: {}".format(url))
                print(" \t-> total of comments for current article: {}".format(infoComments["perfilesHilos"][perfiloHiloId]["numero_mensajes"]))
                if infoComments["perfilesHilos"][perfiloHiloId]["numero_mensajes"] > 0:
                    # La info dice que hay comentarios, se procede a obtenerlos
                    print(" -> total of comments is greater than 0")
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
                    commentsResponse = json.loads(responseComments.text)
                    pageComments = extractComments(commentsResponse["mensajes"], url)
                    print(" \t -> retrieved total of {} comments".format(len(pageComments)))
                    print(
                        "#############################################################################################")
                    self._newsAndComments = self._newsAndComments + pageComments
            print(" -> url has been processed: {}".format(url))
            self._processedUrls.append(url)
            if not self.fetchNext():
                # print(self._newsAndComments)
                today = date.today()
                rootPath = "/home/cflores/cflores_workspace/comments-retriever/results"
                fileName = "{}/{}-{}_{}_{}.json".format(rootPath, "elpais", today.day, today.month, today.year)
                with open(fileName, "w") as file:
                    json.dump(self._newsAndComments, file)
                QtWidgets.qApp.quit()
        else:
            print(" -> processing base URL: {}".format(url))
            auxLinks = renderedPage.xpath("//a/@href")
            # obtener links, cuidado que alguno ya empieza por http...
            auxFinalLinks = list(dict.fromkeys([link for link in auxLinks if not link.endswith("/") and not "#comentarios" in link and not link.endswith("=home")]))
            finalLinks = []
            for l in auxFinalLinks:
                if l.startswith("http"):
                    finalLinks.append(l)
                elif l.startswith("//"):
                    finalLinks.append("https:{}".format(l))
                else:
                    finalLinks.append("https://www.elpais.com{}".format(l))
            print(" -> TOtal of url retrieved to extract comments: {}".format(len(finalLinks)))
            print("==================================================================================================")
            self._urls = iter(finalLinks)
            self._firstPageProcessed = True
            self.fetchNext()

    def handleLoadFinished(self):
        self.toHtml(self.processCurrentPage)


# generate some test urls
urls = []
url = 'https://www.elpais.com'

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