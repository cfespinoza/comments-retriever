"""
Este módulo se encarga de unificar los ficheros de comentarios y contenido que se han obtenido por cada día del período
de extracción y termina generando un csv de comentarios y contenido.
"""

import csv
import json
import os

DATE_FORMATS = {
    "20minutos": "%Y-%m-%-d",
    "elmundo": "%Y-%m-%d",
    "elpais": "%Y-%m-%d",
    "abc": "%d-%m-%Y",
    "lavanguardia": "%Y%m%d"
}


def export(fileName, data):
    """Escribe el csv en disco dejándolo en el directorio de resultados
    :param fileName: nombre del fichero que se generará
    :param data: datos a escribir en el fichero
    """
    with open(fileName, "w") as file:
        csvwriter = csv.writer(file)
        count = 0
        for dataObj in data:
            if count == 0:
                header = dataObj.keys()
                csvwriter.writerow(header)
                count += 1
            csvwriter.writerow(dataObj.values())


def loadJsons(files):
    """Lee el contenido de todos los json generados por cada día
    :param files: array de ficheros a leer para luego unificar su contenido en un único csv
    :return: array con los json leídos de los ficheros
    """
    all = []
    for f in files:
        if os.path.isfile(f):
            with open(f) as file:
                all = all + json.load(file)
        else:
            print(" \t -> file -{}- not found.".format(f))
    return all


def unify(begin, end, media, resultPath, scrapper):
    """Función de alto nivel que se encarga de lanzar el proceso de unificación de los ficheros
    :param begin: inicio del período de scrapping
    :param end: fin del período de scrapping
    :param media: medio del cual se hace el scrapping
    :param resultPath: resultados donde se van a almacenar los resultados finales
    :param scrapper: instancia del scrapper del medio que se usará para obtener el listado de fechas
    :return:
    """
    date_format = DATE_FORMATS[media]
    dates = scrapper.generateDates(start=begin, end=end, dateFormat=date_format)
    period = "{}-{}".format(begin.replace("/", ""), end.replace("/", ""))

    commentsFilesNames = ["{rootPath}/{media}/{date}-comments.json".format(rootPath=resultPath, media=media, date=d) for
                          d in dates]
    contentsFilesNames = ["{rootPath}/{media}/{date}-contents.json".format(rootPath=resultPath, media=media, date=d) for
                          d in dates]

    totalCommentsArr = loadJsons(commentsFilesNames)
    totalContentsArr = loadJsons(contentsFilesNames)

    comments_file_unified = "{rootPath}/{media}/{media}-{period}-comments.csv".format(rootPath=resultPath, media=media,
                                                                                      period=period)
    contents_file_unified = "{rootPath}/{media}/{media}-{period}-contents.csv".format(rootPath=resultPath, media=media,
                                                                                      period=period)
    export(comments_file_unified, totalCommentsArr)
    export(contents_file_unified, totalContentsArr)

    return comments_file_unified, contents_file_unified
