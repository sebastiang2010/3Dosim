function   [I,image_info]=f_cargo_imagen(tiff)

%% version 2.0 22/01/17

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
            return
        end
        cd(directorio);
        [~,~, ext] = fileparts(archivos);
        file=dir(fullfile(directorio,ext));
        
        nFrame=length(file);
        image_info=dicominfo(file(3).name);
       
        I=[];
        tic;
        inicio=1;
        if isempty(ext)==1;inicio=3;           
        end % esta el archivo . y .. 
                       
        %set(gcf,'Pointer','watch');
        a=zeros(1,nFrame-2);
        for i=inicio:nFrame 
            a(i-2)=str2double(file(i).name); 
        end 
        
        min1=min(a(:));
        max1=max(a(:)); 
        for i=min1:max1                             
                archivo=[file(1).folder,'\',num2str(i)];
                I0=dicomread(archivo);
                I=cat(4,I,I0);            
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


