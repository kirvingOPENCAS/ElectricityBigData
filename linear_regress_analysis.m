clc;
clear;

%加载训练数据，取五份作为训练，一份作为测试
data1=load('batch_data1.mat');
data2=load('batch_data2.mat');
data3=load('batch_data3.mat');
data4=load('batch_data4.mat');
data5=load('batch_data5.mat');
data6=load('batch_data6.mat');

B=zeros(0,0);
for i=1:6
    %每次选一份作为测试集，其余五份作为训练集
    if(i==1)
        train_data1=data2.batch2;
        train_data2=data3.batch3;
        train_data3=data4.batch4;
        train_data4=data5.batch5;
        train_data5=data6.batch6;
        test_data=data1.batch1;
            elseif(i==2)
        train_data1=data1.batch1;
        train_data2=data3.batch3;
        train_data3=data4.batch4;
        train_data4=data5.batch5;
        train_data5=data6.batch6;
        test_data=data2.batch2;
            elseif(i==3)
        train_data1=data1.batch1;
        train_data2=data2.batch2;
        train_data3=data4.batch4;
        train_data4=data5.batch5;
        train_data5=data6.batch6;
        test_data=data3.batch3;
            elseif(i==4)
        train_data1=data1.batch1;
        train_data2=data2.batch2;
        train_data3=data3.batch3;
        train_data4=data5.batch5;
        train_data5=data6.batch6;
        test_data=data4.batch4;
            elseif(i==5)
        train_data1=data1.batch1;
        train_data2=data2.batch2;
        train_data3=data3.batch3;
        train_data4=data4.batch4;
        train_data5=data6.batch6;
        test_data=data5.batch5;
            elseif(i==6)
        train_data1=data1.batch1;
        train_data2=data2.batch2;
        train_data3=data3.batch3;
        train_data4=data4.batch4;
        train_data5=data6.batch6;
        test_data=data6.batch6;
        
    end

%总的训练数据是五份叠加
train_data=[train_data1;train_data2;train_data3;train_data4;train_data5];

num_train=size(train_data,1);
Y=train_data(:,1);
temp=train_data(:,2:end);
X=[ones(num_train,1),temp];
[b,bint,r,rint,stats]=regress(Y,X);
B(i,:)=b;

%检验准确性
clear temp;
temp=test_data(:,2:end);
num_test=size(temp,1);
X1=[ones(num_test,1),temp];
predict_result=X1*b;

true_result=test_data(:,1);

%直观数值对比
% contrast=strcat('contrast_',num2str(i));
contrast{i}=[true_result,predict_result];

%统计预测误差
% error=strcat('error_',num2str(i));
error(i)=norm((true_result-predict_result));

if(i==1)
    min_err=error(i);
    min_indx=i;
end

if(error(i)<min_err)
    min_err=error(i);
    min_indx=i;
end

end

%将预测误差最小的模型作为最终模型
% min_err=min(error);
data_plot=contrast{min_indx}(1:1000,:);
x=(1:1000);
real_vals=data_plot(:,1);
predict_vals=data_plot(:,2);

plot(x,real_vals,'-b.',x,predict_vals,'-r.');
title('击穿电压预测值与真实值比较');
xlabel('时间');
ylabel('击穿电压');
legend('真实击穿电压值','预测击穿电压值');


