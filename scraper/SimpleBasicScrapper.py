"""
Clase principal que define la interfaz de los scrappers. Es la clase padre de la que hereadan cada scrapper hijo
(por medio de comunicación).
Esta clase también se encarga de lleva la lógica del proceso de extracción de comentarios. Este proceso pasa por 3 estados

"getUrls" -> estado inicial desde el que se inicia el proceso de scrapping. Este estado se encargará de obtener las urls
de las noticias de las que se van a extraer los comentarios. Para esto recorrerrá las webs de hemeroteca o archivos del medio
para extraer las noticas por día entre el período que se haya definido como argumento al ejecutar el programa. Como resultado
de este estado se vuelcan estos url obtenidos en dos json:
    <ruta_de_resultados>/webpages-per-day.json  -> urls de archivo o hemeroteca para extraer las urls noticias por día
    <ruta_de_resultados>/news-links-per-day     -> urls de noticias por día.

"getComments"   -> estado siguiente al de "getUrls" y al que se llega una vez se hayan extraído las urls para todos los
días. En este estado se recorre el json de las urls de noticias por día y se empieza el proceso de extracción de
comentario por cada medio. Al acabar la extracción de comentarios por día se almacenan dos json por día.
     <ruta_de_resultados>/<formato_de_fecha_del_medio>-comments.json
     <ruta_de_resultados>/<formato_de_fecha_del_medio>-content.json

"commentsRetrieved"     -> en este estado se han terminado de extraer los comentarios y se procede a la exportación y
generación de los csv finales
"""

import csv
import json
import logging
import os
import sys
from datetime import date, timedelta

import requests
from lxml import html as htmlRenderer


class SimpleScrapper():

    def __init__(self):
        """Constructor por defectos
        Función que encargada de inicializar parámetros comunes a todos los scrappers que extiendan la clase.
        No espera argumentos.
        """
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
        self._COMMENTS_RETRIEVED_STATE = "commentsRetrieved"
        self._NEWS_LINKS_PER_DAY = "news-links-per-day"
        self._currentStage = self._GET_URLS_STATE
        self._currentUrl = ""
        self.logger = logging.getLogger(self.__class__.__name__)

    def start(self, historicalRootUrl,
              media, initPeriod, endPeriod, rootPath, dateFormatStr, hemerotecaExtraInfo=[]):
        """Ejecuta el inicio del proceso de scrapping
        Sus argumentos tienen que ser establecidos desde la clase que la extienda ya que son parámetros que dependen
        del medio que se va a procesar.

        :param historicalRootUrl: url desde donde se extraerán las url por cada día
        :param media: nombre del medio que se va a hacer scrapping
        :param initPeriod:  inicio del período
        :param endPeriod: fin del período
        :param rootPath: ruta del directorio donde se va a almacenar los resultados
        :param dateFormatStr: fomato de fecha que se aplica para el medio
        :param hemerotecaExtraInfo: información extra que se necesite para obtener las url de hemroteca desde donde se
            se extraen las noticias por día

        """
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
        """Función encargada de establece la siguiente url a procesar, ya se para extraer url de noticias o comentarios,
        esto está controlado los distintos estados en el que se encuentre el programa

        :return: True si aún quedan url por procesar, False en caso de que se haya acabado de procesar las url
        """
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
                    if len(list(dict.fromkeys(self._newsUrlsPerDayObj))) == 0:
                        self.logger.warning("no news link obtained. The process is aborted")
                        return False
                    else:
                        self.logger.debug("{} days with news".format(len(list(dict.fromkeys(self._newsUrlsPerDayObj)))))
                        dataToExport = {key: self._newsUrlsPerDayObj.get(key) for key in
                                        list(self._newsUrlsPerDayObj.keys()) if
                                        len(self._newsUrlsPerDayObj.get(key)) > 0}
                        self.logger.debug("{} days with news after remove days without any url".format(
                            len(list(dict.fromkeys(dataToExport)))))
                        self._newsUrlsPerDayObj = dataToExport

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
                self.logger.info("retrieving comments from day: {}".format(self._currentDateKey))
                self._currentUrl = next(self._urlsPerDayIt)
            except StopIteration:
                try:
                    # => at this point, all news per day has been retrieved,
                    # it is time to change of day and export collected info
                    # comments
                    self.exportData(self._commentsPerDay, self._currentDateKey, "comments", "json")
                    # self.exportData(self._commentsPerDay, self._currentDateKey, "comments", "csv")
                    # contents
                    self.exportData(self._contentPerDay, self._currentDateKey, "contents", "json")
                    # self.exportData(self._contentPerDay, self._currentDateKey, "contents", "csv")
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
        elif self._currentStage == self._COMMENTS_RETRIEVED_STATE:
            self.logger.info("state detected: {}".format(self._currentStage))
            self.logger.info("nothing to process due to it seems comments and contents files have been downloaded "
                             "previously for period: {}".format(self._period))
            return False
        else:
            # State not supported
            return False
        return True

    def initializeObject(self, initPeriod="", endPeriod="", hemerotecaExtraInfo=[]):
        """Función encargada de determinar inicializar objetos de control. Checkea en caso de existir un fichero con
        con los links de las noticias por día lo carga y así evita tener que obtenerlos de nuevo de la hemeroteca o
        archivo. O en caso de no existir inicializa objetos para procesar la hemeroteca

        :param initPeriod: inicio del período de extracción de comentarios
        :param endPeriod: fin del período de extracción de comentarios
        :param hemerotecaExtraInfo: Array libre que la función "generateHemerotecaUrls" tiene que saber cómo explotar.
        :return:
        """
        if self.existsNewsPerDayFile():
            self.loadNewsPerDayFile()
        else:
            self._datesArr = self.generateDates(start=initPeriod, end=endPeriod, delta=1, dateFormat=self._dateFormat)
            self._urlsPerDayObj = self.generateHemerotecaUrls(self._historicalRootUrl, self._datesArr,
                                                              hemerotecaExtraInfo)
            self._datesArr = list(self._urlsPerDayObj.keys())
            self._datesIt = iter(self._datesArr)
            self.exportData(self._urlsPerDayObj, self._period, "webpages-per-day", "json")

    def existsNewsPerDayFile(self):
        """Función auxiliar que checkea la existencia del fichero de noticias por día para evitar tener que obtenerlo
        de la hemeroteca o archivo.
        :return: True en caso de encontrar un fichero con las url de las noticias por día
            (<ruta_de_resultados>/news-links-per-day). False en caso contrario
        """
        filename = self.getFilename(self._period, self._NEWS_LINKS_PER_DAY, "json")
        return os.path.isfile(filename)

    def loadNewsPerDayFile(self):
        """Función que se encarga de cargar el fichero de noticias por día
        :return:
        """
        filename = self.getFilename(self._period, self._NEWS_LINKS_PER_DAY, "json")
        self.logger.info("trying to load newsPerDayFile from path {}".format(filename))
        with open(filename, 'r') as f:
            self._newsUrlsPerDayObj = json.load(f)
            self._datesArr = list(self._newsUrlsPerDayObj.keys())
            self._datesIt = iter(self._datesArr)
            self._currentDateKey = next(self._datesIt)
            comments_file = self.getFilename(self._currentDateKey, "comments", "json")
            contents_file = self.getFilename(self._currentDateKey, "contents", "json")
            still_search = True
            while os.path.isfile(comments_file) and os.path.isfile(contents_file) and still_search:
                self.logger.info("comments file found: {}".format(comments_file))
                self.logger.info("contents file found: {}".format(contents_file))
                try:
                    self._currentDateKey = next(self._datesIt)
                    comments_file = self.getFilename(self._currentDateKey, "comments", "json")
                    contents_file = self.getFilename(self._currentDateKey, "contents", "json")
                except StopIteration:
                    self.logger.warning("files found for whole period. ")
                    self._currentStage = self._COMMENTS_RETRIEVED_STATE
                    self._currentDateKey = None
                    still_search = False
            self._urlsPerDayIt = iter(list(
                dict.fromkeys(self._newsUrlsPerDayObj.get(self._currentDateKey,
                                                          [])))) if self._currentDateKey else [] if self._currentDateKey else []
            self._currentStage = self._GET_COMMENTS_STATE if self._currentDateKey else self._COMMENTS_RETRIEVED_STATE
        self.logger.info("newsPerDayFile has been loaded from path {}".format(filename))

    def processCurrentPage(self):
        """Función principal que se encarga de lanzar el proceso de scraping. Y controlar la correcta ejecución dependiendo
        del estado actual en el que se encuentre el proceso.
        :return:
        """
        while self.fetchNext():
            self.logger.info("trying to render url: {}".format(self._currentUrl))
            html = None
            try:
                html = requests.get(self._currentUrl)
            except Exception as e:
                self.logger.error(str(e))
                self.logger.error("there was an error while making request to {}".format(self._currentUrl))
                self.logger.error("Url -{}- will not be processed".format(self._currentUrl))

            if html != None and html.text != "":
                renderedPage = htmlRenderer.fromstring(html.text)

                if (self._currentStage == self._GET_URLS_STATE):
                    # in this stage the program is trying to extract urls for news
                    self.logger.debug("processing base URL: {}".format(self._currentUrl))
                    auxLinks = renderedPage.xpath(self._urlXpathQuery)
                    # filter urls
                    finalLinks = self.filterUrls(links=auxLinks)
                    self.logger.debug("TOtal of url retrieved to extract comments: {}".format(len(finalLinks)))
                    self.logger.debug(
                        "==================================================================================================")
                    self._newsUrlsPerDayObj[self._currentDateKey] = self._newsUrlsPerDayObj[
                                                                        self._currentDateKey] + finalLinks

                elif (self._currentStage == self._GET_COMMENTS_STATE):
                    self.logger.debug(
                        "url will be processed to extract content and comments: {}".format(self._currentUrl))
                    self.logger.debug("url to extract comments: {}".format(self._currentUrl))
                    commentsFound = self.lookupForComments(renderedPage, self._currentUrl)
                    if len(commentsFound) > 0:
                        self._commentsPerDay = self._commentsPerDay + commentsFound
                        self.logger.debug("url to extract content: {}".format(self._currentUrl))
                        self._contentPerDay = self._contentPerDay + self.extractContent(renderedPage, self._currentUrl)
                    self.logger.debug("url has been processed: {}".format(self._currentUrl))

                else:
                    self.logger.error(
                        "Something went wrong due to state {} is not recognized... application will be shutted down.".format(
                            self._currentStage))
                    sys.exit(-1)
            else:
                self.logger.warning("Something is wrong. Empty html retrieved from url {}".format(self._currentUrl))

    ####################################################################
    #################### helper functions
    ####################################################################
    def _generateDates(self, init=date(2019, 1, 1), end=date(2019, 8, 31), delta=timedelta(days=1), strFormat=""):
        """Genera las fechas entre el inicio y el final del período que se va a hacer el scrapping.

        :param init: inicio del período de scrapping
        :param end: inicio del período de scrapping
        :param delta: por defecto 1.
        :param strFormat: formato de fecha, lo determina el medio para el que se está ejecutando
        :return: lista de fechas formateadas acorde al medio
        """
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
        """Funcion auxiliar para generar el nombre de los ficheros que se van a crear
        :param dayData: día para le que se ha extraído la información del medio
        :param typeData: flag que determina si es comentarios o contenido
        :param format: formato del fichero que se va a crear
        :return: str. con el nombre del fichero que se va a crear
        """
        formattedDay = dayData.replace("/", "-") if "/" in dayData else dayData
        fileName = "{rootPath}/{media}/{dataDay}-{dataType}.{fileFormat}".format(
            rootPath=self._rootPath,
            media=self._media,
            dataDay=formattedDay,
            dataType=typeData,
            fileFormat=format)
        return fileName

    def exportData(self, data=None, dayData=None, typeData=None, format=None):
        """Función auxiliar que se encarga de hacer la creación de los ficheros una vez se haya terminado de procesar
        un día

        :param data: datos que va a contener el fichero
        :param dayData: día para le que se ha extraído la información del medio
        :param typeData: flag que determina si es comentarios o contenido
        :param format: formato del fichero que se va a crear

        """
        fileName = self.getFilename(dayData, typeData, format)
        self.logger.info("data will be exported in {}".format(format))
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
            self.logger.error("{} format not supported".format(format))
        self.logger.debug("exported data fileName: {}".format(fileName))

    def getDateFormat(self):
        """Función para obtener el formato de fecha que se aplica para el medio que lo esté ejecutando
        :return: formato de fecha que se aplica
        """
        return self._dateFormat

    ####################################################################
    ############ Method to be implemented for children classes
    ####################################################################
    def initialize(self, begin="", end="", rootPath=None):
        """Función a implementar por cada clase hija por medio. Cada una se encarga de inicializar los parámetros
        dependiendo de los mejores que le cuadren.
        :param begin: inicio del período de scrapping
        :param end: fin del período de scrapping
        :param rootPath: ruta del directorio donde se almacenarán los resultados.

        :return:
        """
        raise NotImplementedError("Method must be implemented in subclass")

    def generateDates(self, start="", end="", delta=1, dateFormat="%Y/%m/%-d"):
        """Función que se encarga de generar las fechas para cada medio y llamar a "self._generateDate"
        :param start: inicio del período de scrapping
        :param end: fin del período de scrapping
        :param delta: incremento, por defecto 1 día.
        :param dateFormat: formato de la fecha que mejor cuadre para el medio
        :return:
        """
        raise NotImplementedError("Method must be implemented in subclass")

    def generateHemerotecaUrls(self, urlBase=None, dates=None, extraInfo=None):
        """Fucnión encargada de generar las url de la hemeroteca de donde se extraerán las noticias.
        :param urlBase: Url de la hemeroteca del medio
        :param dates: array de fechas que para las que se extraerá la información
        :param extraInfo: información extra que se necesite para generar las url de acceso a las noticias por día
        :return: listado de urls por día
            # it should return and object that looks like:
            # {
            #   "<day": [<linksOfNewsPerDay>]
            # }
        """
        raise NotImplementedError("Method must be implemented in subclass")

    def filterUrls(self, links=None, urlBase=None):
        """Función encargada de seleccionar las urls de noticias de todas las que se encuentran en los medios.

        :param links: listado de urls obtenidos de un medio
        :param urlBase: url base del medio
        :return: listado de urls de noticias del medio
        """
        raise NotImplementedError("Method must be implemented in subclass")

    def extractComments(self, commentsList=None, urlNoticia=None, specialCase=None):
        """Funcion que se debe implementar en cada scrapper dependiendo del medio. Función que extrae comentarios de un
        listado de datos que se obtiene de los servidores del medio.

        :param commentsList: listado de comentarios a extraer
        :param urlNoticia: url de la noticia de la que se extrae comentario
        :param specialCase: flag que determina si el listado se debe tratar de manera especial
        :return: listado de comentarios ya extraídos
        """
        raise NotImplementedError("Method must be implemented in subclass")

    def lookupForComments(self, renderedPageHtml=None, url=None):
        """Función que implementa el flujo de extracción los comentarios desde la página web renderizada de una url de la
        noticia.
        :param renderedPageHtml: contiene la página web
        :param url: url de la noticia
        :return: devuelve el listado de comentarios para la noticia que se está procesando
        """
        raise NotImplementedError("Method must be implemented in subclass")

    def extractContent(self, renderedPage=None, url=None):
        """FUnción que extrae el contenido de la página web de una noticia

        :param renderedPageHtml: contiene la página web
        :param url: url de la noticia
        :return: devuelve el listado de comentarios para la noticia que se está procesando
        """
        raise NotImplementedError("Method must be implemented in subclass")

    def generateHemerotecaExtraInfo(self):
        """ Función auxiliar que genera información necesaria para la correcta construcción de las url de la hemeroteca
        o archivo

        :return:
        """
        raise NotImplementedError("Method must be implemented in subclass")

    def getTitle(self, renderedPage=None, url=None):
        """Función que se implementa por cada medio para extraer correctamente su título

        :param renderedPageHtml: contiene la página web
        :param url: url de la noticia
        :return: json que contiene la clave title con el título de la noticia
        """
        raise NotImplementedError("Method must be implemented in subclass")
