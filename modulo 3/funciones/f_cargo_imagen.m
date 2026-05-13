function   [I,image_info,Rescale]=f_cargo_imagen(tiff)

% version 1.1 25/04/2019 
% se saca la info de 
% RescaleSlope;
% RescaleIntercept;


%% tiff dicom = 1 es tiff
%% tiff dicom = 0 es dicom
currentdirectory=pwd;
%nTotalFrame=125; 
switch tiff
    case 0
        tipoarchivo='*.*'; 
        %%%%
        %como deberia ser con version 7.0 
        %[archivos,directorio]=uigetfile('*.dcm','Select the Dicom-files', 'MultiSelect', 'on');
        [archivos,directorio]=uigetfile(tipoarchivo,'Select the Dicom-files'); %eligo el archivo y el directorio-
        if isequal(archivos,0)||isequal(directorio,0)
            %txt=5;
            %f_gui_mensaje(1,txt);
            I=[];
            %ScoutView=[];
            return;
        end
        cd(directorio);
        file=dir(fullfile(directorio,tipoarchivo)); %carga la etrucuta de archivos

        %%%inportante ordenar por numero de slice 
        nFrame=length(file); %el primero es el scan view
        %I=[]; %matriz donde voy a grabar las imagenes
        %ScoutView=[];
        
        image_info=dicominfo(file(3).name); % los dos primeros son . y ..       
        %ScoutView=dicomread(file(1).name);
        %%%Inportante revisar el scan View con dicominfo por que puede ser que
        %%%al cambiarle el nombre quede en otra posicion 
        %clear info;
        I=[];
        tic;
        %image_info=zeros(1,nFrame);
        %set(gcf,'Pointer','watch');
        Rescale=zeros(2,nFrame);
        for i=1:nFrame
            info=dicominfo(file(i).name);  
            Rescale(1,i)=info.RescaleSlope;            
            Rescale(2,i)=info.RescaleIntercept;
            archivos=file(i).name;            
            I0=dicomread(archivos);  
            I=cat(4,I,I0);
            %f_gui_bar(i,nTotalFrame);
        end
        
        
%         %%completo los 125
%         if nFrame<nTotalFrame
%             for i=nFrame+1:nTotalFrame;
%                 archivos=file(nFrame+1).name;
%                 I=cat(4,I,I0);
%                 f_gui_bar(i,nTotalFrame);
%                 if i==nTotalFrame;delete(f_gui_bar);end
%             end %for
%         end %if
%        time=toc;
%        clear file;
%        clear I0;
tic;        
I=double(I); %la transformo en double;
%time1=toc;
%ScoutView=double(ScoutView);
set(gcf,'Pointer','arrow');            
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
 
% txt=6;
% f_gui_mensaje(1,txt);
% 
cd(currentdirectory);
% 
% 
% [n,m,o,p]=size(I);
% %%colocar que sea cumpla p=125; 
% if p==125; 
%     ok=1;
% end 

