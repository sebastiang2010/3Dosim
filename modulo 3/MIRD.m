%% MIRD 

% pag 103 Libro Y90
Volumen_normal=302; %ml 
Volumen_tumor=122;% ml 
m_tumor=0.128; %kg
m_normal=0.317; %kg
T_N=2.8; 
SF=0.05; % Shunt pulmonar 
k=49.98; %J-s conversor de unidades 
D_tumor=150; %dosis target 

FU_normal=(1-SF)*(Volumen_normal/(T_N*Volumen_tumor+Volumen_normal));
FU_tumor=(1-SF)*(T_N*Volumen_tumor/(T_N*Volumen_tumor+Volumen_normal));

Actividad_GBq=D_tumor*m_tumor/(k*FU_tumor);

D_normal_GBq=Actividad_GBq*k*FU_normal/m_normal; 

