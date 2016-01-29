clc;
clear;
num=xlsread('G:\\HHX\电力大数据\华南理工数据\番禹巡维中心2011数据\2011.xls');
[row,col]=size(num);

for i=5:col
    data{i-4}=num(:,i);
end

for cicycle1=1:(col-5)
    for cicycle2=(cicycle1+1):(col-4)
        c=corrcoef(data{1,cicycle1},data{1,cicycle2});
        corr_factor(cicycle1,cicycle2)=c(1,2);
    end
end

for i=1:(col-4)
    corr_factor(i,i)=1;
end

save('correlation_coefficient_month12.mat','corr_factor');