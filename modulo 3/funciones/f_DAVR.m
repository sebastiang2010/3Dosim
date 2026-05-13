function [Dosis_liver] = f_DAVYR(PET,I,vCT)
%UNTITLED2 Summary of this function goes here
%   Detailed explanation goes here

%% calculo DAVYR
clc 

S=49.70; %(Gy-kg/GBq)
d_liver=1.03;
d_lung=0.3;


%%
IND=I1==index.tumor; 
T=PET1(IND); 
v_t=sum(IND(:))*prod(tvoxel); %cm^3


IND=I1==index.liver; 
N=PET1(IND);
v_liver=sum(IND(:))*prod(tvoxel); %cm^3

m_tumor=v_t*d_liver/1000; %kg 
m_liver=v_liver*d_liver/1000; %kg 
m_lung=0.01236; %kg


%%
At=sum(T(:));
Aliver=sum(N(:)); 
T_N=At/m_liver/(m_tumor/Aliver);

por_tumor=v_t/(v_liver+v_t);

shunt=0.12; %m 

%% BSA 
W=77; %m 
H=1.72; %

BSA=0.20247*H^0.725*W^0.425; 
A_BSA=BSA-0.2+(por_tumor);

A_lung=A_BSA*shunt;
A_liver=A_BSA*(1-shunt); 

Dosis_liver=A_liver*m_liver*S; %Gy 
Dosis_lung=A_lung*m_lung*S; %Gy 

%% Partitional 








%end

