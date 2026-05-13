% repeat the clustering 3 times to avoid local minima

close all 
%clear all 
clc
%% 
% %
currentdirectory=pwd;
newpath=[currentdirectory,'\funciones']; 
path(path,newpath)
%
directorio=f_creo_directorio;
%%  
clc 
nfig=1; 
%% cargo tiff
tiff=1; %1 tiff 0 dicom

% [CT,info_CT]=f_cargo_imagen(tiff);
% CT=squeeze(CT);
% CT=uint8(CT); 
% 


% 
% s=size(CT);
% higado=zeros(s);
% C=zeros(s);
% 
% tic
% for j=1:s(3)
%     close all
%     clusters=20;
%     [mu,maks]=f_kmeans(CT(:,:,j),clusters);
%     
% %     figure(nfig)
% %     nfig=nfig+1;
% %     set(gcf,'Render','OpenGL')
% %     for i=1:clusters
% %         imshow(maks==i,[])
% %         h=title([' Cluster # ',num2str(i)]);
% %         set(h,'FontWeight','bold')
% %         pause(0.2)
% %     end
% %     
%     
%     A=zeros(s(1),s(2));
%     %antes 14:16
%     for i=14:16
%         A=A+maks==i;            
%     end
%     A=uint8(A);
%     [level,em] = graythresh(A);
%     A = im2bw(A,level);
%     I=uint8(CT(:,:,j)).*uint8(A);
%     
% %     figure()
% %     %nfig=nfig+1;
% %     imshow(I,[])
%     
%     repito=1;
%     for i=1:repito
%         h=fspecial('gaussian',4,7);
%         I= imfilter(I,h);
%     end
%     
% %     figure(nfig)
% %     nfig=nfig+1;
% %     imshow(I,[])
%     
%     [level,em] = graythresh(I);
%     B = im2bw(I,level);
%     
%     fill_B=imfill(B,'holes');
%     
% %     figure(nfig)
% %     nfig=nfig+1;
% %     imshow(I,[])
%     
%     [L, num] = bwlabel(fill_B,8);
%     % for i=1:num(end)
%     %     imshow(L==i,[]);
%     %     pause(0.2)
%     % end
%     
% 
%     
%     C(:,:,j)=C(:,:,j)+L;
% end
% time=toc;
% 
% figure(10)
% for i=1:s(3)
%    
%     %nfig=nfig+1;
%     imshow(C(:,:,i),[])
%     colormap(jet)
%     h=title([' Slice # ',num2str(j)]);
%     set(h,'FontWeight','bold')
%     pause(0.2)
% end
% 





s=size(C);
BW=zeros(s);
for i=1:s(3)
[level,em] = graythresh(C(:,:,i));
BW(:,:,i) = im2bw(C(:,:,i),level);
end

% ingresado por uno 
[L, NUM] = bwlabeln(BW(:,:,20:150),6);


s=size(L);
%for i=1:s(3)
   
     %nfig=nfig+1;
     imshow((L(:,:,130)),[])
     colormap(jet(num))
     h=title([' Slice # ',num2str(i)]);
     set(h,'FontWeight','bold')
     pause(0.2)
%end

















    %clc
    %STATS = regionprops(L,'all');%,'EulerNumber','Orientation','BoundingBox''Extent',...
    %'Perimeter','Centroid''Extrema');
    
%     x1=128;
%     y1=239;
%     tol=50;
%     a=zeros(4,1);
%     ok=zeros(1,num);
%     for i=1:num; 
%        c=STATS(i).Centroid;
%        x=c(1);
%        y=c(2);
%        if x+tol>x1;a(1)=1;end  
%        if x-tol<x1;a(2)=1;end
%        if y+tol>y1;a(3)=1;end
%        if y-tol<y1;a(4)=1;end
%        b=sum(a); 
%        if b==4;ok(i)=1;end
%        a=zeros(4,1);
%     end

%     a=find(ok==1);
%     
%     A=zeros(s(1),s(2));
%     for i=1:length(a);
%         ind1=L==a(i);
%         A=A+double(ind1);
%     end
%     
%     figure(nfig)
%     nfig=nfig+1;
%     imshow(A,[])
%     colormap(jet)
%     h=title([' Slice # ',num2str(j)]);
%     set(h,'FontWeight','bold')
    
%end

% figure(nfig)
% nfig=nfig+1;
% imshow(higado(:,:,j),[])
% h=title([' Slice # ',num2str(j)]);
% set(h,'FontWeight','bold')
%  
 
 
 
 
% nColors=1; 
% [cluster_idx, cluster_center] = kmeans(CT,nColors,'distance','sqEuclidean', ...
%                                       'Replicates',15);
% 
% pixel_labels = reshape(cluster_idx,512,512);
