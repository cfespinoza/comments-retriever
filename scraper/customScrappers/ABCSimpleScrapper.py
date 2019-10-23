import datetime
import json
import logging
import sys
from datetime import date, datetime

import requests
from lxml import html as htmlRenderer

from scraper.SimpleBasicScrapper import SimpleScrapper


class ABCSimpleScrapper(SimpleScrapper):
    def __init__(self):
        super().__init__()
        self._urlInfoComments = "https://gigya.abc.es/comments.getStreamInfo"
        self._urlGetComments = "https://gigya.abc.es/comments.getComments"
        self._urlXpathQuery = "//ul[@id='results-content'][@class='clearfix']//a/@href"
        self.logger = logging.getLogger(self.__class__.__name__)

    def initialize(self, begin="01/01/2019", end="31/08/2019", rootPath=None):
        self.start("https://www.abc.es/hemeroteca/dia-{day}/pagina-{pageNumber}?nres={maxPerDay}", "abc", begin, end,
                   rootPath, "%d-%m-%Y", [])

    def generateDates(self, start="", end="", delta=1, dateFormat="%d-%m-%Y"):
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
        maxPerDay = 20
        urlsPerDayObj = {}
        # templateUrl = "https://www.abc.es/hemeroteca/dia-{day}/pagina-{pageNumber}?nres={maxPerDay}"
        baseUrl = "https://www.abc.es/hemeroteca/dia-{day}?nres={maxPerDay}"
        for d in dates:
            url = baseUrl.format(day=d, maxPerDay=maxPerDay)
            self.logger.info(" \t -> url to get pages: {}".format(url))
            response = requests.get(url)
            self.logger.info(" \t -> url to get pages status_code: {}".format(response.status_code))
            renderedPage = htmlRenderer.fromstring(response.text)
            totalSpan = renderedPage.xpath("//a[@class='current']//span[@class='total']/text()")
            self.logger.info(" \t -> total span len: {}".format(len(totalSpan)))
            totalNewsPerDay = int(totalSpan[0].replace('(', '').replace(')', ''))
            # +1 due to range function ends to totalPages - 1
            totalPages = int(totalNewsPerDay / maxPerDay) + (totalNewsPerDay % 20 > 0) + 1
            urlsPerDay = [urlBase.format(day=d, pageNumber=p, maxPerDay=maxPerDay) for p in range(1, totalPages)]
            urlsPerDayObj[d] = urlsPerDay
        return urlsPerDayObj

    def filterUrls(self, links=[], urlBase=None):
        auxFinalLinks = list(dict.fromkeys([link for link in links
                                            if not link.endswith("/")
                                            and not link.startswith("#")
                                            and not link.startswith("/#")
                                            and not "hemeroteca.abc.es" in link
                                            and not "#disqus_thread" in link]))
        finalLinks = []
        for l in auxFinalLinks:
            if l.startswith("http"):
                finalLinks.append(l)
            elif l.startswith("//"):
                finalLinks.append("https:{}".format(l))
            else:
                finalLinks.append("https://www.abc.es{}".format(l))
        self.logger.info(" -> TOtal of url retrieved to extract comments: {}".format(len(finalLinks)))
        self.logger.info("==================================================================================================")
        return finalLinks

    def lookupForComments(self, renderedPageHtml=None, url=None):
        commentElList = renderedPageHtml.xpath("//div[@id='comments-container']")  # find("js-ueCommentsCounter")
        pageComments = []
        if (len(commentElList) > 0):
            commentEl = commentElList[0]
            commentElValStreamId = commentEl.get("data-voc-comments-stream-id", commentEl.get("data-stream-id"))
            self.logger.info(" \t-> comment-stream-id to get comments is: {}".format(commentElValStreamId))
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
            responseInfoComments = requests.get(self._urlInfoComments, infoArg)
            infoComments = json.loads(responseInfoComments.text)
            self.logger.info(" \t-> getting information for article: {}".format(url))
            self.logger.info(" \t-> total of comments for current article: {}".format(infoComments["streamInfo"]["commentCount"]))

            if infoComments["streamInfo"]["commentCount"] > 0:
                # La info dice que hay comentarios, se procede a obtenerlos
                self.logger.info(" -> total of comments is greater than 0")
                nextTs = ""
                iterate = True
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
                    responseComments = requests.get(self._urlGetComments, commentsArgs)
                    commentsResponse = json.loads(responseComments.text)
                    iterate = commentsResponse["hasMore"]
                    nextTs = commentsResponse["next"]
                    pageComments = pageComments + self.extractComments(commentsResponse["comments"], url, False)
                self.logger.info(" \t -> retrieved total of {} comments".format(len(pageComments)))
                self.logger.info(
                    "#############################################################################################")
        else:
            self.logger.warning(" \t -> there is something wrong due to commentsEl has not been found")
        return pageComments

    def getTitle(self, renderedPage=None, url=None):
        queries_xpath = ["//span[@class='titular']",
                         "//h1[@class='titular']",
                         "//h1[@class='titular principal']"]

        title = url
        for q in queries_xpath:
            el = renderedPage.xpath(q)
            if len(el) > 0:
                title = el[0].text if el[0].text != None else el[0].text_content()
                break
        if title == url:
            self.logger.warning(" \t -> title not found for url {}".format(url))
        return title

    def extractContent(self, renderedPage=None, url=None):
        queries_xpath = ["//span[@class='cuerpo-texto ']//p",
                         "//span[@class='cuerpo-texto  unreg']/p",
                         "//span[@class='cuerpo-texto']/p",
                         "//div[@id='tab_cronica']/p",
                         "//span[@class='cuerpo-texto top-nuevo']//p",
                         "//span[@class='contenido-top']//p",
                         "//div[@id='tab_directo']//p",
                         "//span[@class='cuerpo-texto directo']//p"]
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
            self.logger.warning("\t -> url has not content found {}".format(url))
        title = self.getTitle(renderedPage, url)
        content = {
            "url": url,
            "content": contentStr
        }
        return [content]

    def extractComments(self, commentsList=None, urlNoticia=None, specialCase=None):
        self.logger.info(" \t -> parsing comments list with -{}- elements:".format(len(commentsList)))
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
                "negVotes": commentObj["negVotes"],
                "posVotes": commentObj["posVotes"]
            }
            parsedComments.append(parsedComment)
            if commentObj.get("replies") != None:
                parsedComments = parsedComments + self.extractComments(commentObj.get("replies"), urlNoticia)
        return parsedComments
