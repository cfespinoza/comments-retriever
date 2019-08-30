import sys
from PyQt5 import QtCore, QtWidgets, QtWebEngineWidgets
from lxml import html as htmlRenderer
import requests
import json
from datetime import date
import datetime

urlInfoComments = "https://gigya.abc.es/comments.getStreamInfo"
urlGetComments = "https://gigya.abc.es/comments.getComments"

# "streamID": commentElVal,
# "sourceData": {"categoryID":"abcdigital","streamID":commentElVal},
# "pageURL": url,
# infoArg = {
#     "categoryID": "abcdigital",
#     "ctag": "comments_v2_templates",
#     "APIKey": "3_VjZL6dNEbebJWZu9Fa8JJuSZV00WJeDxEoQEbvVyi-0vOVjBGo7fwqGxuZRNOU5B",
#     "cid": "",
#     "source": "showCommentsUI",
#     "sdk": "js_latest",
#     "authMode": "cookie",
#     "format": "json",
#     "callback": "gigya.callback"
# }
#
# commentsArgs = {
#     "categoryID": "abcdigital",
#     "includeSettings": "true",
#     "threaded": "true",
#     "includeUserOptions": "true",
#     "includeUserHighlighting": "true",
#     "lang": "es",
#     "ctag": "comments_v2_templates",
#     "APIKey": "3_VjZL6dNEbebJWZu9Fa8JJuSZV00WJeDxEoQEbvVyi-0vOVjBGo7fwqGxuZRNOU5B",
#     "cid": "",
#     "source": "showCommentsUI",
#     "sdk": "js_latest",
#     "authMode": "cookie",
#     "format": "json",
#     "callback": "gigya.callback"
# }

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
            "negVotes": commentObj["negVotes"],
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
            commentElList = renderedPage.xpath("//div[@id='comments-container']") # find("js-ueCommentsCounter")
            if (len(commentElList) > 0):
                commentEl = commentElList[0]
                commentElValStreamId = commentEl.get("data-voc-comments-stream-id", commentEl.get("data-stream-id"))
                print(" \t-> comment-stream-id to get comments is: {}".format(commentElValStreamId))
                infoArg = {
                    "categoryID": "abcdigital",
                    "streamID": commentElValStreamId,
                    "ctag": "comments_v2_templates",
                    "APIKey": "3_VjZL6dNEbebJWZu9Fa8JJuSZV00WJeDxEoQEbvVyi-0vOVjBGo7fwqGxuZRNOU5B",
                    "sourceData": {"categoryID": "abcdigital", "streamID": commentElValStreamId},
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
                            "categoryID": "abcdigital",
                            "streamID": commentElValStreamId,
                            "sourceData": {"categoryID": "abcdigital", "streamID": commentElValStreamId},
                            "pageURL": url,
                            "includeSettings": "true",
                            "threaded": "true",
                            "includeUserOptions": "true",
                            "includeUserHighlighting": "true",
                            "lang": "es",
                            "ctag": "comments_v2_templates",
                            "APIKey": "3_VjZL6dNEbebJWZu9Fa8JJuSZV00WJeDxEoQEbvVyi-0vOVjBGo7fwqGxuZRNOU5B",
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
                fileName = "{}/{}-{}_{}_{}.json".format(rootPath, "abc", today.day, today.month, today.year)
                with open(fileName, "w") as file:
                    json.dump(self._newsAndComments, file)
                QtWidgets.qApp.quit()
        else:
            print(" -> processing base URL: {}".format(url))
            auxLinks = renderedPage.xpath("//a/@href")
            auxFinalLinks = list(dict.fromkeys([link for link in auxLinks if not link.endswith("/") and not link.startswith("#") and not link.startswith("/#") and not "hemeroteca.abc.es" in link and not "#disqus_thread" in link]))
            finalLinks = []
            for l in auxFinalLinks:
                if l.startswith("http"):
                    finalLinks.append(l)
                elif l.startswith("//"):
                    finalLinks.append("https:{}".format(l))
                else:
                    finalLinks.append("https://www.abc.es{}".format(l))
            print(" -> TOtal of url retrieved to extract comments: {}".format(len(finalLinks)))
            print("==================================================================================================")
            self._urls = iter(finalLinks)
            self._firstPageProcessed = True
            self.fetchNext()

    def handleLoadFinished(self):
        self.toHtml(self.processCurrentPage)


# categoryID=abcdigital&streamID=53d4acf0-bdd7-11e9-bc3a-9209dd8341d7&includeSettings=true&start=ts_1565716593506&threaded=true&includeUserOptions=true&includeUserHighlighting=true&lang=es&ctag=comments_v2_templates&APIKey=3_VjZL6dNEbebJWZu9Fa8JJuSZV00WJeDxEoQEbvVyi-0vOVjBGo7fwqGxuZRNOU5B&cid=&source=showCommentsUI&sourceData=%7B%22categoryID%22%3A%22abcdigital%22%2C%22streamID%22%3A%2253d4acf0-bdd7-11e9-bc3a-9209dd8341d7%22%7D&sdk=js_latest&authMode=cookie&pageURL=https%3A%2F%2Fwww.abc.es%2Fespana%2Fabci-tenso-encuentro-aviones-rusos-y-caza-espanol-f-18-sobre-baltico-201908131642_noticia.html%23disqus_thread&format=jsonp&callback=gigya.callback&context=R1013975035


# TODO get stream-id
# TODO get inittimestamp



## getComments
# https://gigya.abc.es/comments.getComments
# ?categoryID=abcdigital
# &streamID=4738aa6e-bd32-11e9-82af-84a6ec0d039b
# &includeSettings=true
# &start=ts_1565687084798
# &threaded=true
# &includeUserOptions=true&includeUserHighlighting=true
# &lang=es
# &ctag=comments_v2_templates
# &APIKey=3_VjZL6dNEbebJWZu9Fa8JJuSZV00WJeDxEoQEbvVyi-0vOVjBGo7fwqGxuZRNOU5B
# &cid=
# &source=showCommentsUI
# &sourceData=%7B%22categoryID%22%3A%22abcdigital%22%2C%22streamID%22%3A%224738aa6e-bd32-11e9-82af-84a6ec0d039b%22%7D
# &sdk=js_latest
# &authMode=cookie
# &pageURL=https://www.abc.es/espana/madrid/abci-alerta-oleada-okupa-y-temor-desembarco-clan-gordos-vallecas-201908122252_noticia.html
# &format=json
# &callback=gigya.callback&context=R1013975035
#

#
#
#
# sourceData: {"categoryID":"abcdigital","streamID":"4738aa6e-bd32-11e9-82af-84a6ec0d039b"}
#
#
#
# categoryID=abcdigital&streamID=4738aa6e-bd32-11e9-82af-84a6ec0d039b&includeSettings=true&start=ts_1565703882645&threaded=true&includeUserOptions=true&includeUserHighlighting=true&lang=es&ctag=comments_v2_templates&APIKey=3_VjZL6dNEbebJWZu9Fa8JJuSZV00WJeDxEoQEbvVyi-0vOVjBGo7fwqGxuZRNOU5B&cid=&source=showCommentsUI&sourceData=%7B%22categoryID%22%3A%22abcdigital%22%2C%22streamID%22%3A%224738aa6e-bd32-11e9-82af-84a6ec0d039b%22%7D&sdk=js_latest&authMode=cookie&pageURL=https%3A%2F%2Fwww.abc.es%2Fespana%2Fmadrid%2Fabci-alerta-oleada-okupa-y-temor-desembarco-clan-gordos-vallecas-201908122252_noticia.html&format=jsonp&callback=gigya.callback&context=R717006144


# https://gigya.abc.es/comments.getStreamInfo?categoryID=abcdigital&streamID=2b007c12-be83-11e9-ad48-1988f3591334&ctag=comments_v2_templates&APIKey=3_VjZL6dNEbebJWZu9Fa8JJuSZV00WJeDxEoQEbvVyi-0vOVjBGo7fwqGxuZRNOU5B&cid=&source=showCommentsUI&sourceData=%7B%22categoryID%22%3A%22abcdigital%22%2C%22streamID%22%3A%222b007c12-be83-11e9-ad48-1988f3591334%22%7D&sdk=js_latest&authMode=cookie&pageURL=https%3A%2F%2Fwww.abc.es%2Fespana%2Fmadrid%2Fabci-isabel-diaz-ayuso-investida-presidenta-comunidad-madrid-201908141807_noticia.html&format=jsonp&callback=gigya.callback&context=R1873278276
## getInfo
# categoryID: abcdigital
# streamID: 2b007c12-be83-11e9-ad48-1988f3591334
# ctag: comments_v2_templates
# APIKey: 3_VjZL6dNEbebJWZu9Fa8JJuSZV00WJeDxEoQEbvVyi-0vOVjBGo7fwqGxuZRNOU5B
# cid:
# source: showCommentsUI
# sourceData: {"categoryID":"abcdigital","streamID":"2b007c12-be83-11e9-ad48-1988f3591334"}
# sdk: js_latest
# authMode: cookie
# pageURL: https://www.abc.es/espana/madrid/abci-isabel-diaz-ayuso-investida-presidenta-comunidad-madrid-201908141807_noticia.html
# format: jsonp
# callback: gigya.callback
# context: R1873278276






# generate some test urls
urls = []
url = 'https://www.abc.es'

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