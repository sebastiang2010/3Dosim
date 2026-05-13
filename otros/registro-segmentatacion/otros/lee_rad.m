%% lee los gamas del fichero RAD de IRCP 101
% ID 1 X 
% ID 2 gamma
close all 
clear all 
clc 

cutoff=1e-1; %MeV

%% poner para elegir el archivo 
[fid,msm]=fopen('D:\MAT\Emergencias\Ir-192.txt','rt');
%%
A=[];
tic 
a=0;
n=1;
while ~feof(fid)
   
     tline = fgetl(fid);
     matches = findstr(tline,'Number of photon radiations:');
     
     if matches>0;
              n1=str2num(tline(30:end));
     end
     
     matches1= findstr(tline,'START RADIATION RECORDS'); 
     
    if matches1>0;a=2;end
    
    if a==2;
       A(n,:)=fscanf(fid,'%e'); % me funciono poner el tamaño 
       if n==n1;break;end
       n=n+1;
    end
end   
time=toc;
fclose(fid);


ind=find(A(:,3)>cutoff);

emisividad=A(ind,2); %por desintegracion nuclear 
E=A(ind,3); %MeV 
