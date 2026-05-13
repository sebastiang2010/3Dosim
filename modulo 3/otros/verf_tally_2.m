close all 
clc
%clear all 

currentdirectory=pwd;
newpath=[currentdirectory,'\funciones']; 
path(path,newpath)


tiff=1; %1 tiff 2 dicom  
Phantom=f_cargo_imagen(tiff);
Phantom=squeeze(Phantom); 
Phantom=uint8(Phantom);
s_n=size(Phantom);


densidad1=paciente.densidad; 
cell=paciente.cell; 


densidad=[cell densidad1];

volumen=0.08*0.08*0.25;

masa=[];
masa(:,1)=densidad(:,1);
%g
masa(:,2)=densidad(:,2).*volumen;
%Kg 
%masa(:,2)=masa(:,2)/1000;    



%s_n=[250,386,10]; %es el tamaño del imagen queda tra
file=[];
flip=1; 
% % if op==1;busco='tally    1  ';end
% % if op==4;busco='tally    8  ';end
% % if op==2;busco='tally    3  ';end
% % if op==3;busco='tally   18 ';end
% % if op==5;busco='tally   26';end
% % if op==6;busco='tally    6';end
% 
% %
tic 
op=1; %tally 1
[D1,error1,file]=f_cargo_mctall(s_n,op,file);
% Dosis MeV/cm^3/source_particle
D1=f_flip(D1,flip);
error1=f_flip(error1,flip);
error1=error1.*100;
% %%
op=2; % tally 3
[D3,error3,file]=f_cargo_mctall(s_n,op,file);
% Dosis MeV/cm^3/source_particle
D3=f_flip(D3,flip);
error3=f_flip(error3,flip);
error3=error3.*100;
%%
% op=3; %
% [D8,error8,file]=f_cargo_mctall(s_n,op,file);
% % Dosis MeV/source_particle
% D8=f_flip(D8,flip);
% error8=f_flip(error8,flip);
% error8=error8.*100;
%%
% op=5; %
% [D6,error6,file]=f_cargo_mctall(s_n,op,file);
% % Dosis MeV/g/source_particle
% D6=f_flip(D6,flip);
% error6=f_flip(error6,flip);
% error6=error6.*100;
% 
% f8=5.85848E-17; %MeV 
% ind=find(D8==f8); 
% [x1,y1,z1]=ind2sub(s_n,ind);
%%
time=toc;  

%%
x1=83;
y1=45;
z1=3;

max1=max(D8(:));
ind=find(D8==max1); 
[x,y,z]=ind2sub(s_n,ind);

D8=f_div_masa(D8,Phantom,masa); %MeV/g 
D3=f_div_densidad(D3,Phantom,densidad); %MeV/g
D6=f_div_masa(D6,Phantom,masa); % MeV/g 

figure(100)
imshow(D8(:,:,z),[])
colormap(jet)
figure(101)
imshow(D3(:,:,z),[])
colormap(jet)
figure(102)
imshow(D6(:,:,z),[])

f8=D8(x,y,z);
mas_f6=D6(x,y,z);
tally_3=D3(x,y,z);

f18=D8(x1,y1,z1);
mas_f16=D6(x1,y1,z1);
tally_13=D3(x1,y1,z1);

clc 
disp('Maximo  ')
disp(['  f8 (div masa)                  :   [MeV/g]:  ',num2str(f8)]);
disp(['  error f8                       :  ',num2str(error8(x,y,z))]);
disp(['  +f6 (div masa)                 :   [MeV/g]:  ',num2str(mas_f6)]);
disp(['  error +f6                      :  ',num2str(error6(x,y,z))]);
disp(['  mesh tally 3 (div densidad )   :    [MeV/g]:  ',num2str(tally_3)]);
disp(['  error tally3                   :  ',num2str(error3(x,y,z))]);
%clc 
disp('tally verf ')
disp(['  f8 (div masa)                  :   [MeV/g]:  ',num2str(f18)]);
disp(['  error f8                       :  ',num2str(error8(x1,y1,z1))]);
disp(['  +f6 (div masa)                 :   [MeV/g]:  ',num2str(mas_f16)]);
disp(['  error +f6                      :  ',num2str(error6(x1,y1,z1))]);
disp(['  mesh tally 3 (div densidad )   :    [MeV/g]:  ',num2str(tally_13)]);
disp(['  error tally3                   :  ',num2str(error3(x1,y1,z1))]);
