clc
close all
%clear 
%% 
index.aire=1;
index.liver=90;
index.tejido_blando=30;
index.hueso=80; 
index.lung=50; 
index.tumor=100; %>100
%
nfig=1; 
%%
currentdirectory=pwd;
newpath=[currentdirectory,'\funciones']; 
path(path,newpath)
%%
directorio=f_creo_directorio;
%%
[p,file_paciente]=f_cargo_mat;
if ~isempty(p)
    paciente=p.paciente;
    clear p 
end 

%% Cargo la imagen original 

if isfield(paciente,'CT')
    I=paciente.CT;
else
    tiff=0; %1 tiff 0 dicom
    clc
    disp(' ')
    disp(' Ingrese la imagen CT a segmentar' )
    
    [I,image_info]=f_cargo_imagen(tiff);
    I=squeeze(I);
end
 
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

corte=0;
for i=1:nslice 
   
    [bw_lung,bw_intestino,corte]=f_saco_lung(I(:,:,i),corte); 
    
%     figure(500)
%     imshowpair(bw_lung,bw_intestino,'montage')
%     title(['Slice number # ',num2str(i)]);
%     pause(0.1)
    
       
    I(:,:,i)=double(I(:,:,i)).*double(~bw_lung);  
    I(:,:,i)=double(I(:,:,i)).*double(~bw_intestino);
    Phantom(:,:,i)=Phantom(:,:,i)+bw_intestino.*index.aire;
    Phantom(:,:,i)=Phantom(:,:,i)+bw_lung.*index.lung; 
end
%a=unique(Phantom); 
clear bw_lung bw_intestino


%% saco hueso
tic 
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
    Phantom(:,:,i)=Phantom(:,:,i)+BW_hueso.*index.hueso;     
end
time=toc; 
%a=unique(Phantom);
clear BW_hueso
% figure(2) 
% for i=1:nslice
%     imshowpair(I(:,:,i),Phantom(:,:,i),'montage')
%     %imshow(I(:,:,i),[])
%     title(['Slice number # ',num2str(i)]);
%     pause(0.1)
%  end 


 figure(2)
 for i=1:nslice
     %imshowpair(I(:,:,i),Phantom(:,:,i),'montage')
     imshow(I(:,:,i),[])
     title(['Slice number # ',num2str(i)]);
     pause(0.1)
 end 
p=1;
%% 
figure(2)
h=imshow(I,[]);
title('Original Image')
% Create mask and specify seed location. You can also use roipoly to create the mask interactively.
mask=roipoly;
%mask = false(size(I)); 
%mask(170,70) = true;

% Compute the weight array based on grayscale intensity differences.
W = graydiffweight(I, mask, 'GrayDifferenceCutoff', 25);

% Segment the image using the weights.
thresh = 0.01;
[BW, D] = imsegfmm(W, mask, thresh);
dd=D(:,:,1)>0.1;

st=strel('disk',18);

d1=imerode(dd,st);

mul=immultiply(d1,I(:,:,1));

Img1 = imresize(mul,[256 256]);
Img=double(Img1(:,:,1));   
G=fspecial('gaussian',5);
Img_smooth=conv2(Img,G,'same');  
[Ix,Iy]=gradient(Img_smooth);
f=Ix.^2+Iy.^2;
g=1./(1+f);    
equldis=2; weight=6;   
width = 256;
height = 256;
radius = 10;
centerW = width/3.3;
centerH = height/2.3;
[W,H] = meshgrid(1:width,1:height);
mask = ((W-centerW).^2 + (H-centerH).^2) < radius^2;


%  mask=roipoly(Img1)
if  mean2(I2)>50
mask=imread('mask1.jpg');
else
mask=imread('mask.jpg');
end

BW = double(im2bw(mask)); 
% BW=mask;
[nrow, ncol]=size(Img1);
c0=4; 
initialLSF= -c0*2*(0.5-BW); 
u=initialLSF;
u=initialLSF;
evolution=230;
% move evolution
for n=1:evolution
    u=levelset(u, g ,equldis, weight);    
    if mod(n,20)==0
         pause(1);
        figure(4),imshow(Imgg, [0, 255]);colormap(gray);hold on;
        [c,h] = contour(u,[0 0],'r');        
        title('level set');
        hold off;
    end
end

u=imfill(u,'holes');

% u=immultiply(u,u1);
st=strel('disk',2);
u2=imdilate(u,st);
u1=double(imclearborder(im2bw(u)));
imwrite(u1,'seg.jpg')
st1=strel('disk',1);
aa=double(imread('seg.jpg'));
aa=imerode(aa,st1);

figure,
imshow(Imgg, [0, 255]);colormap(gray);hold on;
[c,h] = contour(1-aa,[0 0],'r');

segg=immultiply(u1,double(rgb2gray(Imgg)));


figure,
subplot(2,2,1)
imshow(I)
title('input')

subplot(2,2,2)
imshow(u1)
title('binary')

subplot(2,2,4)
imshow(uint8(segg))
title('segment')

subplot(2,2,3)
imshow(Imgg, [0, 255]);colormap(gray);hold on;
[c,h] = contour(1-aa,[0 0],'r');
title('boundary')





