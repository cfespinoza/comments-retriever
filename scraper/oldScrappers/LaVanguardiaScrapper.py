import sys
from PyQt5 import QtCore, QtWidgets, QtWebEngineWidgets
from lxml import html as htmlRenderer
import requests
import json
from datetime import date
import datetime
import base64

urlInfoComments = "https://grupogodo1.bootstrap.fyre.co/api/v1.1/public/comments/ncomments/{}.json"
urlGetComments = "https://data.livefyre.com/bs3/v3.1/grupogodo1.fyre.co/{}/{}/init"


def extractComments(commentsObjectList, authorObjectList, urlNoticia="", specialCase = False):
    print(" \t -> parsing comments list with -{}- elements:".format(len(commentsObjectList)))
    parsedComments = []
    listToParse = commentsObjectList[1] if specialCase else commentsObjectList
    for commentObj in listToParse:
        contentObj = commentObj.get("content", None)
        isValidContent = "bodyHtml" in contentObj.keys()
        if isValidContent:
            fechaObj = datetime.datetime.fromtimestamp(contentObj["createdAt"])
            fechaStr = fechaObj.strftime("%d/%m/%Y-%H:%M:%S")
            fechaArr = fechaStr.split("-")
            parsedComment = {
                "urlNoticia": urlNoticia,
                "fecha": fechaArr[0],
                "hora": fechaArr[1],
                "user": authorObjectList[contentObj['authorId']]['displayName'],
                "commentario": contentObj['bodyHtml']
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
            commendInfoKeysElArr = renderedPage.xpath("//label[@class='livefyre-commentcount']")
            if len(commendInfoKeysElArr) > 0:

                commentInfoEl = commendInfoKeysElArr[0]
                commentSiteId = commentInfoEl.get("data-lf-site-id")
                commentArticleId =  commentInfoEl.get("data-lf-article-id")
                if (commentSiteId != "" and commentArticleId != ""):
                    print(" \t-> data-lf-site-id to get comments is: {}".format(commentSiteId))
                    print(" \t-> data-lf-article-id to get comments is: {}".format(commentArticleId))

                    # Get Comments Info
                    urlParam = "{}:{}".format(commentSiteId, commentArticleId)
                    urlParamBase64 = str(base64.b64encode(urlParam.encode("utf-8")), "utf-8")
                    commentElArticleIdEncoded = str(base64.b64encode(commentArticleId.encode("utf-8")), "utf-8")
                    urlInfoCommentsEncoded = urlInfoComments.format(urlParamBase64)
                    print(" \t-> getting information for article: {}".format(urlInfoCommentsEncoded))
                    responseInfoComments = requests.get(urlInfoCommentsEncoded)
                    infoComments = json.loads(responseInfoComments.text)
                    if commentSiteId in infoComments["data"] \
                            and commentArticleId in infoComments["data"][commentSiteId] \
                            and infoComments["data"][commentSiteId][commentArticleId]["total"] > 0:
                        # La info dice que hay comentarios, se procede a obtenerlos
                        print(" \t-> total of comments for current article: {}".format(
                            infoComments["data"][commentSiteId][commentArticleId]["total"]))
                        urlGetCommentsEncoded = urlGetComments.format(commentSiteId, commentElArticleIdEncoded)
                        responseComments = requests.get(urlGetCommentsEncoded)
                        commentsResponse = json.loads(responseComments.text)
                        pageComments = extractComments(commentsResponse["headDocument"]['content'], commentsResponse["headDocument"]['authors'], url)
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
                    fileName = "{}/{}-{}_{}_{}.json".format(rootPath, "lavanguardia", today.day, today.month, today.year)
                    with open(fileName, "w") as file:
                        json.dump(self._newsAndComments, file)
                    QtWidgets.qApp.quit()
        else:
            print(" -> processing base URL: {}".format(url))
            auxLinks = renderedPage.xpath("//a/@href")
            auxFinalLinks = list(dict.fromkeys([ link for link in auxLinks
                                                if "lavanguardia" in link
                                                and link.endswith("html")
                                                and not "cookies_privacy_LV_popup.html" in link
                                                and not "lavanguardia.com/servicios/bolsa" in link ]))
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
url = 'https://www.lavanguardia.com/'

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