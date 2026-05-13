close all 
clc
%clear all 

currentdirectory=pwd;
newpath=[currentdirectory,'\funciones']; 
path(path,newpath)

volumen=0.08*0.08*0.25;

s_n=[386,250,10]; 
file=[];
flip=0; 
% % if op==1;busco='tally    1  ';end
% % if op==4;busco='tally    8  ';end
% % if op==2;busco='tally    3  ';end
% % if op==3;busco='tally   18 ';end
% % if op==5;busco='tally   26';end
% % if op==6;busco='tally    6';end
% 
% %%
% op=1; %tally 1
% [D1,error1,file]=f_cargo_mctall(s_n,op,file);
% % Dosis MeV/cm^3/source_particle
% D1=f_flip(D1,flip);
% error1=f_flip(error1,flip);
% error1=error1.*100;
% % %%
% op=2; % tally 3 
% [D3,error3,file]=f_cargo_mctall(s_n,op,file);
% % Dosis MeV/cm^3/source_particle
% D3=f_flip(D3,flip);
% error3=f_flip(error3,flip);
% error3=error3.*100;
% op=4; % 
% [D8,error8,file]=f_cargo_mctall(s_n,op,file);
% % Dosis MeV/cm^3/source_particle
% D8=f_flip(D8,flip);
% error8=f_flip(error8,flip);
% error8=error8.*100;

max1=max(D8(:));
ind=find(D8==max1); 
[x,y,z]=ind2sub(s_n,ind);

figure(100)
imshow(D8(:,:,z),[])
colormap(jet)


x1=1:1:250;

Df8=D8(:,y,z)/volumen;
Df6=D1(:,y,z);
D_mas_f6=D3(:,y,z);

figure(1)
h=plot(x1,Df8);
set(h,'Color','g')
hold on 
h=plot(x1,Df6);
set(h,'Color','r')
h=plot(x1,D_mas_f6);
set(h,'Color','k')
scatter(x,max1/volumen,'b','.')



diff=(Df8-D_mas_f6)./Df8;
diff=diff.*100;
figure(3)
plot(x1,diff)

f8=D8(x,y,z);
f6=D1(x,y,z);
mas_f6=D3(x,y,z);


f8=f8/volumen;

clc 
disp(' ')
disp(['  f8/volumen              [MeV/cm^3]:  ',num2str(f8)]);
disp(['  +f6 (mesh tally 3)      [MeV/cm^3]:  ',num2str(mas_f6)]);



