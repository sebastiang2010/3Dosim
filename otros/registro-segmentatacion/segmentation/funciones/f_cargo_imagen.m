function   [I,image_info]=f_cargo_imagen(tiff)

%% version 2.1 30/06/17

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
            %ScoutView=[];
            return;
        end
        cd(directorio);
        [~,~, ext] = fileparts(archivos);
        file=dir(fullfile(directorio,ext));
        
        nFrame=length(file); %el primero es el scan view
        image_info=dicominfo(file(3).name);
       
        I=[];
        tic;
        inicio=1;
        if isempty(ext)==1;inicio=3;end
        %set(gcf,'Pointer','watch');
        for i=inicio:nFrame;
            archivos=file(i).name;             % la primer imagen es el scan view
            I0=dicomread(archivos);
            I=cat(4,I,I0);
            %f_gui_bar(i,nTotalFrame);
        end
        
        tic;
        %I=double(I); %la transformo en double;
        %time1=toc;
        %set(gcf,'Pointer','arrow');
   
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


