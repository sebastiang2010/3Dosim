function [I1,BW_hueso] = f_seg_hueso_1(I1)

BW_hueso=zeros(size(I1));

%% mejorar el metodo...
%close all
clc 
disp(' ')
op=input(' Segmentacion automatica (0-Si) // (~=0-No) ');

x2=255;
for j=1:size(I1,3)
    I=I1(:,:,j);
    
%     %if op~=0
%         figure(501)
%         
%         imhist(uint8(I>0)) %buscar el minimo relativo
%     %end
    
    x1=70; %analizar buscar el mejor
    clc
    parar=1;
    while parar==1
        
        ind=find(I>=x1 & I<=x2);
        
        [promedio,desv,entropia]=f_entropy(I,ind);
        
        bw_hueso=zeros(size(I));
        bw_hueso(ind)=1;
        
        if op==0
            if desv<11
                parar=-1;
            else
                x1=x1+1;
            end
        end
        
        
        bw_hueso=bwareaopen(bw_hueso,5);
        
        se = strel('disk',1);
        bw_hueso = imclose(bw_hueso,se);
        
             
        if op~=0
            clc
            ind=find(bw_hueso==1);
            [y,x]=ind2sub(size(bw_hueso),ind);
            figure(503)
            h=title(['Slice number # ',num2str(j),'   /   x1 = ',num2str(x1)]);
            set(h,'FontWeight','bold')
            imshow(I1(:,:,j),[])
            hold on
            h=scatter(x,y,'g','.');
            set(h,'SizeData',12)
            pause(0.1)
            key=input(' Ingrese ENTER para incrementar x1 ');
            if isempty(key)
                x1=x1+1;
            else
                parar=-1;
            end
        else
            %
        end
 
        
        
    end
BW_hueso(:,:,j)=bw_hueso;

nmap=255;
map=f_map(nmap);
ind=bw_hueso==1;
I(ind)=nmap+3;
%I2=ind2rgb(I1(:,:,vertices(i,3)),map);
I2=ind2rgb(I,map);
figure(505);
imshow(I2,[])
pause(0.1)
clear I2;

% figure(505)
% imshow(bw_hueso,[])
% h=title(['Slice number # ',num2str(j)]);
% set(h,'FontWeight','bold')
% pause(0.1)
end

BW_hueso=double(BW_hueso);
I1=double(I1);
I1=I1.*~BW_hueso;

