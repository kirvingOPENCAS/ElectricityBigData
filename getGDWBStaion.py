#coding utf-8
import csv
import sys
reload(sys)
sys.setdefaultencoding('utf-8')
csvfile=file("/home/hadoop/20160120152132BDC_WM_MDATA.csv",'rb')
reader=csv.reader(csvfile)
stationList={}
for line in reader:
    if line[2] not in stationList:

        newLine=[line[9].decode('gb2312'),line[10].decode('gb2312'),line[11].decode('gb2312')]
        stationList[line[2]]=newLine
    #print line[9].decode('gb2312')
    #print ','.join(line).decode('gb2312')

csvfile.close()

station=open("GDweatherStation.txt","w+")
for key in stationList:
    station.write(key+' ')

    for loc in stationList[key]:
        station.write(loc+' ')
    station.write('\n')
station.close()
print 'total station: ',len(stationList)