import sys
from PyQt5 import QtCore, QtWidgets, QtWebEngineWidgets
from lxml import html as htmlRenderer
import requests
import json
from datetime import date


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
            print(" --> ")
            for u in self._urls:
                print( " - {}".format(u))
            print(" <-- ")
            if self.fetchNext():
                QtWidgets.qApp.quit()
        else:
            print(" -> processing base URL: {}".format(url))
            auxLinks = renderedPage.xpath("//a/@href")
            links = list(dict.fromkeys(["https://www.abc.es{}".format(link) for link in auxLinks if link.endswith("noticia.html")]))
            # print(auxLinks)
            print("==================================================================================================")
            self._urls = iter(links)
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