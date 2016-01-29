clc;
clear;
total_data=zeros(0,0);

%�ȶ�ȡʮ���µ�����
num=xlsread('G:\HHX\����������\����������\����Ѳά����2011����\2011.xls',1);
total_data=num(:,5:18);
clear num;

%����һ�·ݺͶ��·ݵ�����
for i=2:3
num=xlsread('G:\HHX\����������\����������\����Ѳά����2011����\2011.xls',i);
temp=num(:,4:17);
total_data=[total_data;temp];
clear num;
clear temp;
end

for i=4:12
num=xlsread('G:\HHX\����������\����������\����Ѳά����2011����\2011.xls',i);
temp=num(:,5:18);
total_data=[total_data;temp];
clear num;
clear temp;
end

save('2011_total_data.mat','total_data');

%������2�У����ǿ�ȣ��ɻ�����ѹ�ó�����10�У����У��͵�14�У�Ϊ����ֵ20��������������
temp1=total_data(:,1);
temp2=total_data(:,3:9);
temp3=total_data(:,11:13);
rm_useless_col_data=[temp1 temp2 temp3];
save('rm_2and10and11_2011.mat','rm_useless_col_data');
clear temp1 temp2 temp3;

%������ѹ��һ���Ϊ��ѹ�䶯��С��ͨ�����Իع��õ�ϵ���ܴ󣬽ӽ�0.5�����Բ��С�ȥ����ʵ��
temp1=rm_useless_col_data(:,1:4);
temp2=rm_useless_col_data(:,6:end);
rm_uselessandairpression_data=[temp1 temp2];
save('rm_uselessandairpression_data.mat','rm_uselessandairpression_data');
clear temp1 temp2;

%��ȫ�����ݷֳ����ݣ���������֤ʹ��
num_data=size(rm_useless_col_data,1);
yushu=mod(num_data,6);
batch_size=(num_data-yushu)/6;
batch_seq=0;
batch1=zeros(0,0);
batch2=zeros(0,0);
batch3=zeros(0,0);
batch4=zeros(0,0);
batch5=zeros(0,0);
batch6=zeros(0,0);

for i=1:(num_data-yushu)
    
    if(i==(batch_seq*6+1))
        temp=rm_useless_col_data(i,:);
        batch1=[batch1;temp];
        clear temp;
        
    elseif(i==(batch_seq*6+2))
        temp=rm_useless_col_data(i,:);
        batch2=[batch2;temp];
        clear temp;
       
    elseif(i==(batch_seq*6+3))
        temp=rm_useless_col_data(i,:);
        batch3=[batch3;temp];
        clear temp;

    elseif(i==(batch_seq*6+4))
        temp=rm_useless_col_data(i,:);
        batch4=[batch4;temp];
        clear temp;

        elseif(i==(batch_seq*6+5))
        temp=rm_useless_col_data(i,:);
        batch5=[batch5;temp];
        clear temp;

        elseif(i==(batch_seq*6+6))
        temp=rm_useless_col_data(i,:);
        batch6=[batch6;temp];
        batch_seq=batch_seq+1;
        clear temp;
        
    end
end

save('batch_data1','batch1');
save('batch_data2','batch2');
save('batch_data3','batch3');
save('batch_data4','batch4');
save('batch_data5','batch5');
save('batch_data6','batch6');

%����Է���
[row,col]=size(total_data);
for cicycle1=1:col
    for cicycle2=cicycle1:col
        c=corrcoef(total_data(:,cicycle1),total_data(:,cicycle2));
        corr_factor(cicycle1,cicycle2)=c(1,2);
    end
end

save('correlation_coefficient_2011.mat','corr_factor');