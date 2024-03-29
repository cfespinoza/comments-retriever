import json
import logging
from datetime import date, datetime

import requests

from scraper.SimpleBasicScrapper import SimpleScrapper


class VeinteMinutosSimpleScrapper(SimpleScrapper):

    def __init__(self):
        super().__init__()
        self.urlInfoComments = "https://comments.eu1.gigya.com/comments.getStreamInfo"
        self.urlGetComments = "https://comments.eu1.gigya.com/comments.getComments"
        self._urlXpathQuery = "//section[@class='container']//a/@href"
        self.data_layer_key = "dataLayer"
        self.categoria_key = "categoria"
        self.subcategoria_key = "subcategoria"

        self.logger = logging.getLogger(self.__class__.__name__)

    def initialize(self, begin="01/01/2019", end="01/01/2019", rootPath=None):
        self.start("https://www.20minutos.es/archivo/{date}/", "20minutos", begin, end, rootPath, "%Y/%m/%-d", [])

    def generateDates(self, start="", end="", delta=1, dateFormat="%Y/%m/%-d"):
        # dateFormat = "%Y/%m/%-d"
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
        urlsPerDay = {}
        print("Url-Base: {}".format(urlBase))
        for d in dates:
            urlsPerDay[d] = [urlBase.format(date=d)]
        return urlsPerDay

    def filterUrls(self, links=[], urlBase="https://www.20minutos.es{}"):
        self.logger.debug("filtering urls. Total urls as input: {}".format(len(links)))
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
        self.logger.debug("filtering urls. Total urls as output: {}".format(len(reformattedLinks)))
        return reformattedLinks

    def extractComments(self, commentsList=None, urlNoticia=None, specialCase=None):
        self.logger.debug("parsing comments list with -{}- elements:".format(len(commentsList)))
        parsedComments = []
        listToParse = commentsList[1] if specialCase else commentsList
        for commentObj in listToParse:
            fechaObj = datetime.fromtimestamp(round(commentObj["timestamp"] / 1000))
            fechaStr = fechaObj.strftime("%d/%m/%Y-%H:%M:%S")
            fechaArr = fechaStr.split("-")
            parsedComment = {
                "urlNoticia": urlNoticia,
                "fecha": fechaArr[0],
                "hora": fechaArr[1],
                "user": commentObj['sender']['name'],
                "commentario": commentObj['commentText'],
                "negVotes": commentObj["TotalVotes"] - commentObj["posVotes"],
                "posVotes": commentObj["posVotes"]
            }
            parsedComments.append(parsedComment)
            if commentObj.get("replies") != None:
                parsedComments = parsedComments + self.extractComments(commentObj.get("replies"), urlNoticia)
        return parsedComments

    def getTitle(self, renderedPage=None, url=None):
        queryXpath = "//div[@class='title']/h1"
        el = renderedPage.xpath(queryXpath)
        title = url
        if len(el) == 0:
            self.logger.warning("title not found in: {}".format(url))
        else:
            title = el[0].text
        return title

    def getDataLayer(self, rendered_html=None):
        scriptText = ""
        for element in rendered_html.iter('script'):
            scriptText = element.text_content()
            if self.data_layer_key in scriptText:
                self.logger.debug(" data_layer_key has been found")
                break
        if not scriptText:
            return {}

        data_layer_json_str = scriptText.split('dataLayer = [')[-1].rsplit('];', 1)[0].strip()
        try:
            data_layer = json.loads(data_layer_json_str)
            return data_layer
        except Exception as e:
            self.logger.error(" parsing json has failed.")
            self.logger.error("-------------------------------")
            self.logger.error(data_layer_json_str)
            self.logger.error("-------------------------------")
            self.logger.error(str(e))
            return {}

    def extractContent(self, renderedPage=None, url=None):
        queries_xpath = ["//div[@class='article-text']",
                         "//div[@class='article-text']//p",
                         "//div[@class='article-text']//span",
                         "//div[@class='article-text']/div[@class='gmail_default']"]

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
        dataLayer = self.getDataLayer(renderedPage)
        category = dataLayer.get(self.categoria_key, "")
        subcategory = dataLayer.get(self.subcategoria_key, "")
        content = {
            "url": url,
            "content": contentStr,
            "title": title,
            "category": category,
            "subcategory": subcategory
        }
        return [content]

    def lookupForComments(self, renderedPageHtml=None, url=None):
        streamIDStr = ""

        pageComments = []
        if ".es/noticia/" in url:
            streamIDStr = "noticia-{}".format(url.split("/noticia/")[1].split("/")[0])
        elif "/noticia/" in url:
            auxSplitted = url.split("/noticia/")[1].split("/")[0].split("-")
            streamIDStr = "noticia-{}".format(auxSplitted[len(auxSplitted) - 1])

        if (streamIDStr != ""):
            commentElValStreamId = streamIDStr
            self.logger.debug("comment-stream-id to get comments is: {}".format(commentElValStreamId))

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
            responseInfoComments = requests.get(self.urlInfoComments, infoArg)
            infoComments = json.loads(responseInfoComments.text)
            self.logger.debug("getting information for article: {}".format(url))
            self.logger.debug(
                "total of comments for current article: {}".format(infoComments["streamInfo"]["commentCount"]))
            if infoComments["streamInfo"]["commentCount"] > 0:
                # La info dice que hay comentarios, se procede a obtenerlos
                self.logger.debug("total of comments is greater than 0")
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
                    responseComments = requests.get(self.urlGetComments, commentsArgs)
                    commentsResponse = json.loads(responseComments.text)
                    iterate = commentsResponse["hasMore"]
                    nextTs = commentsResponse["next"]
                    pageComments = pageComments + self.extractComments(commentsResponse["comments"], url)
                self.logger.debug("retrieved total of {} comments".format(len(pageComments)))
                self.logger.debug(
                    "#############################################################################################")
        return pageComments
