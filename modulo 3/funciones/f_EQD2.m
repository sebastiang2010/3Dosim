function [EQD2] =f_EQD2(D,organo,p_radiobiologicos,index)

% resolver paa pretumor 
ab=0; 

if organo==index.liver;ab=p_radiobiologicos.liver.alfa_beta;end 
if organo==index.tumor;ab=p_radiobiologicos.tumor.alfa_beta;end

EQD2=D*ab/(2+ab); 

end 