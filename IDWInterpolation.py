#get the geo location of the meteorological stations
#construct the raster according to the range of longitude and lagitude
#compute the distance of each point to each meteorological station then
#compute the inverse distance weight.

import pyhs2
import math
import time
import sys
import happybase

#connect hive database
def getStationInfo(host,port,database,user,password,authMechanism,partition):
    with pyhs2.connect(host=host,
                    port=port,
                    database=database,
                    user=user,
                    password=password,
                    authMechanism=authMechanism) as conn:
        with conn.cursor() as cur:
        #get the table which stores the geo info of the meteorological station
            sql="select sid,lon,lat from awsstationdesc where dt='"+partition+"'"
            cur.execute(sql)
        #cur.execute("select * from awsstationdesc")
            listStationInfo=cur.fetch()
            del listStationInfo[0]

    return listStationInfo

#access hive database to get data for interpolation
def getDataForInt():
    with pyhs2.connect(host='172.20.111.54',
                    port=10001,
                    database='default',
                    user='hive',
                    password='hive',
                    authMechanism="PLAIN") as conn:
        with conn.cursor() as cur:
        #get the table which stores the geo info of the meteorological station
            cur.execute("select site,value from awsrain")
        #cur.execute("select * from awsstationdesc")
            awsrain=cur.fetch()

    return awsrain

#generate raster points according giving range of area and min step
def genGridData(staLon,staLat,endLon,endLat,disEW,disSN,stepDis):

    rangeLon=endLon-staLon
    rangeLat=endLat-staLat
    #the corresponding longitude and lagitude of stepDis distance
    steDisCorLon=(rangeLon/disEW)*stepDis
    steDisCorLat=(rangeLat/disSN)*stepDis
    #the number of grid points in east-west direction and south-north direction
    xDim=int(math.ceil(rangeLon/steDisCorLon)+1)
    yDim=int(math.ceil(rangeLat/steDisCorLat)+1)

    #generate each grid's longitude and lagitude
    grid=[]
    for y in range(0,yDim):
        for x in range(0,xDim):
            count=y*xDim+x
            pointLon=staLon+x*steDisCorLon
            pointLat=staLat+y*steDisCorLat
            grid.append([count,pointLon,pointLat])

    return grid

#given grid and meteorological station information,computing the weight
# alpha is the power exponent of distance,used to determin the influence of
#distance to weight
def computeWeight(grid,stationInfo,alpha=1):
    #for each point in grid
    time_start=time.time()
    totalDisSet={}
    totalWeiSet={}
    for point in grid:
        weightSet=[]
        disSet={}
        for oneStation in stationInfo:
            #compute distance
            # disSquare=(point[1]-float(str(oneStation[1])))^2+(point[2]-float(str(oneStation[2])))^2
            disSquare=(point[1]-oneStation[1])**2+(point[2]-oneStation[2])**2
            disSet[(point[0],oneStation[0])]=disSquare
        totalDisSet[point[0]]=disSet
        #after computing a point to all meteorological stations' distance,compute weight
        #compute sum weight first
        sumWeight=0
        for iteDis in disSet:
            sumWeight+=1/(disSet[iteDis])**alpha
        #compute weight
        #pointWeiSet=[]
        for iteDis in disSet:
            weight=(1/(disSet[iteDis]**alpha))/sumWeight
            weightSet.append([iteDis[0],iteDis[1],weight])
        #sort the weight
        weightSet.sort(key=lambda x:x[2],reverse=True)
        totalWeiSet[point[0]]=weightSet
        '''
        #examing whether the sum of weight is 1
        sumTest=0
        for test in pointWeiSet:
            sumTest+=test[2]
         '''
        #weightSet.append(pointWeiSet)
    time_end=time.time()
    print 'running time computing weight:',time_end-time_start,'s'
    #save to file
    print 'saving total weight set to file...'
    try:
        f=open('totalWeightSet.txt','w')
    except IOError:
        print 'error occurs while opening weightSet.txt to write! '
    else:
        for weight in totalWeiSet:
            f.write(str(weight)+'\t'+str(totalWeiSet[weight])+'\n')
        f.close()
    try:
        f=open('distanceSet.txt','w')
    except IOError:
        print 'error occurs while opening distanceSet.txt to write!'
    else:
        for dis in totalDisSet:
            f.write(str(dis)+'\t'+str(totalDisSet[dis])+'\n')
        f.close()

    return totalWeiSet,totalDisSet

#load weightSet.txt to a dictionary.weightSet{key(point,sampleLocation):value(weight)}
def loadWeiToDic(filePath):
    try:
        f=open(filePath,'r')
    except IOError:
        print 'open weightSet.txt error!'
    else:
        #use weightDic to store the dictionary formed weight.
        weightDic={}
        for line in f:
            processedLine=line.strip().lstrip('[').rstrip(']').split(',')
            weightDic[(int(processedLine[0]),int(processedLine[1]))]=float(processedLine[2])

    return weightDic

#load disSet.txt to a dictionary disSet{key(point,sampleLocation):value(distance)}
def loadDisToDic(filePath):
    try:
        f=open(filePath,'r')
    except IOError:
        print 'open disSet.txt error!'
    else:
        #use disDic to store the dictionary formed weight.
        disDic={}
        for line in f:
            processedLine=line.strip().lstrip('[').rstrip(']').split(',')
            disDic[(int(processedLine[0]),int(processedLine[1]))]=float(processedLine[2])

    return disDic


#interpolation,using computed weight
#grid: grid points need to be interpolated
#weight:a dictionay which looks like {[0,a]:val,[0,b]:val,...,[1,a]:val,[1,b]:val...}
# each element represent the weight of a point to a sample location
#sampleData:sample data used to interpolation
#it has the form of [ID,value]
def IDWinterpolation(grid,totalWeightSet,distanceSet,sampleData,topK):
    #get station's ID set including in sampleData
    stationList=[]
    for station in sampleData:
        stationList.append(station[0])
    #for each grid point
    intRes=[]
    for point in grid:
        valuePoint=0
        pointWeiList=totalWeightSet[point[0]]
        disDic=distanceSet[point[0]]
        #get the biggest topK meteorological stations' ID
        topkStationInfo=[]
        count=0
        for weight in pointWeiList:
            if weight[1] in stationList:
                # topkStationID.append(weight[1])
                #find the ID's index in the stationList,then according the index find the corresponding value in sampleData
                index=stationList.index(weight[1])
                #we need to judge whether the sampleData[index][1] is None!
                if sampleData[index][1] is not None:
                    topkStationInfo.append([weight[1],sampleData[index][1]])
                    count+=1
                    if count==topK:
                        break
        if count<topK:
            print 'the value of topK is bigger than the number of stations in the sampleData while computing !'
            print 'please check the sampleData and topK value!'
            sys.exit()
        #according to the biggest topK weight stations' ID,conputing their corresponding weight again!
        sumDis=0
        for staInfo in topkStationInfo:
            sumDis+=disDic[(point[0],staInfo[0])]
        newWeight={}
        for staInfo in topkStationInfo:
            newWeight[(point[0],staInfo[0])]=disDic[(point[0],staInfo[0])]/sumDis

        #computing the interpolation according to the new weight
        value=0
        for staInfo in topkStationInfo:
            value+=staInfo[1]*newWeight[(point[0],staInfo[0])]
        intRes.append([point[0],point[1],point[2],value])

    #save the interpolation result to file
    # try:
    #     f=open('interpolationResult.txt','w')
    # except IOError:
    #     print 'error occurs while opening file to write interpolation result!'
    # else:
    #     for line in intRes:
    #         f.write(str(line))
    #     f.close()

    return intRes

#create table to store final concatenated interpolation result.
def createResultTable(host,port,database,user,password,authMechanism):
   with pyhs2.connect(host=host,
                port=port,
                database=database,
                user=user,
                password=password,
                authMechanism=authMechanism) as conn:
        with conn.cursor() as cur:
            cur.execute("drop table if exists IntRes")
            cur.execute("create table intRes("
                        "TIME timestamp"
                        "ID int,"
                        "LONGITUDE float,"
                        "LAGITUDE float,"
                        "ATMOSPRS float,"
                        "RAIN float,"
                        "RHUMD float,"
                        "TEMP float,"
                        "WNDDR float,"
                        "WNDSP float)"
                        "partitioned by (dt string)"
                        "row format delimited fields terminated by ','")


#load final interpolation result into hive
def loadResToHive(host,port,database,user,password,authMechanism,resultFilePath,partition):
    #connect to hive database
   with pyhs2.connect(host=host,
                port=port,
                database=database,
                user=user,
                password=password,
                authMechanism=authMechanism) as conn:
        with conn.cursor() as cur:
            str="load data local inpath "+resultFilePath+" into table IntRes partition(dt='"+partition+"')"
            # cur.execute("load data local inpath '/home/hadoop/PycharmProjects/IDWInterpolation/concatenateResult.txt' into table IntRes partition(dt='2016-03-01')")
            cur.execute(str)


if __name__=="__main__":

    time_start1=time.time()
#base info of hive database
    host='172.20.111.54'
    port=10000
    database='default'
    user='hive'
    password='hive'
    authMechanism='PLAIN'
    topK=3

    #establish a connection to hbase
    connection = happybase.Connection(host, autoconnect=False)

    # before first use:
    connection.open()
    intRes=connection.table('intRes')

    dtStart='2016-03-01'
    ini_time_start='2016-03-01 00:00:00'
    time_start=ini_time_start

    dtThis=dtStart
    count=0
    #current time reduce the value of hoursAgo is the biggest point of the computation can reach
    hoursAgo=1

    #compute initial end time point
    timeArray=time.strptime(ini_time_start,"%Y-%m-%d %H:%M:%S")
    timeStamp=int(time.mktime(timeArray))
    timeStamp+=3600
    timeArray=time.localtime(timeStamp)
    ini_time_end=time.strftime("%Y-%m-%d %H:%M:%S",timeArray)
    time_end=ini_time_end

    #compute initial time threshold
    now=int(time.time())
    nHourAgo=now-3600*hoursAgo
    timeArray=time.localtime(nHourAgo)
    ini_timeThr=time.strftime("%Y-%m-%d %H:%M:%S",timeArray)
    timeThr=ini_timeThr

    #create hive table to store interpolation result,execute once only!
    # createResultTable(host,port,database,user,password,authMechanism)
    #get station info from hive
    stationInfo=getStationInfo(host,port,database,user,password,authMechanism,dtThis)
    #create grid according to input area and minstep
    gridData=genGridData(122.2,22.2,156.6,34.2,50,30,10)
    #compute each grid point's weight to all stations
    weightDic,disSet=computeWeight(gridData,stationInfo)

    while time_end<timeThr:

        qua_time_start='"'+time_start+'"'
        qua_time_end='"'+time_end+'"'

        qua_dtThis='"'+dtThis+'"'

        sqlAtmosprs="select site,value from awsatmosprs where dt="+qua_dtThis+" and time>"+qua_time_start+" and time<"+qua_time_end
        sqlRain="select site,value from awsrain where dt="+qua_dtThis+" and time>"+qua_time_start+" and time<"+qua_time_end
        sqlRhumd="select site,value from awsrhumd where dt="+qua_dtThis+" and time>"+qua_time_start+" and time<"+qua_time_end
        sqlTemp="select site,value from awstemp where dt="+qua_dtThis+" and time>"+qua_time_start+" and time<"+qua_time_end
        sqlWnddr="select site,value from awswnddr where dt="+qua_dtThis+" and time>"+qua_time_start+" and time<"+qua_time_end
        sqlWndsp="select site,value from awswndsp where dt="+qua_dtThis+" and time>"+qua_time_start+" and time<"+qua_time_end

        # weightDic=loadWeiToDic('weightSet.txt')
        time_start2=time.time()
        #connect to hive database
        with pyhs2.connect(host=host,
                    port=port,
                    database=database,
                    user=user,
                    password=password,
                    authMechanism=authMechanism) as conn:
            with conn.cursor() as cur:
            #get the sample data for interpolation
                cur.execute(sqlAtmosprs)
                atmosprsData=cur.fetch()
                # del atmosprsData[0]
                cur.execute(sqlRain)
                rhumdData=cur.fetch()
                # del rhumdData[0]
                cur.execute(sqlRhumd)
                rainData=cur.fetch()
                # del rainData[0]
                cur.execute(sqlTemp)
                tempData=cur.fetch()
                # del tempData[0]
                cur.execute(sqlWnddr)
                wnddrData=cur.fetch()
                # del wnddrData[0]
                cur.execute(sqlWndsp)
                wndspData=cur.fetch()
                # del wndspData[0]
        time_end2=time.time()
        print 'time used for getting data from hive: ',time_end2-time_start2,'s'

        time_start3=time.time()
        if atmosprsData:
            atmosprsIntRes=IDWinterpolation(gridData,weightDic,disSet,atmosprsData,topK)
        else:
            atmosprsIntRes=[]
        if rhumdData:
            rhumdIntRes=IDWinterpolation(gridData,weightDic,disSet,rhumdData,topK)
        else:
            rhumdIntRes=[]
        if rainData:
            rainIntRes=IDWinterpolation(gridData,weightDic,disSet,rainData,topK)
        else:
            rainIntRes=[]
        if tempData:
            tempIntRes=IDWinterpolation(gridData,weightDic,disSet,tempData,topK)
        else:
            tempIntRes=[]
        if wnddrData:
            wnddrIntRes=IDWinterpolation(gridData,weightDic,disSet,wnddrData,topK)
        else:
            wnddrIntRes=[]
        if wndspData:
            wndspIntRes=IDWinterpolation(gridData,weightDic,disSet,wndspData,topK)
        else:
            wndspIntRes=[]
        time_end3=time.time()
        print 'time used for computing all the interpolation result:',time_end3-time_start3,'s'

        #concatenate the interpolation result,converting to the intended form
        conRes=[]
        #use this time's time_end to be the time of these interpolation result
        for i in range(0,len(gridData)):
            if atmosprsIntRes:
                atmosprsValue=atmosprsIntRes[i][3]
            else:
                atmosprsValue=None
            if rhumdIntRes:
                rhumdValue=rhumdIntRes[i][3]
            else:
                rhumdValue=None
            if rainIntRes:
                rainValue=rainIntRes[i][3]
            else:
                rainValue=None
            if tempIntRes:
                tempValue=tempIntRes[i][3]
            else:
                tempValue=None
            if wnddrIntRes:
                wnddrValue=wnddrIntRes[i][3]
            else:
                wnddrValue=None
            if wndspIntRes:
                wndspValue=wndspIntRes[i][3]
            else:
                wndspValue=None

#write interpolation result to hbase
            row_key=time_end+'-'+str(gridData[i][1])+'-'+str(gridData[i][2])
            str_row_key="'"+row_key+"'"
            strTime_end="'"+time_end+"'"
            strId="'"+str(gridData[i][0])+"'"
            strLongitude="'"+str(gridData[i][1])+"'"
            strLagitude="'"+str(gridData[i][2])+"'"
            strAtmosprs="'"+str(atmosprsValue)+"'"
            strRhumd="'"+str(rhumdValue)+"'"
            strRain="'"+str(rainValue)+"'"
            strTemp="'"+str(tempValue)+"'"
            strWnddr="'"+str(wnddrValue)+"'"
            strWndsp="'"+str(wndspValue)+"'"

            intRes.put(str_row_key,{'time:col1':strTime_end,\
                                    'id:col1':strId,\
                                    'longitude:col1':strLongitude,\
                                    'lagitude:col1':strLagitude,\
                                    'attValue:col1':strAtmosprs,\
                                    'attValue:col2':strRhumd,\
                                    'attValue:col3':strRain,\
                                    'attValue:col4':strTemp,\
                                    'attValue:col5':strWnddr,\
                                    'attValue:col6':strWndsp})


            conRes.append([time_end,gridData[i][0],gridData[i][1],gridData[i][2],atmosprsValue,rhumdValue,rainValue,tempValue,wnddrValue,wndspValue])

        time_start4=time.time()
        #write conRes into file
        fileName=time_end+"_concatenateResult.txt"
        f=open(fileName,'w')
        for line in conRes:
            lineStr=str(line).strip().lstrip('[').rstrip(']')
            f.write(lineStr+'\n')
        f.close()
        time_end4=time.time()
        print 'time used for writing result into file: ',time_end4-time_start4,'s'
        time_end1=time.time()
        print 'total time used: ',time_end1-time_start1,'s'

        # #load file to hive
        # loadResToHive(host,port,database,user,password,authMechanism,fileName,dtThis)

        count+=1
        if count==24:
            #set count to 0
            count=0
            #dt need to be changed
            timeArray=time.strptime(dtThis,"%Y-%m-%d")
            timeStamp=int(time.mktime(timeArray))
            newTimeStamp=timeStamp+86400
            newTimeArray=time.localtime(newTimeStamp)
            newDt=time.strftime("%Y-%m-%d",newTimeArray)

            dtThis=newDt

            #update the station info and recompute the weight
            stationInfo=getStationInfo(host,port,database,user,password,authMechanism,dtThis)
            weightDic,disSet=computeWeight(gridData,stationInfo)


        #after reset count,update the time_end and time_end
        time_start=time_end

        timeArray=time.strptime(time_end,"%Y-%m-%d %H:%M:%S")
        timeStamp=int(time.mktime(timeArray))
        timeStamp+=3600
        timeArray=time.localtime(timeStamp)
        upd_time_end=time.strftime("%Y-%m-%d %H:%M:%S",timeArray)
        time_end=upd_time_end

        #update time threshold
        #get the system date first
        now=int(time.time())
        nHourAgo=now-3600*hoursAgo
        timeArray1=time.localtime(nHourAgo)
        timeThr=time.strftime("%Y-%m-%d %H:%M:%S",timeArray1)

        #while time_end>timeThreshold,waiting for the time_end<timeThreshold
        while time_end>timeThr:
            #sleep a period of time
            time.sleep(600)
            #update time threshold
            now=int(time.time())
            nHourAgo=now-3600*hoursAgo
            timeArray=time.localtime(nHourAgo)
            timeThr=time.strftime("%Y-%m-%d %H:%M:%S",timeArray)
