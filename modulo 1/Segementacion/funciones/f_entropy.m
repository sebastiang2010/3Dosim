function [promedio,desv,entropia]=f_entropy(I_hueso,ind)


promedio= mean2(I_hueso(ind));
desv=std2(I_hueso(ind));
entropia=entropy(I_hueso(ind));





