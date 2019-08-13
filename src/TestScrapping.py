def render(source_url):
    """Fully render HTML, JavaScript and all."""

    import sys
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import QUrl
    from PyQt5.QtWebEngineWidgets import QWebEngineView

    class Render(QWebEngineView):
        def __init__(self, url):
            self.html = None
            self.app = QApplication(sys.argv)
            QWebEngineView.__init__(self)
            self.loadFinished.connect(self._loadFinished)
            #self.setHtml(html)
            self.load(QUrl(url))
            self.app.exec_()

        def _loadFinished(self, result):
            # This is an async call, you need to wait for this
            # to be called before closing the app
            self.page().toHtml(self._callable)

        def _callable(self, data):
            self.html = data
            # Data has been stored, it's safe to quit the app
            self.app.quit()

    return Render(source_url).html

# Render web page
urlNoticia = 'https://www.elmundo.es'
resultNoticia = render(urlNoticia)


from lxml import html, etree
import time
tree = html.fromstring(resultNoticia)

el = tree.xpath("//a/@href")
links = [ link for link in el if "elmundo" in link and "#ancla_comentarios" not in link and  "logo_home" not in link and "intcmp" not in link and "menu.html" not in link and "cgi.elmundo.es" not in link]

newsAndComments = []
for noticia in links:
    print("\t Link: ")
    print("\t\t {}".format(noticia))
    print("_____________________________________________________________")
    noticiaHtmlStr = render(noticia)
    noticiaHtml = html.fromstring(noticiaHtmlStr)
    autores = noticiaHtml.xpath("//div[@class='autor']/span[@class='alias']/text()")
    fechas = noticiaHtml.xpath("//time/span[@class='fecha']/text()")
    horas = noticiaHtml.xpath("//time/span[@class='hora']/text()")
    comentarios = noticiaHtml.xpath("//div[@class='texto-comentario']/p/text()")

    if (len(autores) > 0):
        # there are comments
        linksRepe = [noticia] * (len(autores))
        autores.reverse()
        fechas.reverse()
        horas.reverse()
        comentarios.reverse()

        tuples = zip(linksRepe, autores, fechas, horas, comentarios)
        newsAndComments = newsAndComments + tuples

for tuple in newsAndComments:
    print(tuple)
