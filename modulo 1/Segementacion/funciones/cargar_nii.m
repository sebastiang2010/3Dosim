% cargar_nii 
clc 

tipoarchivo='*.nii';'*.*';
%tipoarchivo='*.*';
%%%%
%como deberia ser con version 7.0
%[archivos,directorio]=uigetfile('*.dcm','Select the Dicom-files', 'MultiSelect', 'on');
[archivos,directorio]=uigetfile(tipoarchivo,'Select the NII Files'); %eligo el archivo y el directorio-
if isequal(archivos,0)||isequal(directorio,0)
                   I=[];
            %ScoutView=[];
   return;
end
cd(directorio);
file=dir(fullfile(directorio,tipoarchivo)); %carga la etrucuta de archivos
        
      %nii = load_nii(filename, img_idx, dim5_idx, dim6_idx, dim7_idx, ...
		%	old_RGB, tolerance, preferredForm)  
     
            
tumor=load_nii(file.name); %estructura 

%% agregar el archivo original 

I=tumor.img;

figure 
for i=1:size(I,3)
    imshow(I(:,:,i),[])
    pause(0.1)
end 






