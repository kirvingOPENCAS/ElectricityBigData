import happybase
import math

host='172.20.111.54'
connection=happybase.Connection(host,autoconnect=False)
connection.open()
intRes=connection.table('intRes')

longitude_start=122.2
longitude_end=156.6
lagitude_start=22.2
lagitude_end=34.2
stepLongitude=6.88
stepLagitude=4.0


query_time_start='2016-03-01 01:00:00'
query_time_end='2016-03-01 08:00:00'
query_longitude_start=124
query_longitude_end=155
query_lagitude_start=24
query_lagitude_end=30

if query_longitude_start<longitude_start or \
    query_longitude_end>longitude_end or \
    query_lagitude_start<lagitude_start or \
    query_lagitude_end>lagitude_end:
    print 'the query area is out of range! program exit!'
    exit()

realStaLon=math.floor((query_longitude_start-longitude_start)/stepLongitude)*stepLongitude+longitude_start
realEndLon=math.floor((query_longitude_end-longitude_start)/stepLongitude)*stepLongitude+longitude_start
realStaLag=math.floor((query_lagitude_start-lagitude_start)/stepLagitude)*stepLagitude+lagitude_start
realEndLag=math.floor((query_lagitude_end-lagitude_start)/stepLagitude)*stepLagitude+lagitude_start

str_row_start="'"+query_time_start+'-'+str(realStaLon)+'-'+str(realStaLag)+"'"
str_row_stop="'"+query_time_end+'-'+str(realEndLon)+'-'+str(realEndLag)+"'"

Data=[]

for key,data in intRes.scan(row_start=str_row_start,row_stop=str_row_stop):
     Data.append((key,data))

