function [recorte]=f_recorto(Phantom1,ind_liver,nshow)

% version 2.0 
% se podria incluir z 

ind=find(Phantom1(:,:,:)==ind_liver);
[x,y,~]=ind2sub(size(Phantom1),ind);
xmin=min(x(:));
ymin=min(y(:));
xmax=max(x(:));
ymax=max(y(:));


ref=10; % pixeles que quito 
n=0;
[a,b,~]=size(Phantom1);
if xmax+ref<=a;n=n+1;end
if xmin-ref>=1;n=n+1;end
if ymax+ref<=b;n=n+1;end
if ymin-ref>=1;n=n+1;end

if n==4;
    Phantom=Phantom1(xmin-ref:xmax+ref,ymin-ref:ymax+ref,:);
    figure(100)
    for i=1:nshow
        imshow(Phantom(:,:,i),[]);         
        h=title(['Slice number # ',num2str(i)]);
        set(h,'FontWeight','bold')
        colormap(jet)
        pause(0.1)
    end
    clc
    disp('.....')
    resp=input(' La imagen fue recortada correctamente: >0 (SI) // 0 (NO) ');
    if resp>0;
        recorte=[xmin-ref,xmax+ref,ymin-ref,ymax+ref];    
        % Ojo que queda [ymin ymax xmin xmax]
    else
        clc
        recorte=[];
        
        disp('.....')
        disp(' La imagen no fue modificada ');
        pause(0.25)
    end
    
else
    recorte=[];
    disp('.....')
    disp(' La imagen no fue modificada ');
    pause(0.25)
end




