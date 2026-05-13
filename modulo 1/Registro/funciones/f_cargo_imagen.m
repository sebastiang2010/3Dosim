function   [I,image_info,Rescale,spatial]=f_cargo_imagen(tiff)

Rescale=[]; 

%%
% leo la informacion del volumen 
% es mas facil usar esa informacion para el volumen 

%% tiff dicom = 1 es tiff
%% tiff dicom = 0 es dicom
currentdirectory=pwd;
switch tiff
%% dicom    
    case 0
        %tipoarchivo='*.dcm';
        tipoarchivo='*.*'; 
        %%%%
        %como deberia ser con version 7.0
        %[archivos,directorio]=uigetfile('*.dcm','Select the Dicom-files', 'MultiSelect', 'on');
        [archivos,directorio]=uigetfile(tipoarchivo,'Select the Dicom-files'); %eligo el archivo y el directorio-
        if isequal(archivos,0)||isequal(directorio,0)
            I=[];
            return
        end
        cd(directorio);
        [~,~,~] = fileparts(archivos);
        file=dir(directorio); 
        
        % aca directamente cargo el stack
        [~,spatial,~] = dicomreadVolume(directorio);
        %V = squeeze(V);
        %esta en le version 2022 
        %medVol = medicalVolume(directorio);
        
        %ordeno los archivos 
        [~, reindex] = sort( str2double( regexp( {file.name}, '\d+', 'match', 'once' ))); 
        file = file(reindex) ;
        
        nFrame=length(file);
        image_info=dicominfo(file(1).name); 
       
        
        I=[];
        tic;
        
        n=1;
        for i=1:nFrame
            if  file(i).isdir~=1 % lo hago para evitar . y ..
                archivo=file(i).name
                info=dicominfo(archivo);
                Rescale(n,1)=info.RescaleSlope;
                Rescale(n,2)=info.RescaleIntercept;
                I0=dicomread(archivo);
                I=cat(4,I,I0);
                n=n+1;
            end
        end
        
        
        
        
        tic;
           
%% tiff    
    case 1
        tipoarchivo='*.tif;*.tiff';
        %%%%
        %como deberia ser con version 7.0
        %[archivos,directorio]=uigetfile('*.dcm','Select the Dicom-files', 'MultiSelect', 'on');
        [archivos,directorio]=uigetfile(tipoarchivo,'Select the Tiff-files'); %eligo el archivo y el directorio-
        if isequal(archivos,0)||isequal(directorio,0)
            %txt=5;
            %f_gui_mensaje(1,txt);
            I=[];
            %ScoutView=[];
            return;
        end
        
        
        I=[]; %matriz donde voy a grabar las imagenes
        %ScoutView=[];
        cd(directorio);
        %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        % Carga las imagenes a partir del stack de tiff de 256 x 256 x 125
        %set(gcf,'Pointer','watch');
        image_info=imfinfo(archivos,'tiff');
        for i = 1:length(image_info)
            I(:,:,1,i)=imread(archivos,'tiff',i);
            %f_gui_bar(i,125);
            %if i==125;delete(f_gui_bar);end
        end
        %set(gcf,'Pointer','arrow');
end

cd(currentdirectory);


