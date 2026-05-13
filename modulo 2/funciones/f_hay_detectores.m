function [det,detectores]=f_hay_detectores

disp('  ')
resp=input('Ingrese  0 si hay detectore; >0 si no hay detectores:   '); 

if resp==0;det=1;else det=-1;end

clc

detectores=[]; 
if resp==0;
   detectores=f_detectores;
end
   
    