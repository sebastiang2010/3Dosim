clc 
clear all 

k=2;
c=k/(exp(k)-exp(-k));

p=0.25; 

cos_o=log(p/c);
cos_o=cos_o/k;

o=acos(cos_o);


o=45;
%o=o/2;
rad=o*pi/180;
%deg=deg/2;


u=cos(rad);

p=c*exp(k*u);