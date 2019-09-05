import sys
from PyQt5 import QtCore, QtWidgets, QtWebEngineWidgets
from lxml import html as htmlRenderer
import requests
import json
from datetime import date

def extractComments(commentsObjectList, urlNoticia="", specialCase = False):
    print(" \t -> parsing comments list with -{}- elements:".format(len(commentsObjectList)))
    parsedComments = []
    listToParse = commentsObjectList[1] if specialCase else commentsObjectList
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


class WebPage(QtWebEngineWidgets.QWebEnginePage):
    def __init__(self):
        super(WebPage, self).__init__()
        self._newsAndComments = []
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
            url = next(self._urls)
        except StopIteration:
            return False
        else:
            self.load(QtCore.QUrl(url))
        return True

    def processCurrentPage(self, html):
        url = self.url().toString()
        renderedPage = htmlRenderer.fromstring(html)
        if (self._firstPageProcessed):
            pageComments = []
            print(" -> processing extras URL: {}".format(url))
            totalComentarioElList = renderedPage.find_class("js-ueCommentsCounter") # find("js-ueCommentsCounter")
            if (len(totalComentarioElList) > 0):
                totalComentarioEl = totalComentarioElList[0]
                idNoticia = int(totalComentarioEl.get("data-commentid"))
                print(" \t idNoticia found: {}".format(idNoticia))
                urlBase = "https://www.elmundo.es/servicios/noticias/scroll/comentarios/comunidad/listar.html"
                params = {"noticia": idNoticia, "version": "v2"}
                response = requests.get(urlBase, params)
                responseDecoded = json.loads(response.text)
                print(responseDecoded)
                iterate = responseDecoded["lastPage"]
                total = responseDecoded["total"]
                print(" -> retrieved total of comments: {}".format(total))
                if (total > 0):
                    pageComments = extractComments(responseDecoded['items'], url)
                    while not iterate:
                        print(" - iterating...")
                        print(" -> total of comments: {}".format(len(pageComments)))
                        nextComments = total - len(pageComments)
                        specialCase = False
                        if (nextComments == 1):
                            print(" -> special case, adding extra value in order to avoid wrong behaviour")
                            specialCase = True
                            nextComments = nextComments + 1
                        print(" -> next pagina: {}".format(nextComments))
                        params = {"noticia": idNoticia, "version": "v2", "pagina": nextComments}
                        response = requests.get(urlBase, params)
                        responseDecoded = json.loads(response.text)
                        pageComments = pageComments + extractComments(responseDecoded['items'], url, specialCase)
                        iterate = responseDecoded["lastPage"]
                        print("---------------------------------------------------------------------------------------------")
                    print(" \t -> retrieved total of {} comments".format(len(pageComments)))
                    print("#############################################################################################")
                    self._newsAndComments = self._newsAndComments + pageComments
            if not self.fetchNext():
                # print(self._newsAndComments)
                today = date.today()
                rootPath = "/home/cflores/cflores_workspace/pyscrapper/results"
                fileName = "{}/{}-{}_{}_{}.json".format(rootPath, "elmundo", today.day, today.month, today.year)
                with open(fileName, "w") as file:
                    json.dump(self._newsAndComments, file)
                QtWidgets.qApp.quit()
        else:
            print(" -> processing base URL: {}".format(url))
            auxLinks = renderedPage.xpath("//a/@href")
            links = [link for link in auxLinks if "elmundo" in link and "#ancla_comentarios" not in link and "logo_home" not in link and "intcmp" not in link and "menu.html" not in link and "cgi.elmundo.es" not in link and "follow=1" not in link]
            print(" \t -> links found: ")
            print(" Total of links found: {}".format(links))
            print("==================================================================================================")
            #             links = [ link for link in el if "elmundo" in link and "#ancla_comentarios" not in link and  "logo_home" not in link and "intcmp" not in link and "menu.html" not in link and "cgi.elmundo.es" not in link]
            self._urls = iter(links)
            self._firstPageProcessed = True
            self.fetchNext()

    def handleLoadFinished(self):
        self.toHtml(self.processCurrentPage)


# generate some test urls
urls = []
url = 'https://www.elmundo.es'

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