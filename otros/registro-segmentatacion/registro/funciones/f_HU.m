function I=f_HU(I,info_CT)

m=info_CT.RescaleSlope;
b=info_CT.RescaleIntercept; 

I=m.*I+b; 
