#!/bin/bash -e

for i in "$@"
do
case $i in
    -i=*|--imagen_docker=*)
    imagen_docker="${i#*=}"
    echo " > imagen_docker: ${imagen_docker} "
    ;;
    -b=*|--begin_offset=*)
    inicio_offset="${i#*=}"
    echo " > inicio_offset: ${inicio_offset} "
    ;;
    -r=*|--result_dir=*)
    result_dir="${i#*=}"
    echo " > result_dir: ${result_dir} "
    ;;
    -e=*|--end_offset=*)
    fin_offset="${i#*=}"
    echo " > fin_offset: ${fin_offset} "
    ;;
    *)
    ;;
esac
done

result_dir=${result_dir:?"Es necesario que se establezca la ruta absoluta del directorio en el sistema de ficheros local donde se almacenarán los resultados. Por ejemplo: ./launch_docker_scraper.sh -r /var/data"}
imagen_docker=${imagen_docker:-scrapper:v1}
inicio_offset=${inicio_offset:-"4 day ago"}
fin_offset=${fin_offset:-"3 day ago"}

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
  comando="docker run -it --rm -v ${result_dir}:/results -e BEGIN=${inicio} -e END=${fin} -e MEDIA=${medio} ${imagen_docker}"
  echo " -> comando a ejecutar: ${comando}"
  $comando
  echo " -> extraccion de comentarios y contenidos para -${medio}- finalizado"
  echo " "
done