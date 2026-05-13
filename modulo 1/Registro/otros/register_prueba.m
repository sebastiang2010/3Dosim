
tipo=0; 

currentdirectory=pwd;
newpath=[currentdirectory,'\funciones']; 
path(path,newpath)
clear newpath currentdirectory

disp(' ' )
disp(' Ingrese la Imagen PET');
[PET,info_PET,Rescale_PET,medVol_PET]=f_cargo_imagen(tipo);% 1 es tiff
PET=squeeze(PET);
PET=double(PET);

disp(' ' )
disp(' Ingrese la Imagen CT');
[CT,info_CT,~,medVol_CT]=f_cargo_imagen(tipo);% 1 es tiff
CT=squeeze(CT);
CT=uint16(CT);