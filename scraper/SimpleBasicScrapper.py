import csv
import json
import logging
import os
import sys
from datetime import date, datetime, timedelta

import requests
from lxml import html as htmlRenderer


class SimpleScrapper():

    def __init__(self):
        super(SimpleScrapper, self).__init__()
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
        self._NEWS_LINKS_PER_DAY = "news-links-per-day"
        self._currentStage = self._GET_URLS_STATE
        self._currentUrl = ""

    def start(self, historicalRootUrl,
              media, initPeriod, endPeriod, rootPath, dateFormatStr, hemerotecaExtraInfo=[]):
        self._historicalRootUrl = historicalRootUrl
        self._media = media
        self._initPeriod = initPeriod
        self._endPeriod = endPeriod
        self._dateFormat = dateFormatStr
        self._rootPath = rootPath

        self._period = "{}-{}".format(initPeriod.replace("/", ""), endPeriod.replace("/", ""))
        self.initializeObject(initPeriod, endPeriod, hemerotecaExtraInfo)
        self.processCurrentPage()

    def fetchNext(self):
        if self._currentStage == self._GET_URLS_STATE:
            try:
                if self._currentDateKey == "":
                    self._currentDateKey = next(self._datesIt)
                    self._urlsPerDayIt = iter(self._urlsPerDayObj.get(self._currentDateKey, []))
                    self._newsUrlsPerDayObj[self._currentDateKey] = []

                # => iterate in urls per day
                self._currentUrl = next(self._urlsPerDayIt)
            except StopIteration:
                try:
                    self._currentDateKey = next(self._datesIt)
                    self._urlsPerDayIt = iter(self._urlsPerDayObj.get(self._currentDateKey, []))
                    self._newsUrlsPerDayObj[self._currentDateKey] = []
                    self._currentUrl = next(self._urlsPerDayIt)
                except StopIteration:
                    # => in case of this code, proccessing datesIt has finished
                    #   it is time to change to next stage
                    self._currentStage = self._GET_COMMENTS_STATE
                    self.exportData(self._newsUrlsPerDayObj, self._period, self._NEWS_LINKS_PER_DAY, "json")
                    self._datesIt = iter(self._datesArr)
                    self._currentDateKey = next(self._datesIt)
                    # initialize variable for the next stage
                    self._urlsPerDayIt = iter(
                        list(dict.fromkeys(self._newsUrlsPerDayObj.get(self._currentDateKey, []))))
                    self._currentUrl = next(self._urlsPerDayIt)
                else:
                    return True
            else:
                return True

        elif self._currentStage == self._GET_COMMENTS_STATE:
            try:
                # => iterate in urls per day, but in this case it is extracting url news
                self._currentUrl = next(self._urlsPerDayIt)
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
                    self._urlsPerDayIt = iter(
                        list(dict.fromkeys(self._newsUrlsPerDayObj.get(self._currentDateKey, []))))
                    self._currentUrl = next(self._urlsPerDayIt)
                except StopIteration:
                    # => in case of this code, proccessing datesIt has finished
                    #   it is time to finish
                    return False
                else:
                    return True
            else:
                return True
        else:
            # State not supported
            return False
        return True

    def initializeObject(self, initPeriod="", endPeriod="", hemerotecaExtraInfo=[]):
        if self.existsNewsPerDayFile():
            self.loadNewsPerDayFile()
        else:
            self._datesArr = self.generateDates(start=initPeriod, end=endPeriod, delta=1, dateFormat=self._dateFormat)
            self._datesIt = iter(self._datesArr)
            self._urlsPerDayObj = self.generateHemerotecaUrls(self._historicalRootUrl, self._datesArr, hemerotecaExtraInfo)
            self.exportData(self._urlsPerDayObj, self._period, "webpages-per-day", "json")

    def existsNewsPerDayFile(self):
        filename = self.getFilename(self._period, self._NEWS_LINKS_PER_DAY, "json")
        return os.path.isfile(filename)

    def loadNewsPerDayFile(self):
        filename = self.getFilename(self._period, self._NEWS_LINKS_PER_DAY, "json")
        logging.info(" \t -> trying to load newsPerDayFile from path {}".format(filename))
        with open(filename, 'r') as f:
            self._newsUrlsPerDayObj = json.load(f)
            self._datesArr = list(self._newsUrlsPerDayObj.keys())
            self._datesIt = iter(self._datesArr)
            self._currentDateKey = next(self._datesIt)
            self._urlsPerDayIt = iter(list(dict.fromkeys(self._newsUrlsPerDayObj.get(self._currentDateKey, []))))
            self._currentStage = self._GET_COMMENTS_STATE
        logging.info(" \t -> newsPerDayFile has been loaded from path {}".format(filename))

    def processCurrentPage(self):
        while self.fetchNext():
            logging.info(" -> trying to render url: {}".format(self._currentUrl))
            html = requests.get(self._currentUrl)
            if html.text != "":
                renderedPage = htmlRenderer.fromstring(html.text)

                if (self._currentStage == self._GET_URLS_STATE):
                    # in this stage the program is trying to extract urls for news
                    logging.debug(" -> processing base URL: {}".format(self._currentUrl))
                    auxLinks = renderedPage.xpath(self._urlXpathQuery)
                    # filter urls
                    finalLinks = self.filterUrls(links=auxLinks)
                    logging.debug(" -> TOtal of url retrieved to extract comments: {}".format(len(finalLinks)))
                    logging.debug(
                        "==================================================================================================")
                    self._newsUrlsPerDayObj[self._currentDateKey] = self._newsUrlsPerDayObj[
                                                                        self._currentDateKey] + finalLinks

                elif (self._currentStage == self._GET_COMMENTS_STATE):
                    logging.debug(
                        " -> url will be processed to extract content and comments: {}".format(self._currentUrl))
                    logging.debug(" -> url to extract comments: {}".format(self._currentUrl))
                    commentsFound = self.lookupForComments(renderedPage, self._currentUrl)
                    if len(commentsFound) > 0:
                        self._commentsPerDay = self._commentsPerDay + commentsFound
                        logging.debug(" -> url to extract content: {}".format(self._currentUrl))
                        self._contentPerDay = self._contentPerDay + self.extractContent(renderedPage, self._currentUrl)
                    logging.debug(" -> url has been processed: {}".format(self._currentUrl))

                else:
                    logging.error(
                        " -> Something went wrong due to state {} is not recognized... application will be shutted down.".format(
                            self._currentStage))
                    sys.exit(-1)
            else:
                logging.warning(" -> Something is wrong. Empty html retrieved from url {}".format(self._currentUrl))

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

    def getFilename(self, dayData=None, typeData=None, format=None):
        formattedDay = dayData.replace("/", "-") if "/" in dayData else dayData
        fileName = "{rootPath}/{media}/{dataDay}-{dataType}.{fileFormat}".format(
            rootPath = self._rootPath,
            media = self._media,
            dataDay = formattedDay,
            dataType = typeData,
            fileFormat = format)
        return fileName

    def exportData(self, data=None, dayData=None, typeData=None, format=None):
        fileName = self.getFilename(dayData, typeData, format)
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
