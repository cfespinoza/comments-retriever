import csv
import json
import logging
from datetime import date, datetime, timedelta

from PyQt5 import QtCore, QtWidgets, QtWebEngineWidgets
from lxml import html as htmlRenderer


class BasicScrapper(QtWebEngineWidgets.QWebEnginePage):

    def __init__(self):
        super(BasicScrapper, self).__init__()
        self._commentsPerDay = []
        self._contentPerDay = []
        self._processedUrls = []
        self._newsUrlsPerDayObj = {}
        self._urlsPerDayObj = {}
        self._newsPerDayUrls = []
        self._datesArr = []
        self._historicalRootUrl = ""
        self._media = ""
        self._initPeriod = ""
        self._endPeriod = ""
        self._period = ""
        self._rootPath = ""
        self._currentDateKey = ""
        self._urlInfoComments = ""
        self._urlGetComments = ""
        self._urlXpathQuery = ""
        self._baseUrls = []
        self._GET_URLS_STATE = "getUrls"
        self._GET_COMMENTS_STATE = "getComments"
        self._currentStage = self._GET_URLS_STATE
        self.loadFinished.connect(self.handleLoadFinished)

    def start(self, historicalRootUrl,
              media, initPeriod, endPeriod, rootPath, dateFormatStr, hemerotecaExtraInfo=[]):
        self._historicalRootUrl = historicalRootUrl
        self._media = media
        self._initPeriod = initPeriod
        self._endPeriod = endPeriod
        self._dateFormat = dateFormatStr
        self._rootPath = rootPath
        self._datesArr = self.generateDates(start=initPeriod, end=endPeriod, delta=1, dateFormat=self._dateFormat)
        self._datesIt = iter(self._datesArr)
        self._urlsPerDayObj = self.generateHemerotecaUrls(self._historicalRootUrl, self._datesArr, hemerotecaExtraInfo)
        logging.basicConfig(filename="{}-{}.log".format(self._media, datetime.today().strftime("%H%M%S")),
                            level=logging.INFO)
        self.exportData(self._urlsPerDayObj, self._period, "webpages-per-day", "json")
        self.fetchNext()

    def fetchNext(self):
        if self._currentStage == self._GET_URLS_STATE:
            try:
                if self._currentDateKey == "":
                    self._currentDateKey = next(self._datesIt)
                    self._urlsPerDayIt = iter(self._urlsPerDayObj.get(self._currentDateKey, []))
                    self._newsUrlsPerDayObj[self._currentDateKey] = []

                # => iterate in urls per day
                url = next(self._urlsPerDayIt)
            except StopIteration:
                try:
                    self._currentDateKey = next(self._datesIt)
                    self._urlsPerDayIt = iter(self._urlsPerDayObj.get(self._currentDateKey, []))
                    self._newsUrlsPerDayObj[self._currentDateKey] = []
                    url = next(self._urlsPerDayIt)
                except StopIteration:
                    # => in case of this code, proccessing datesIt has finished
                    #   it is time to change to next stage
                    self._currentStage = self._GET_COMMENTS_STATE
                    self.exportData(self._newsUrlsPerDayObj, self._period, "news-links-per-day", "json")
                    self._datesIt = iter(self._datesArr)
                    self._currentDateKey = next(self._datesIt)
                    self._urlsPerDayIt = iter(self._newsUrlsPerDayObj.get(self._currentDateKey, []))
                    url = next(self._urlsPerDayIt)
                    self.load(QtCore.QUrl(url))
                else:
                    self.load(QtCore.QUrl(url))
            else:
                self.load(QtCore.QUrl(url))

        elif self._currentStage == self._GET_COMMENTS_STATE:
            try:
                # => iterate in urls per day, but in this case it is extracting url news
                url = next(self._urlsPerDayIt)
            except StopIteration:
                try:
                    # => at this point, all news per day has been retrieved,
                    # it is time to change of day and export collected info
                    # comments
                    self.exportData(self._commentsPerDay, self._currentDateKey, "comments", "json")
                    self.exportData(self._commentsPerDay, self._currentDateKey, "comments", "csv")
                    # contents
                    self.exportData(self._contentPerDay, self._currentDateKey, "contents", "json")
                    self.exportData(self._contentPerDay, self._currentDateKey, "contents", "csv")
                    del (self._contentPerDay)
                    del (self._commentsPerDay)

                    # reset local variables
                    self._contentPerDay = []
                    self._commentsPerDay = []

                    self._currentDateKey = next(self._datesIt)
                    self._urlsPerDayIt = iter(self._newsUrlsPerDayObj.get(self._currentDateKey, []))
                    url = next(self._urlsPerDayIt)
                except StopIteration:
                    # => in case of this code, proccessing datesIt has finished
                    #   it is time to finish
                    # comments
                    self.exportData(self._commentsPerDay, self._currentDateKey, "comments", "json")
                    self.exportData(self._commentsPerDay, self._currentDateKey, "comments", "csv")
                    # contents
                    self.exportData(self._contentPerDay, self._currentDateKey, "comments", "json")
                    self.exportData(self._contentPerDay, self._currentDateKey, "comments", "csv")
                    return False
                else:
                    self.load(QtCore.QUrl(url))
            else:
                self.load(QtCore.QUrl(url))
        else:
            # State not supported
            return False
        return True

    def processCurrentPage(self, html):
        url = self.url().toString()
        logging.info(" -> trying to render url: {}".format(url))
        if html != "":
            renderedPage = htmlRenderer.fromstring(html)

            if (self._currentStage == self._GET_URLS_STATE):
                # in this stage the program is trying to extract urls for news
                logging.debug(" -> processing base URL: {}".format(url))
                auxLinks = renderedPage.xpath(self._urlXpathQuery)
                # filter urls
                finalLinks = self.filterUrls(links=auxLinks)
                logging.debug(" -> TOtal of url retrieved to extract comments: {}".format(len(finalLinks)))
                logging.debug(
                    "==================================================================================================")
                self._newsUrlsPerDayObj[self._currentDateKey] = self._newsUrlsPerDayObj[
                                                                    self._currentDateKey] + finalLinks

            elif (self._currentStage == self._GET_COMMENTS_STATE):
                logging.debug(" -> url will be processed to extract content and comments: {}".format(url))
                logging.debug(" -> url to extract comments: {}".format(url))
                commentsFound = self.lookupForComments(renderedPage, url)
                if len(commentsFound) > 0:
                    self._commentsPerDay = self._commentsPerDay + commentsFound
                    logging.debug(" -> url to extract content: {}".format(url))
                    self._contentPerDay = self._contentPerDay + self.extractContent(renderedPage, url)
                logging.debug(" -> url has been processed: {}".format(url))

            else:
                logging.error(" -> Something went wrong... application will be shutted down.")
                QtWidgets.qApp.quit()
        else:
            logging.warning(" -> Something is wrong. Empty html retrieved from url {}".format(url))

        # clear history in order to trying to avoid memory leak
        self.history().clear()

        if not self.fetchNext():
            QtWidgets.qApp.quit()

    def handleLoadFinished(self):
        self.toHtml(self.processCurrentPage)

    ####################################################################
    #################### helper functions
    ####################################################################
    def _generateDates(self, init=date(2019, 1, 1), end=date(2019, 8, 31), delta=timedelta(days=1), strFormat=""):
        curr = init
        dates = []
        while curr <= end:
            if strFormat == "":
                dates.append(str(curr))
            else:
                dates.append(curr.strftime(strFormat))
            curr += delta
        return dates

    def exportData(self, data=None, dayData=None, typeData=None, format=None):
        today = date.today()
        currentDay = today.strftime("%d%m%Y")
        formattedDay = dayData.replace("/","-") if "/" in dayData else dayData
        fileName = "{rootPath}/{media}/{dataDay}-{dataType}.{fileFormat}".format(
            rootPath=self._rootPath,
            today=currentDay,
            media=self._media,
            dataDay=formattedDay,
            dataType=typeData,
            fileFormat=format)
        logging.info(" \t data will be exported in {}".format(format))
        if format == "csv":
            with open(fileName, "w") as file:
                csvwriter = csv.writer(file)
                count = 0
                for dataObj in data:
                    if count == 0:
                        header = dataObj.keys()
                        csvwriter.writerow(header)
                        count += 1
                    csvwriter.writerow(dataObj.values())
        elif format == "json":
            with open(fileName, "w") as file:
                json.dump(data, file)
        else:
            logging.error(" \t {} format not supported".format(format))
        logging.debug(" \t -> exported data fileName: {}".format(fileName))

    ####################################################################
    ############ Method to be implemented for children classes
    ####################################################################
    def initialize(self, begin="", end="", rootPath=None):
        raise NotImplementedError("Method must be implemented in subclass")

    def generateDates(self, start="", end="", delta=1, dateFormat="%Y/%m/%-d"):
        # this method should call to self._generateDate
        raise NotImplementedError("Method must be implemented in subclass")

    def generateHemerotecaUrls(self, urlBase=None, dates=None, extraInfo=None):
        # it should return and object
        # {
        #   "<day": [<linksOfNewsPerDay>]
        # }
        raise NotImplementedError("Method must be implemented in subclass")

    def filterUrls(self, links=None, urlBase=None):
        raise NotImplementedError("Method must be implemented in subclass")

    def extractComments(self, commentsList=None, urlNoticia=None, specialCase=None):
        raise NotImplementedError("Method must be implemented in subclass")

    def lookupForComments(self, renderedPageHtml=None, url=None):
        raise NotImplementedError("Method must be implemented in subclass")

    def extractContent(self, renderedPage=None, url=None):
        raise NotImplementedError("Method must be implemented in subclass")
