function nii=f_cargar_nii 

currentdirectory=pwd;

tipoarchivo='*.nii';'*.*';
%tipoarchivo='*.*';
%%%%
%como deberia ser con version 7.0
%[archivos,directorio]=uigetfile('*.dcm','Select the Dicom-files', 'MultiSelect', 'on');
[archivos,directorio]=uigetfile(tipoarchivo,'Select the NII Files'); %eligo el archivo y el directorio-
if isequal(archivos,0)||isequal(directorio,0);
      nii=[];
      %ScoutView=[];
   return;
end
cd(directorio);
%file=dir(fullfile(directorio,tipoarchivo)); %carga la etrucuta de archivos
        
     
file=[directorio,archivos];             
nii=load_nii(file); %estructura 

cd(currentdirectory);

