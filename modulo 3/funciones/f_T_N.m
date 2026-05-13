function [T_N,volumen_liver,volumen_tumor] = f_T_N(PET,Phantom,vCT) 

index_tumor=100; 
index_liver=90; 

volumen_liver=f_volumen(index_liver,vCT,Phantom);
volumen_tumor=f_volumen(index_tumor,vCT,Phantom);


ind=Phantom==index_tumor; 
A_tumor=sum(PET(ind));

ind=Phantom==index_liver; 
A_liver=sum(PET(ind));

T_N=(A_tumor/volumen_tumor)/(A_liver/volumen_liver);

end

