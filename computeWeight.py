#get the geo location of the meteorological stations
#construct the raster according to the range of longitude and lagitude
#compute the distance of each point to each meteorological station then
#compute the inverse distance weight.

import pyhs2
import math
import time
import sys

#connect hive database
def getStationInfo(host,port,database,user,password,authMechanism):
    with pyhs2.connect(host=host,
                    port=port,
                    database=database,
                    user=user,
                    password=password,
                    authMechanism=authMechanism) as conn:
        with conn.cursor() as cur:
        #get the table which stores the geo info of the meteorological station
            cur.execute("select sid,lon,lat from awsstationdesc")
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
    #create hive table to store interpolation result,execute once only!
    createResultTable(host,port,database,user,password,authMechanism)
    #get station info from hive
    stationInfo=getStationInfo(host,port,database,user,password,authMechanism)
    #create grid according to input area and minstep
    gridData=genGridData(122.2,22.2,156.6,34.2,500,300,1)
    #compute each grid point's weight to all stations
    weightDic,disSet=computeWeight(gridData,stationInfo)

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
            cur.execute("select site,value from awsatmosprs where dt='2016-03-01'")
            atmosprsData=cur.fetch()
            del atmosprsData[0]
            cur.execute("select site,value from awsrhumd where dt='2016-03-01'")
            rhumdData=cur.fetch()
            del rhumdData[0]
            cur.execute("select site,value from awsrain where dt='2016-03-01'")
            rainData=cur.fetch()
            del rainData[0]
            cur.execute("select site,value from awstemp where dt='2016-03-01'")
            tempData=cur.fetch()
            del tempData[0]
            cur.execute("select site,value from awswnddr where dt='2016-03-01'")
            wnddrData=cur.fetch()
            del wnddrData[0]
            cur.execute("select site,value from awswndsp where dt='2016-03-01'")
            wndspData=cur.fetch()
            del wndspData[0]
    time_end2=time.time()
    print 'time used for getting data from hive: ',time_end2-time_start2,'s'

    time_start3=time.time()
    atmosprsIntRes=IDWinterpolation(gridData,weightDic,disSet,atmosprsData,topK)
    rhumdIntRes=IDWinterpolation(gridData,weightDic,disSet,rhumdData,topK)
    rainIntRes=IDWinterpolation(gridData,weightDic,disSet,rainData,topK)
    tempIntRes=IDWinterpolation(gridData,weightDic,disSet,tempData,topK)
    wnddrIntRes=IDWinterpolation(gridData,weightDic,disSet,wnddrData,topK)
    wndspIntRes=IDWinterpolation(gridData,weightDic,disSet,wndspData,topK)
    time_end3=time.time()
    print 'time used for computing all the interpolation result:',time_end3-time_start3,'s'

    #concatenate the interpolation result,converting to the intended form
    conRes=[]
    for i in range(0,len(gridData)):
         conRes.append([atmosprsIntRes[i][0],atmosprsIntRes[i][1],atmosprsIntRes[i][2],atmosprsIntRes[i][3],rhumdIntRes[i][3],rainIntRes[i][3],tempIntRes[i][3],wnddrIntRes[i][3],wndspIntRes[i][3]])

    time_start4=time.time()
    #write conRes into file
    f=open('concatenateResult.txt','w')
    for line in conRes:
        lineStr=str(line).strip().lstrip('[').rstrip(']')
        f.write(lineStr+'\n')
    f.close()
    time_end4=time.time()
    print 'time used for writing result into file: ',time_end4-time_start4,'s'
    time_end1=time.time()
    print 'total time used: ',time_end1-time_start1,'s'
    # resultFilePath="'/home/hadoop/concatenateResult.txt'"
    # partition='2016-03-01'
    # #load file to hive
    # loadResToHive(host,port,database,user,password,authMechanism,resultFilePath,partition)
