
clear 
clc 
close all 

load('C:\MAT\3Dosim\paciente.mat')

radiobiologia=paciente.p_radiobiologicos;
D=paciente.Dosis.voxel; 
BED=paciente.BED;
index=paciente.index; 
I=paciente.Phantom; 

N=1; %esto lo tengo que calcular pata cada voxel 

IND=I==index.tumor; 
IND=double(IND); 
BED=BED.*IND; 

N_D=N.*exp(BED); 

% pensar en ordenarlas y multiplicarlas

%bed=0:0.01:max(BED(:)); 
% n=1; 
% for i=1:512  
%   for j=1:512 
%     for k=1:171
%         tcp_v=N_D(i,j,k); 
%         bed=BED(i,j,k);
%        A(n,:)=[tcp_v,bed];
%        n=n+1; 
%     end 
%   end 
% end 
% PCT=1