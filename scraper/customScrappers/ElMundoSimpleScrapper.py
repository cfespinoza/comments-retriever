import json
import logging
import time
from datetime import date
from json import JSONDecodeError

import requests

from scraper.SimpleBasicScrapper import SimpleScrapper


class ElMundoSimpleScrapper(SimpleScrapper):

    def __init__(self):
        super().__init__()
        self.urlGetComments = "https://www.elmundo.es/servicios/noticias/scroll/comentarios/comunidad/listar.html"
        self._urlXpathQuery = "//a/@href"
        self.logger = logging.getLogger(self.__class__.__name__)
        

    def initialize(self, begin="01/01/2019", end="31/08/2019", rootPath=None):
        extraInfoHemeroteca = self.generateHemerotecaExtraInfo()
        self.start("https://www.elmundo.es/elmundo/hemeroteca/{date}/{partOfDay}.html", "elmundo", begin, end, rootPath,
                   "%Y/%m/%d", extraInfoHemeroteca)

    def generateDates(self, start="", end="", delta=1, dateFormat="%Y/%m/%d"):
        # dateFormat = "%Y/%m/%d"
        # initDateStr = "01/01/2019"
        # endDateStr = "01/01/2019"
        self._period = "{}-{}".format(start.replace("/", ""), end.replace("/", ""))

        initDateArr = start.split("/")
        endDateArr = end.split("/")

        initDateArr.reverse()
        endDateArr.reverse()

        datesBase = self._generateDates(
            date(int(initDateArr[0]), int(initDateArr[1]), int(initDateArr[2])),
            date(int(endDateArr[0]), int(endDateArr[1]), int(endDateArr[2])),
            strFormat=dateFormat)
        return datesBase

    def generateHemerotecaUrls(self, urlBase=None, dates=None, extraInfo=None):
        # https://www.elmundo.es/elmundo/hemeroteca/2019/01/01/m/economia.html
        urlsPerDay = {}
        self.logger.info("Url-Base: {}".format(urlBase))
        for d in dates:
            partOfDayUrls = [urlBase.format(date=d, partOfDay=p) for p in extraInfo]
            urlsPerDay[d] = partOfDayUrls
        self.logger.info("urlsPerDay length: {}".format(len(urlsPerDay)))
        return urlsPerDay

    def filterUrls(self, links=[], urlBase="https://www.elmundo.es{}"):
        filteredLinks = list(dict.fromkeys([link for link in links
                                            if "elmundo" in link
                                            and "#ancla_comentarios" not in link
                                            and "logo_home" not in link
                                            and "intcmp" not in link
                                            and "menu.html" not in link
                                            and "cgi.elmundo.es" not in link
                                            and "follow=1" not in link
                                            and "?autoplay=true" not in link
                                            and "mailto:?subject" not in link
                                            and ".pdf" not in link
                                            and self._currentDateKey in link]))
        return filteredLinks

    def extractComments(self, commentsList=None, urlNoticia=None, specialCase=None):
        self.logger.info("parsing comments list with -{}- elements:".format(len(commentsList)))
        parsedComments = []
        listToParse = commentsList[1] if specialCase and len(commentsList) > 1 else commentsList
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

    def getTitle(self, renderedPage=None, url=None):
        queries_xpath = ["//div[@class='ue-l-article__header']//h1[@class='js-headline']",
                         "//div[@class='ue-l-article__header']//h1[@class='ue-c-article__headline js-headline']",
                         "//div[@class='titles']//h1[@class='js-headline']",
                         "//div[@class='ue-l-article__header']//h1",
                         "//h1[@class='ue-c-article__headline js-headline ']",
                         "//h1[@itemprop='headline']"]

        title = url
        for q in queries_xpath:
            el = renderedPage.xpath(q)
            if len(el) > 0:
                title = el[0].text
                break
        if title == url:
            self.logger.warning("title not found for url {}".format(url))
        return title

    def extractContent(self, renderedPage=None, url=None):
        queries_xpath = ["//div[@data-section='articleBody']/p",
                         "//div[@class='row content cols-70-30']/p",
                         "//dl[@class='ue-c-article__interview']",
                         "//ul[@class='ue-c-article__list ue-c-article__list--unordered']",
                         "//dl[@class='interview']"]
        contentStr = ""
        for q in queries_xpath:
            commentsElList = renderedPage.xpath(q)
            if len(commentsElList) > 0:
                contentArr = []
                for p in commentsElList:
                    contentArr.append(p.text_content())
                contentStr = "".join([parrafo for parrafo in contentArr])
                break
        if not contentStr:
            self.logger.warning("url has not content found {}".format(url))

        title = self.getTitle(renderedPage, url)
        content = {
            "url": url,
            "content": contentStr,
            "title": title
        }
        return [content]

    def extractCommentFromHtml(self, renderedPageHtml=None, url=None):
        #       extract comment from html page
        user = renderedPageHtml.xpath("//aside[@id='ancla_comentarios']//div[@class='autor ']/text()")[0]
        hora = renderedPageHtml.xpath("//aside[@id='ancla_comentarios']//span[@class='hora']/text()")[0]
        fecha = renderedPageHtml.xpath("//aside[@id='ancla_comentarios']//span[@class='fecha']/text()")[0]
        comentario = renderedPageHtml.xpath("//aside[@id='ancla_comentarios']//div[@class='texto-comentario']//p/text()")[0]
        user = user.replace("\n", "")
        hora = hora.replace("horas", "").strip()
        parsedComment = {
            "urlNoticia": url,
            "fecha": fecha,
            "hora": hora,
            "user": user,
            "commentario": comentario,
            "order": 1
        }
        return [parsedComment]

    def lookupForComments(self, renderedPageHtml=None, url=None):
        totalComentarioElList = renderedPageHtml.find_class("js-ueCommentsCounter")  # find("js-ueCommentsCounter")
        pageComments = []
        if (len(totalComentarioElList) > 0):
            totalComentarioEl = totalComentarioElList[0]
            idNoticia = int(totalComentarioEl.get("data-commentid"))
            self.logger.info("idNoticia found: {}".format(idNoticia))
            params = {"noticia": idNoticia, "version": "v2"}
            response = requests.get(self.urlGetComments, params)
            if response.status_code != 200:
                self.logger.error("something when wrong retrieving comments from idNoticia {}".format(idNoticia))
                self.logger.info("retrieving comments from idNoticia {} return status_code {}".format(idNoticia, response.status_code))
                time.sleep(5)
                response = requests.get(self.urlGetComments, params)
            responseDecoded = {}
            try:
                responseDecoded = json.loads(response.text)
            except JSONDecodeError as e:
                self.logger.error(str(e))

            self.logger.debug(responseDecoded)
            iterate = responseDecoded["lastPage"]
            pageComments = self.extractComments(responseDecoded['items'], url)
            if len(pageComments) == 0:
                pageComments = self.extractCommentFromHtml(renderedPageHtml, url)
            total = pageComments[0]["order"]
            self.logger.info("retrieved total of comments: {}".format(total))
            while not iterate:
                self.logger.info("- iterating...")
                self.logger.info("total of comments: {}".format(len(pageComments)))
                nextComments = pageComments[len(pageComments)-1]["order"]
                specialCase = False
                if (nextComments == 1):
                    self.logger.info("special case, adding extra value in order to avoid wrong behaviour")
                    specialCase = True
                    nextComments = nextComments + 1
                self.logger.info("next pagina: {}".format(nextComments))
                params = {"noticia": idNoticia, "version": "v2", "pagina": nextComments}
                response = requests.get(self.urlGetComments, params)
                responseDecoded = json.loads(response.text)
                pageComments = pageComments + self.extractComments(responseDecoded['items'], url, specialCase)
                iterate = responseDecoded["lastPage"]
                self.logger.info(
                    "---------------------------------------------------------------------------------------------")
            self.logger.info("retrieved total of {} comments".format(len(pageComments)))
            self.logger.info("#############################################################################################")
        else:
            self.logger.warning("there is something wrong due to commentsEl has not been found")
        return pageComments

    def generateHemerotecaExtraInfo(self):
        partOfDay = ["m", "t", "n"]
        sections = ['espana',
                    "index",
                    'madrid',
                    'andalucia',
                    'baleares',
                    'catalunya',
                    'comunidad-valenciana',
                    'pais-vasco',
                    'opinion',
                    'economia',
                    'internacional',
                    'deportes',
                    'cultura',
                    'television',
                    'ciencia-y-salud',
                    'tecnologia',
                    'loc']
        extraInfo = []
        for s in sections:
            extraInfo = extraInfo + ["{}/{}".format(p, s) for p in partOfDay]

        return extraInfo
