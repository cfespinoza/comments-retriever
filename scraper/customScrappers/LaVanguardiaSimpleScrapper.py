import base64
import json
import logging
import time
from datetime import date, datetime

import requests
from dateutil import parser

from scraper.SimpleBasicScrapper import SimpleScrapper


class LaVanguardiaSimpleScrapper(SimpleScrapper):

    def __init__(self):
        self.logger = logging.getLogger("lavanguardia")
        super().__init__()

        self._urlInfoComments = "https://data.livefyre.com/bs3/v3.1/grupogodo1.fyre.co/{}/{}/init"
        self._urlGetComments = "https://data.livefyre.com/bs3/v3.1/grupogodo1.fyre.co/{}/{}/{}.json"
        self._urlXpathQuery = "//div[@class='main']//i/@data-href"

    def initialize(self, begin="01/01/2019", end="31/08/2019", rootPath=None):
        logging.basicConfig(filename="{}-{}.log".format("lavanguardia", datetime.today().strftime("%d%m%Y-%H%M%S")),
                            level=logging.INFO)
        self.start("https://web.archive.org/web/{timestamp}/https://www.lavanguardia.com/", "lavanguardia", begin, end,
                   rootPath, "%Y%m%d", [])

    def generateDates(self, start="", end="", delta=1, dateFormat="%Y%m%d"):
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

    def generateHemerotecaUrls(self, urlBase="https://web.archive.org/web/{timestamp}/https://www.lavanguardia.com/",
                               dates=None, extraInfo=None):
        # urlBase = "https://web.archive.org/web/{timestamp}/https://www.lavanguardia.com/"
        beginDate = dates[0]
        endDate = dates[len(dates) - 1]
        beginParsedDate = parser.parse(beginDate).date()
        endParsedDate = parser.parse(endDate).date()
        urlObj = {}
        hemerotecaUrl = "https://web.archive.org/__wb/calendarcaptures?url=https://www.lavanguardia.com/&selected_year={year}".format(
            year=beginParsedDate.year)
        snapshotsForUrl = requests.get(hemerotecaUrl)
        yearInfo = json.loads(snapshotsForUrl.text)
        for monthArr in yearInfo:
            for weekArr in monthArr:
                for dayObj in weekArr:
                    if dayObj != None:
                        if len(dayObj.keys()) > 0:
                            tsArr = dayObj.get("ts", [])
                            stArr = dayObj.get("st", [])
                            goodIndex = stArr.index(200) if 200 in stArr else -1
                            goodTs = tsArr[goodIndex]
                            currentParsedDate = parser.parse(str(goodTs)).date()
                            if beginParsedDate <= currentParsedDate and endParsedDate >= currentParsedDate:
                                urlObj[date.strftime(currentParsedDate, self._dateFormat)] = [urlBase.format(timestamp=goodTs)]
                            else:
                                logging.info(" \t -> date is lower than min date or higher than max date")

        return urlObj

    def filterUrls(self, links=[], urlBase="https://www.lavanguardia.com{}"):
        auxFinalLinks = list(dict.fromkeys([link for link in links
                                            if "lavanguardia" in link
                                            and link.endswith("html")
                                            and not "cookies_privacy_LV_popup.html" in link
                                            and not "lavanguardia.com/servicios/bolsa" in link]))
        finalLinks = []
        for l in auxFinalLinks:
            if l.startswith("http"):
                finalLinks.append(l)
            elif l.startswith("//"):
                finalLinks.append("https:{}".format(l))
            else:
                finalLinks.append(urlBase.format(l))

        logging.info(" -> TOtal of url retrieved to extract comments: {}".format(len(finalLinks)))
        logging.info(
            "==================================================================================================")
        return list(dict.fromkeys(finalLinks))

    def extractComments(self, commentsList=None, authorObjectList=None, urlNoticia=None, specialCase=None):
        logging.info(" \t -> parsing comments list with -{}- elements:".format(len(commentsList)))
        parsedComments = []
        listToParse = commentsList[1] if specialCase else commentsList
        for commentObj in listToParse:
            contentObj = commentObj.get("content", None)
            isValidContent = "bodyHtml" in contentObj.keys()
            if isValidContent:
                fechaObj = datetime.fromtimestamp(contentObj["createdAt"])
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

    def lookupForComments(self, renderedPageHtml=None, url=None):
        commendInfoKeysElArr = renderedPageHtml.xpath("//label[@class='livefyre-commentcount']")
        pageComments = []
        if len(commendInfoKeysElArr) > 0:
            commentInfoEl = commendInfoKeysElArr[0]
            commentSiteId = commentInfoEl.get("data-lf-site-id")
            commentArticleId = commentInfoEl.get("data-lf-article-id")
            if (commentSiteId != "" and commentArticleId != ""):
                logging.info(" \t-> data-lf-site-id to get comments is: {}".format(commentSiteId))
                logging.info(" \t-> data-lf-article-id to get comments is: {}".format(commentArticleId))

                # Get Comments Info
                urlParam = "{}:{}".format(commentSiteId, commentArticleId)
                urlParamBase64 = str(base64.b64encode(urlParam.encode("utf-8")), "utf-8")
                commentElArticleIdEncoded = str(base64.b64encode(commentArticleId.encode("utf-8")), "utf-8")
                urlInfoCommentsEncoded = self._urlInfoComments.format(commentSiteId, commentElArticleIdEncoded)
                logging.info(" \t-> getting information for article: {}".format(urlInfoCommentsEncoded))
                responseInfoComments = requests.get(urlInfoCommentsEncoded)
                infoComments = json.loads(responseInfoComments.text)
                if "collectionSettings" in infoComments and \
                        infoComments["collectionSettings"]["numVisible"] > 0:
                    # La info dice que hay comentarios, se procede a obtenerlos
                    pages = infoComments["collectionSettings"]["archiveInfo"]["nPages"]
                    logging.info(" \t-> total of comments for current article: {}".format(
                        infoComments["collectionSettings"]["numVisible"]))
                    logging.info(" \t-> total of pages for current article: {}".format(pages))

                    for page in range(pages):
                        urlGetCommentsEncoded = self._urlGetComments.format(commentSiteId, commentElArticleIdEncoded, page)
                        logging.info(" \t -> getting comments with url: {}".format(urlGetCommentsEncoded))
                        responseComments = requests.get(urlGetCommentsEncoded)
                        if responseComments.status_code != 200:
                            logging.info(" \t -> status code in latest request returned {}".format(responseComments.status_code))
                            logging.info(" \t -> response returned: \n {}".format(responseComments))
                            logging.info(" \t ==>> sleep while few seconds ")
                            time.sleep(5)
                            responseComments = requests.get(urlGetCommentsEncoded)

                        commentsResponse = json.loads(responseComments.text)
                        pageComments = pageComments + self.extractComments(commentsResponse['content'],
                                                                      commentsResponse['authors'], url)
                else:
                    logging.info(" \t -> no comments info found, pages without comments")
        logging.info(" \t -> retrieved total of {} comments".format(len(pageComments)))
        logging.info(
            "#############################################################################################")
        return pageComments

    def get_title(self, renderedPage=None, url=None):
        queryXpath = "//article//h1"
        el = renderedPage.xpath(queryXpath)
        title = url
        if len(el) == 0:
            print(" -> title not found in: {}".format(url))
        else:
            title = el[0].text
        return title

    def extractContent(self, renderedPage=None, url=None):
        queries_xpath = ["//div[@class='content-structure ']//p",
                         "//div[@itemprop='articleBody']//p"]
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
            print("\t -> url has not content found {}".format(url))

        title = self.get_title(renderedPage, url)
        content = {
            "url": url,
            "content": contentStr,
            "title": title
        }
        return [content]
