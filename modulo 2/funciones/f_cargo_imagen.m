function   [I,image_info]=f_cargo_imagen(tiff)

%% Version=1.1 
%% tiff dicom = 1 es tiff
%% tiff dicom = 0 es dicom
currentdirectory=pwd;
%tiff=0;
switch tiff
    case 0
        tipoarchivo='*.dcm';'*.*';
        %tipoarchivo='*.*';
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
        file=dir(fullfile(directorio,tipoarchivo)); %carga la etrucuta de archivos
        
        %%%inportante ordenar por numero de slice
%         nFrame=length(file); %el primero es el scan view
%         I=[]; %matriz donde voy a grabar las imagenes
%         %ScoutView=[];
%         info=dicominfo(file(1).name);
%         %ScoutView=dicomread(file(1).name);
%         %%%Inportante revisar el scan View con dicominfo por que puede ser que
%         %%%al cambiarle el nombre quede en otra posicion
%         clear info;
%         I=[];
        tic;
        image_info=dicominfo(archivos);
        W=image_info(1,1).Width;
        H=image_info(1,1).Height;  
        nslice=length(file);
        %I=zeros(H,W,1,nslice);
        I=[];
        set(gcf,'Pointer','watch');
        for i=1:nslice;
            image_info(i)=dicominfo(file(i).name);
            I0=dicomread(file(i).name);
            I=cat(4,I,I0);
            %f_gui_bar(i,nTotalFrame);
        end
        tic;
        I=double(I); 
        set(gcf,'Pointer','arrow');
    case 1
        tipoarchivo='*.tif;*.tiff';
        %%%%
        %como deberia ser con version 7.0
        %[archivos,directorio]=uigetfile('*.dcm','Select the Dicom-files', 'MultiSelect', 'on');
        [archivos,directorio]=uigetfile(tipoarchivo,'Select the Tiff-files'); %eligo el archivo y el directorio-
        if isequal(archivos,0)||isequal(directorio,0)
%             %txt=5;
%             %f_gui_mensaje(1,txt);
%             I=[];
%             %ScoutView=[];
            return;
        end
                
         cd(directorio);
         image_info=imfinfo(archivos,'tiff');
%         W=image_info(1,1).Width;
%         H=image_info(1,1).Height;  
         nslice=length(image_info);
%         I=zeros(H,W,3,nslice);
        for i = 1:nslice
            I(:,:,:,i)=imread(archivos,'tiff',i);
        end
end

cd(currentdirectory);
end

