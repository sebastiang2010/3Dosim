function [Phantom,corte_aire]=f_saco_aire(Phantom1) %,n_aire)

% version 1.0 
Phantom_original=Phantom1;
n_aire=0; 

for i=1:size(Phantom1,3)
    [x,y]=find(Phantom1(:,:,i)~=n_aire);
    if size(x,1)>0 && size(y,1)>0
        x1(i)=min(x);
        y1(i)=min(y);
        x2(i)=max(x);
        y2(i)=max(y);
    else
        Phantom=Phantom_original;
        corte_aire=[];
        clc
        disp('.....')
        disp(' La imagen no fue modificada ');
        pause(0.25)
        return
    end     
end

xmin=min(x1);
ymin=min(y1);
xmax=max(x2);
ymax=max(y2);

n=0;
[a,b,~]=size(Phantom1);
if xmax+2<=a;n=n+1;end
if xmin-2>=1;n=n+1;end
if ymax<=b;n=n+1;end
if ymin-2>=1;n=n+1;end

if n==4
    Phantom=Phantom1(xmin-2:xmax+2,ymin-2:ymax,:);
    figure(50)
    for i=1:size(Phantom,3)
        imshow(Phantom(:,:,i),[]);         
        h=title(['Slice number # ',num2str(i)]);
        set(h,'FontWeight','bold')
        colormap(jet)
        pause(0.15)
    end
    clc
    disp('.....')
    resp=input(' La imagen fue recortada correctamente: >0 (SI) // 0 (NO) ');
    if resp>0
        corte_aire=[xmin-2,xmax+2,ymin-2,ymax];    
        % Ojo que queda [ymin ymax xmin xmax]
    else
        clc
        %I=Ioriginal;
        Phantom=Phantom_original;
        corte_aire=[];
        
        clc
        disp('.....')
        disp(' La imagen no fue modificada ');
        pause(0.25)
    end
    
else
    %I=Ioriginal;
    Phantom=Phantom_original;
    corte_aire=[];
    disp('.....')
    disp(' La imagen no fue modificada ');
    pause(0.25)
end




