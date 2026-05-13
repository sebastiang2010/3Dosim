%%
clc 
close
clear all 
%%
currentdirectory=pwd;
newpath=[currentdirectory,'\funciones']; 
path(path,newpath)

liver=f_cargar_nii;