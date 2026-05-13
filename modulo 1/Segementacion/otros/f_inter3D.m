function [Iint,ok]=f_inter3D(I,s_n)


s=size(I);

%method='linear';
method='cubic';
%method='spline';
extrapval=NaN;

[y, x ,z]=ndgrid(linspace(1,s(1),s_n(1)),...
    linspace(1,s(2),s_n(2)),...
    linspace(1,s(3),s_n(3)));

Iint=interp3(I,x,y,z,method,extrapval);

s1=size(Iint);
ok1=s1==s_n;
ok1=sum(ok1);
% 
extp=Iint==extrapval;
ok2=sum(extp(:));
% 
neg=Iint<0;
Iint(neg)=0; 


ok=[ok1,ok2];

% figure(100)
% for i=1:s(3)
%     imshow(I(:,:,i),[])
%     colormap(jet)
%     pause(0.5)
% end
% 
% figure(101)
% for i=1:s_n(3)
%     imshow(Iint(:,:,i),[])
%     colormap(jet)
%     pause(0.5)
% end
