   
    clear all
    clc 
    close all
    
   
    
    
    
    
    s_n=[80,140,15];
    s=[50,100,15]; 
    
      
    
    Dosis=rand(s).*1000;
    A=zeros(s);
    A(20:40,50:80,:)=1;
    Dosis=Dosis.*A; 
    
    
    ny=s_n(2);    
    nx=s_n(1);
    nz=s_n(3);
   
    %method='linear';
    method='cubic';
    %method='spline';
    extrapval=NaN; 
    
    
[y, x ,z]=ndgrid(linspace(1,s(1),nx),...
          linspace(1,s(2),ny),...
          linspace(1,s(3),nz));
Dint=interp3(Dosis,x,y,z,method,extrapval);
           
%     %method='linear';
%     method='cubic';
%     %method='spline';
%     extrapval=-1; 
%     
%     a=s(1)/p(1)-1;
%     b=s(2)/p(2)-1;
%     c=s(3)/p(3)-1;
%     
%     [xc,yc,zc]=meshgrid(0:p(2):b,0:p(1):a,0:p(3):c);
%     [xx,yy,zz]=meshgrid(1:1:s_n(2),1:1:s_n(1),1:s_n(3));
%     
%     Dint=interp3(xc,yc,zc,Dosis,xx,yy,zz,method,extrapval);
%     
   
    s1=size(Dint);
    ok=s1==s_n;
    ok=sum(ok);
    
    extp=Dint==extrapval;
    ok2=sum(extp(:)); 
    
    ok3=Dint==0; 
    ok3=sum(ok3(:)); 
    produc=prod(s_n);
    
    figure(100)
    for i=1:s(3)
      imshow(Dosis(:,:,i),[])
      colormap(jet)
      pause(0.5)
    end
    
    figure(101)
    for i=1:s_n(3)
      imshow(Dint(:,:,i),[])
      colormap(jet)
      pause(0.5)
    end 
    
    figure(102)
    imshow(Dint(:,:,5),[])
    colormap(jet)