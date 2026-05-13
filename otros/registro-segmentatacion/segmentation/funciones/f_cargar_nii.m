function  nii=f_cargar_nii

tipoarchivo='*.nii';'*.*';
file=[]; 
%tipoarchivo='*.*';
%%%%
%como deberia ser con version 7.0
%[archivos,directorio]=uigetfile('*.dcm','Select the Dicom-files', 'MultiSelect', 'on');
[archivos,directorio]=uigetfile(tipoarchivo,'Select the NII Files'); %eligo el archivo y el directorio-
if isequal(archivos,0)||isequal(directorio,0);
                   I=[];
            %ScoutView=[];
   return;
end
cd(directorio);
%file=dir(fullfile(directorio,tipoarchivo)); %carga la etrucuta de archivos
        
   
file=[directorio,archivos];            
nii=load_nii(file); %estructura 

%% agregar el archivo original 

%I=tumor.img;

%figure 
%for i=1:size(I,3)
%    imshow(I(:,:,i),[])
%end 
%pause(0.2)






