# -*- coding: utf-8 -*-
import xlrd
import xlwt
import csv
import time
import math
import sys
type = sys.getfilesystemencoding()
print type
#reload(sys)
#sys.setdefaultencoding('utf-8')

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
            weightSet.append([iteDis[0],int(iteDis[1]),weight])
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
        stationList.append(int(station[0]))
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
                    topkStationInfo.append([weight[1],float(sampleData[index][1])])
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

workbook=xlrd.open_workbook(r'/home/hadoop/GDStationInfo.xlsx')

csvfile=file('/home/hadoop/bdc_wm_mdata.csv')
reader=csv.reader(csvfile)
i=0
iniData={}

for line in reader:
    i+=1
    if i==1:
        continue
    line[1]=line[1].strip()
    if len(line[1])<8:
        continue
    if len(line[1])<16:
        timeArray=time.strptime(line[1],"%Y/%m/%d")
    else:
    # print line[1]
    # print len(line[1])
        timeArray=time.strptime(line[1],"%Y/%m/%d %H:%M:%S")
    timeStamp=int(time.mktime(timeArray))
    timeArray=time.localtime(timeStamp)
    line[1]=time.strftime("%Y/%m/%d %H:%M:%S",timeArray)
    iniData.setdefault(line[1],[]).append(line[2:9])




print 'total row: ',i

print workbook.sheet_names()
sheet=workbook.sheet_by_index(0)
print sheet.name,sheet.nrows,sheet.ncols

stationInfo=[]
for i in range(1,sheet.nrows):
    # print sheet.row_values(i)
    stationInfo.append([sheet.row_values(i)[1],sheet.row_values(i)[3],sheet.row_values(i)[4]])

ini_day='2015/08/04'
ini_time_start='2015/08/04 19:00:00'
timeArray=time.strptime(ini_time_start,"%Y/%m/%d %H:%M:%S")
curTimeStamp=int(time.mktime(timeArray))
#current time reduce the value of hoursAgo is the biggest point of the computation can reach
hoursAgo=1

time_end='2016/07/05 15:00:00'
timeArray=time.strptime(time_end,"%Y/%m/%d %H:%M:%S")
endTimeStamp=int(time.mktime(timeArray))
# timeArray=time.localtime(timeStamp)
# time_end=time.strftime("%Y-%m-%d %H:%M:%S",timeArray)

#complement the deficient iniData
curTimeStamp0=curTimeStamp
endTimeStamp0=endTimeStamp
while(curTimeStamp0<endTimeStamp0):

    timeArray=time.localtime(curTimeStamp0)
    cur_time=time.strftime("%Y/%m/%d %H:%M:%S",timeArray)

    lastTimeStamp=curTimeStamp0-3600
    timeArray=time.localtime(lastTimeStamp)
    last_time=time.strftime("%Y/%m/%d %H:%M:%S",timeArray)

    if cur_time not in iniData:
        iniData[cur_time]=iniData[last_time]

    curTimeStamp0=curTimeStamp0+3600


gridData=genGridData(112.92847,22.49733,114.08203,23.93480,116.80,158.181,0.5)
#compute each grid point's weight to all stations
weightDic,disSet=computeWeight(gridData,stationInfo)
topK=3
lastTimePointData=[]

while curTimeStamp<endTimeStamp:

    totalResult=[]
    timeArray=time.localtime(curTimeStamp)
    day=time.strftime("%Y/%m/%d",timeArray)
    dayName=time.strftime("%Y-%m-%d",timeArray)

    timeArray=time.strptime(day,"%Y/%m/%d")
    dayEndTimeStamp=int(time.mktime(timeArray))
    dayEndTimeStamp+=3600*24

    while curTimeStamp<dayEndTimeStamp and curTimeStamp<=endTimeStamp:
        timeArray=time.localtime(curTimeStamp)
        cur_time=time.strftime("%Y/%m/%d %H:%M:%S",timeArray)
        if cur_time=='2015/08/05 08:00:00':
            pass
        atmos=[]
        temp=[]
        rhumd=[]
        rain=[]
        wnddr=[]
        wndsp=[]
        if cur_time in iniData:
            #get the corresponding time point data
            for ele in iniData[cur_time]:
                atmos.append([ele[0],ele[1]])
                temp.append([ele[0],ele[2]])
                rhumd.append([ele[0],ele[3]])
                rain.append([ele[0],ele[4]])
                wnddr.append([ele[0],ele[5]])
                wndsp.append([ele[0],ele[6]])

        else:
            print 'this time point is not in iniData: ',cur_time
            curTimeStamp+=3600
            continue
            #if the time point doesn't appear in the iniData,then copy the last time point's data to the time point
            #write lastTimePoint's data into file,the only difference with last time point is the date
            #on the initial time point,if there is no initial data,then jump to next time point
            # if lastTimePointData:
            #     tempL=[]
            #     tempL=lastTimePointData
            #     for ele in tempL:
            #         ele[0]=cur_time
            #     #totalResult.extend(tempL)
            #     totalResult=totalResult+tempL
            #     curTimeStamp+=3600
            # else:
            #     curTimeStamp+=3600
            #
            # continue


        #interpolation
        atmosprsIntRes=IDWinterpolation(gridData,weightDic,disSet,atmos,topK)
        tempIntRes=IDWinterpolation(gridData,weightDic,disSet,temp,topK)
        rhumdIntRes=IDWinterpolation(gridData,weightDic,disSet,rhumd,topK)
        rainIntRes=IDWinterpolation(gridData,weightDic,disSet,rain,topK)
        wnddrIntRes=IDWinterpolation(gridData,weightDic,disSet,wnddr,topK)
        wndspIntRes=IDWinterpolation(gridData,weightDic,disSet,wndsp,topK)

        #concantenate interpolation result
        numGrid=len(gridData)
        result=[]
        for ele in range(numGrid):
            #if the rain value is less than 0.1 and bigger than 0,then set it to 0.1
            if (rainIntRes[ele][3]<0.1 and rainIntRes[ele][3]>0):
                rainIntRes[ele][3]=0.1
            result.append([cur_time,gridData[ele][1],gridData[ele][2],atmosprsIntRes[ele][3],tempIntRes[ele][3],rhumdIntRes[ele][3],rainIntRes[ele][3],wnddrIntRes[ele][3],wndspIntRes[ele][3]])

        # lastTimePointData=result
        totalResult=totalResult+result
        curTimeStamp+=3600

    #write day result into file
    # f=xlwt.Workbook()
    # sheet1=f.add_sheet(u'sheet1',cell_overwrite_ok=True)
    # row0=[u'Time',u'Longitude',u'Lagitude',u'Atmosprs',u'Temp',u'Rhumd',u'Rain',u'Wnddr',u'Wndsp']
    # for i in range(0,len(row0)):
    #     sheet1.write(0,i,row0[i])
    #
    # print 'len(totalResult: ',len(totalResult)
    # for row in range(1,len(totalResult)+1):
    #     for i in range(0,9):
    #         if i==0:
    #             timePoint=totalResult[row-1][i]
    #             timePoint=timePoint.strip().lstrip("'").rstrip("'")
    #             sheet1.write(row,i,timePoint)
    #         else:
    #             sheet1.write(row,i,totalResult[row-1][i])
    # filename='./data/'+dayName+'.xlsx'
    # f.save(filename)

    filename='./data/'+dayName+'.txt'
    f=open(filename,'w')
    f.write('Time'+' '+'Longitude'+' '+'Lagitude'+' '+'Atmosprs'+' '+'Temp'+' '+'Rhumd'+' '+'Rain'+' '+'Wnddr'+' '+'Wndsp'+'\n')
    for ele in totalResult:
        for subEle in ele:
            subEle=str(subEle).strip().lstrip("'").rstrip("'")
            f.write(subEle+' ')
        f.write('\n')
    f.close()

















