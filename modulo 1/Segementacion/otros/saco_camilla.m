close all 
clc 
%
index.aire=1;
index.liver=50;
index.tejido_blando=30;
index.hueso=80; 
index.lung=70; 
index.tumor=100; %>100


currentdirectory=pwd;
newpath=[currentdirectory,'\funciones']; 
path(path,newpath)

directorio=f_creo_directorio;

%% Cargo la imagen original 
tiff=0; %1 tiff 0 dicom
[I,image_info]=f_cargo_imagen(tiff);
I=squeeze(I);

Phantom=zeros(size(I)); 


nslice=size(I,3); 

for i=1:nslice 
I(:,:,i) = imadjust(I(:,:,i),stretchlim(I(:,:,i)),[]);
end 

% for i=1:nslice
%     figure(1)
%     imshow(I(:,:,i),[])
%     title(['Slice number # ',num2str(i)]);
%     pause(0.1)
% end 

%% OK
for i=1:nslice
    [BW_camilla] =f_saco_camilla(I(:,:,i)); % saco camillas y partes pequenas 
%     imshow(BW_camilla,[])
%     title(['Slice number # ',num2str(i)]);
%     pause(0.1)   
    I(:,:,i)=double(I(:,:,i)).*double(~BW_camilla); % sin camilla
        
end 
clear BW_camilla
% for i=1:nslice
%     figure(1)
%     imshow(I(:,:,i),[])
%     title(['Slice number # ',num2str(i)]);
%     pause(0.1)
% end

%% saco aire_periferico OK 
for i=1:nslice 
    [bw_s_aire] =f_saco_aire(I(:,:,i)); % saco aire
%     figure(500)
%     imshow(bw_s_aire,[])
    I(:,:,i)=double(I(:,:,i)).*double(bw_s_aire); % sin camilla       
end 
clear bw_s_aire; 
% 
% for i=1:nslice 
%     figure(2)
%     imshow(I(:,:,i),[])
%     title(['Slice number # ',num2str(i)]);
%     pause(0.1)
% end

%% saco hueso
for i=1:nslice 
    %if i==1 
     %  J = histeq(I(:,:,159)); 
     %  imshow(J,[]) 
      % imcontrast(gca);
    %end 
    
    %J= imadjust(J,[60000/65535 1],[]);
    [BW_hueso] =f_saco_hueso(I(:,:,i)); % saco hueso 
    
%     figure(500)
%     imshow(BW_hueso,[])
%     title(['Slice number # ',num2str(i)]);
%     pause(0.1)
    
    I(:,:,i)=double(I(:,:,i)).*double(~BW_hueso); % sin camilla
    Phantom(:,:,i)=BW_hueso.*index.hueso;     
end 
clear BW_hueso 
% figure(2) 
% for i=1:nslice
%     imshowpair(I(:,:,i),Phantom(:,:,i),'montage')
%     %imshow(I(:,:,i),[])
%     title(['Slice number # ',num2str(i)]);
%     pause(0.1)
%  end 

corte=0;
for i=1:nslice 
   
    [bw_lung,bw_intestino,corte] =f_saco_lung(I(:,:,i),corte); 
    
%     figure(500)
%     imshowpair(bw_lung,bw_intestino,'montage')
%     title(['Slice number # ',num2str(i)]);
%     pause(0.1)
    
       
    I(:,:,i)=double(I(:,:,i)).*double(~bw_lung);  
    I(:,:,i)=double(I(:,:,i)).*double(~bw_intestino);
    Phantom(:,:,i)=Phantom(:,:,i)+bw_intestino.*index.aire;
    Phantom(:,:,i)=Phantom(:,:,i)+bw_lung.*index.lung; 
end 
clear bw_lung bw_intestino 
figure(2)
for i=1:nslice
    
    imshowpair(I(:,:,i),Phantom(:,:,i),'montage')
    %imshow(I(:,:,i),[])
    title(['Slice number # ',num2str(i)]);
    pause(0.1)
end 

