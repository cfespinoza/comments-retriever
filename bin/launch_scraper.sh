#!/bin/bash -e

result_dir=${1:?"Es necesario que se establezca la ruta absoluta del directorio en el sistema de ficheros local donde se almacenarán los resultados. Por ejemplo: /var/data"}
imagen_docker=${2:-scrapper:v1}
inicio_offset=${3:-"4 day ago"}
fin_offset=${4:-"3 day ago"}

lista_medios=("lavanguardia" "elmundo" "abc" "20minutos" "elpais")

echo " "
echo "-> ruta de resultados establecida: ${result_dir}"
echo " "
echo "-> desplazamiento para la fecha de inicio: ${inicio_offset}"
echo "-> desplazamiento para la fecha de fin: ${fin_offset}"
echo " "
echo "-> calculando fechas... "
inicio=$(date +%d/%m/%Y -d "${inicio_offset}")
echo " # -> fecha de inicio: ${inicio} "
fin=$(date +%d/%m/%Y -d "${fin_offset}")
echo " # -> fecha de fin: ${fin} "
echo " "
echo "-> fechas calculadas: "
echo " Inicio: ${inicio}"
echo " Fin: ${fin}"
echo " "

for medio in ${lista_medios[*]}
do
  echo "______________________________________________________________________________________________________________"
  echo " -> medio: ${medio}"
  comando="scrapper -b ${inicio} -e ${fin} -m ${medio} -r ${result_dir}"
  echo " -> comando a ejecutar: ${comando}"
  result_exec=$comando
  if [[ ! ${result_exec} -eq 0 ]]; then
    echo " WARNING: la ejecucion parece haber acabado con errores, revisen los logs"
  fi
  echo " -> extraccion de comentarios y contenidos para -${medio}- finalizado"
  echo " "
done