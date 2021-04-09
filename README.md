# Analyse av dørdata

Inneholder følgende filer:

* `door.csv`: rådata fra november 2014 til november 2017
* `door_stats.py`: kode for å ekstrahere og behandle data fra door.csv
* `door_plots.py`: kode for å plotte data fra door.csv

Avhengigheter:

* python >= 3.6
* numpy >= 1.12.1
* matplotlib >= 3.1.0
* LaTeX (valgfritt, brukes til plotting hvis det er installert)

For å plotte alt samtidig, kjør `python door_plots.py`. For å gjøre noe annet enn det, importer `door_stats` eller `door_plots` i et nytt skript og hent ut det du trenger

![plot](https://raw.githubusercontent.com/jonathangjertsen/door_analysis/master/plots.png)
