import sys
from PyQt5 import QtCore, QtWidgets, QtWebEngineWidgets
from lxml import html as htmlRenderer

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
            # do stuff with html...
    #         print('loaded: [%d chars] %s' % (len(html), url))
            print(" -> processing extras URL: {}".format(url))
            autores = renderedPage.xpath("//div[@class='autor']/span[@class='alias']/text()")
            fechas = renderedPage.xpath("//time/span[@class='fecha']/text()")
            horas = renderedPage.xpath("//time/span[@class='hora']/text()")
            comentarios = renderedPage.xpath("//div[@class='texto-comentario']/p/text()")

            if (len(autores) > 0):
                # there are comments
                print(" \t {} comments found".format(len(autores)))
                linksRepe = [url]*(len(autores))
                autores.reverse()
                fechas.reverse()
                horas.reverse()
                comentarios.reverse()

                tuples = zip(linksRepe, autores, fechas, horas, comentarios)
                for tuple in tuples:
                    self._newsAndComments.append(tuple)
                # self._newsAndComments = self._newsAndComments + tuples
                print("---------------------------------------------------------------------------------------------")
            if not self.fetchNext():
                print(self._newsAndComments)
                QtWidgets.qApp.quit()
        else:
            print(" -> processing base URL: {}".format(url))
            auxLinks = renderedPage.xpath("//a/@href")
            links = [link for link in auxLinks if "elmundo" in link and "#ancla_comentarios" not in link and "logo_home" not in link and "intcmp" not in link and "menu.html" not in link and "cgi.elmundo.es" not in link and "follow=1" not in link]
            print(" \t -> links found: ")
            print(links)
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
app = QtWidgets.QApplication(sys.argv)
webpage = WebPage()
webpage.start(url)
sys.exit(app.exec_())