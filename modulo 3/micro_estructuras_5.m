%% Micro estructuras 
%Esto es valido solo para el higado
%por lo tanto hay que usar el Phantoma para seleccionar solo el higado 
% usar la densidad que estaba antes
close all
clear 
clc

nfig=1; 
% 
n_colors = 1024;
cmap = jet(n_colors);
cmap(1, :) = [1 1 1];

%% R_SAND 
SAND_inf=49.72; %Gy/MBq


%HepaticArteria(1)
%BileDuc(2)
%PortalVein(3);
%Central_vein(4); 

% son muy parecidos tabla 
% 22 uS/ah  
% R_SAND(1,1)=3.1; 
% R_SAND(1,2)=1.7;
% R_SAND(1,3)=1.7; 
% R_SAND(1,4)=0.9; 
% 24
% R_SAND(1,1)=3.1; 
% R_SAND(1,2)=1.7;
% R_SAND(1,3)=1.7; 
% R_SAND(1,4)=0.9; 
% % 43
% R_SAND(1,1)=3.1; 
% R_SAND(1,2)=1.7;
% R_SAND(1,3)=1.7; 
% R_SAND(1,4)=0.9; 

%%
load('C:\MAT\3Dosim\paciente.mat')
%vPET=paciente.vPET; 
vCT=paciente.vCT; 
PET1=paciente.PET_intp.PET;
vPET=paciente.PET_intp.vPET; 
%factor=paciente.PET_exp.factor; 
I1=paciente.Phantom; 
index=paciente.index;
actividad=paciente.Actividad_GBq;   

a=max(PET1(:)); 


%load('rescalado.mat')
%PET_org=paciente.PET;

volumen=prod(vPET./10); %cm 
masa1=1.06*volumen;  %el volumen esta en cm^3  

D=paciente.Dosis.voxel; 
CT=paciente.CT; 

A=PET1; 
%A=PET./prod(factor);
uS_ah=A./50; % asumo de recina 
A=A.*1e-6; %Bq2MBq  
A=A./masa1; %MBq/g

%% maximos 
s=size(A);
ind_maxA=find(max(A(:))==A);
ind_maxD=find(max(D(:))==D); 
[xa,ya,za]=ind2sub(s,ind_maxA); 
[xD,yD,zD]=ind2sub(s,ind_maxD);

uS_ah1=uS_ah(xa,ya,za);
%%
 figure(nfig)
 nfig=nfig+1;
 imshow(I1(:,:,80),[])
 hold on 
 imshow(D(:,:,80),[]); 
 alpha 0.4
 colormap(cmap)
 colorbar 
 unit=' Gy';
 title(' Dosis MCNP ')
 valor = f_obtener_coordenadas(D(:,:,80),unit); 
 


 % figure(nfig)
 % nfig=nfig+1; 
 % imshow(CT(:,:,zD),[])
 % hold on 
 % h=imshow(A(:,:,zD),[]); 
 % colormap(cmap)
 % alpha 0.4
 % %alpha 0.2

%% factor
% ESsta en el Excel 

micro.hepatic_arteria=154; %Gy*g*MBq^-1;
micro.bile_duct=85;
micro.portal_vein=85.5;
%micro.portal_vein=85; %valor real 
micro.parenquima=50; 
micro.central_vein=45;

% tengo que consideras solo el higado 
%ind=I1==index.liver; %higado sin tumor

Dmicro(1).D=A.*micro.hepatic_arteria; %Bq/g*(Gy*g*Bq^-1)=Gy
Dmicro(2).D=A.*micro.bile_duct; %Bq/g*(Gy*g*Bq^-1)=Gy   
Dmicro(3).D=A.*micro.portal_vein;        %Bq/g*(Gy*g*Bq^-1)=Gy
Dmicro(4).D=A.*micro.parenquima;        %Bq/g*(Gy*g*Bq^-1)=Gy % no es necesario porque es lo que calculo con MCNP 
Dmicro(5).D=A.*micro.central_vein;        %Bq/g*(Gy*g*Bq^-1)=Gy


DosisParenquima=Dmicro(4).D; 


% figure(1500)
% DHepaticArteria=Dmicro(1).D; 
% imshow(DHepaticArteria(:,:,80),[])
% colormap jet 
% max1=max(DHepaticArteria(:));
% clim([0 max1])
% colorbar 
% title(' Dosis A*micro_estructura (Hepatic Arteria)')
% unit=' Gy';
% %valor = f_obtener_coordenadas(DHepaticArteria(:,:,80),unit);
% figure(1501)
% % Asigna el denominador (A.parenquima) y la imagen D
% Dparenquima = Dmicro(4).D; 
% % Crea una máscara para evitar la división por cero
% mask = Dparenquima ~= 0;
% % Inicializa la matriz ratio con ceros (o podrías usar NaN en lugar de 0)
% ratio = zeros(s);
% % Realiza la división solo donde el denominador no es cero
% ratio(mask) = D(mask) ./ Dparenquima(mask);
% ratio(~mask) = NaN;
% minValue = min(ratio(ratio > 0), [], 'all');
% maxValue = max(ratio(:)); 
% imshow(ratio(:,:,80), [])
% colormap jet 
% clim([minValue, maxValue])
% colorbar 
% title('Ratio entre D / A.parenquima')
% unit = ' ';
% valor = f_obtener_coordenadas(ratio(:,:,80), unit);


% %%  usando el R_SAND 
 R_SAND1(1,1)=3.1; %  Hepatic Arteria 
 R_SAND1(1,2)=1.7; % Bile Duct 
 R_SAND1(1,3)=1.7; %  Portal Vein  
 R_SAND1(1,4)=1; % Parenquima 
 R_SAND1(1,5)=0.9; % Cemtral Vein 

%% buscar cual es el modelo 
R_SAND.hepatic_arteria=3.1; 
R_SAND.bile_duct=1.7; 
R_SAND.portal_vein=1.7; 
R_SAND.parenquima=1; 
R_SAND.central_vein=0.9; 

D_RSand_micro(1).D=D.*R_SAND1(1,1); % Gy
D_RSand_micro(2).D=D.*R_SAND1(1,2); % Gy   
D_RSand_micro(3).D=D.*R_SAND1(1,3); % Gy
D_RSand_micro(4).D=D.*R_SAND1(1,4); % Gy % no es necesario porque es lo que calculo con MCNP 
D_RSand_micro(5).D=D.*R_SAND1(1,5); % Gy

figure(100)
%hepatic arteria 
%ratio=D_RSand_micro(1).D./Dmicro(1).D; 
minValue = min(uS_ah(uS_ah> 0), [], 'all');
maxValue= max(uS_ah(:));
imshow(uS_ah(:,:,80),[])
colormap jet 
%max1=max(DportalVein(:));
clim([minValue maxValue])
colorbar 
title(' uS')
unit=' ';
valor = f_obtener_coordenadas(uS_ah(:,:,80),unit); 

%%
D22=zeros(s); 
ind=D>0; 
D23=D.*ind; 
D24=DosisParenquima.*ind; 

A22=(D23-D24)*100./D23;


figure(nfig)
nfig=nfig+1; 
 
minValue = min(A22(:)); %, [], 'all');
maxValue= max(A22(:));
imshow(A22(:,:,80),[])
colormap(jet) 
%max1=max(DportalVein(:));
clim([minValue maxValue])
colorbar 
title(' Ratio entre Arteria Hepatica-1 /Arteria Hepatica-2')
unit=' ';
valor = f_obtener_coordenadas(A22(:,:,80),unit); 
% devuelve el ultimo 




%%
figure(3001)
%hepatic arteria 
ratio=D_RSand_micro(1).D./Dmicro(1).D; 
minValue = min(ratio(ratio > 0), [], 'all');
maxValue= max(ratio(:));
imshow(ratio(:,:,80),[])
colormap jet 
%max1=max(DportalVein(:));
clim([minValue maxValue])
colorbar 
title(' Ratio entre Arteria Hepatica-1 /Arteria Hepatica-2')
unit=' ';
valor = f_obtener_coordenadas(ratio(:,:,80),unit); 
% devuelve el ultimo 


%%
figure(3001)
%hepatic arteria 
ratio=Dmicro(1).D; 
a=ratio(:,:,za(end)); 
minValue = min(ratio(ratio > 0), [], 'all');
maxValue= max(a(:));
imshow(a,[])
colormap jet 
%max1=max(DportalVein(:));
clim([2000 maxValue])
colorbar 
title(' jskf')
unit=' Gy';
valor = f_obtener_coordenadas(a,unit); 
% devuelve el ultimo 


figure(3001)
%hepatic arteria 
ratio=D; 
a=ratio(:,:,zD(end)); 
minValue = min(ratio(ratio > 0), [], 'all');
maxValue= max(a(:));
imshow(a,[])
colormap jet 
%max1=max(DportalVein(:));
%clim([2000,maxValue])
colorbar 
title(' jskf')
unit=' Gy';
valor = f_obtener_coordenadas(a,unit); 
% devuelve el ultimo 



%%
%nfig=1000; 
%% 
organo=index.tumor; 
%volumen=f_HDV(D3,I1,organo,vCT,nfig);
for i=1:5
  f_HDV_micro(Dmicro(i).D,I1,organo,vCT,nfig,i); 
end
nfig=nfig+1; 

organo=index.pretumor; 
%volumen=f_HDV(D3,I1,organo,vCT,nfig);
for i=1:5
  f_HDV_micro(Dmicro(i).D,I1,organo,vCT,nfig,i); 
end
nfig=nfig+1; 

organo=index.liver; 
for i=1:5
  f_HDV_micro(Dmicro(i).D,I1,organo,vCT,nfig,i); 
end


ind=I1==index.liver;
Dosis.liver.hepatic_arteria=A(ind).*micro.hepatic_arteria;        %Bq/g*(Gy*g*Bq^-1)=Gy
Dosis.liver.max_hepatic_Arteria=max(Dosis.liver.hepatic_arteria(:));
Dosis.liver.bile_duct=A(ind).*micro.bile_duct;        %Bq/g*(Gy*g*Bq^-1)=Gy
Dosis.liver.max_bile_duct=max(Dosis.liver.bile_duct(:));
Dosis.liver.portal_vein=A(ind).*micro.portal_vein;        %Bq/g*(Gy*g*Bq^-1)=Gy
Dosis.liver.max_portal_vein=max(Dosis.liver.portal_vein(:));
Dosis.liver.parenquima=A(ind).*micro.parenquima;        %Bq/g*(Gy*g*Bq^-1)=Gy
Dosis.liver.max_parenquima=max(Dosis.liver.parenquima(:));
Dosis.liver.central_vein=A(ind).*micro.central_vein;        %Bq/g*(Gy*g*Bq^-1)=Gy
Dosis.liver.max_central_vein=max(Dosis.liver.central_vein(:));

ind=I1==index.tumor;
Dosis.tumor.hepatic_arteria=A(ind).*micro.hepatic_arteria;        %Bq/g*(Gy*g*Bq^-1)=Gy
Dosis.tumor.max_hepatic_Arteria=max(Dosis.tumor.hepatic_arteria(:));
Dosis.tumor.bile_duct=A(ind).*micro.bile_duct;        %Bq/g*(Gy*g*Bq^-1)=Gy
Dosis.tumor.max_bile_duct=max(Dosis.tumor.bile_duct(:));
Dosis.tumor.portal_vein=A(ind).*micro.portal_vein;        %Bq/g*(Gy*g*Bq^-1)=Gy
Dosis.tumor.max_portal_vein=max(Dosis.tumor.portal_vein(:));
Dosis.tumor.parenquima=A(ind).*micro.parenquima;        %Bq/g*(Gy*g*Bq^-1)=Gy
Dosis.tumor.max_parenquima=max(Dosis.tumor.parenquima(:));
Dosis.pretumor.central_vein=A(ind).*micro.central_vein;        %Bq/g*(Gy*g*Bq^-1)=Gy
Dosis.pretumor.max_central_vein=max(Dosis.pretumor.central_vein(:));

ind=I1==index.pretumor;
Dosis.pretumor.hepatic_arteria=A(ind).*micro.hepatic_arteria;        %Bq/g*(Gy*g*Bq^-1)=Gy
Dosis.pretumor.max_hepatic_Arteria=max(Dosis.tumor.hepatic_arteria(:));
Dosis.pretumor.bile_duct=A(ind).*micro.bile_duct;        %Bq/g*(Gy*g*Bq^-1)=Gy
Dosis.pretumor.max_bile_duct=max(Dosis.tumor.bile_duct(:));
Dosis.pretumor.portal_vein=A(ind).*micro.portal_vein;        %Bq/g*(Gy*g*Bq^-1)=Gy
Dosis.pretumor.max_portal_vein=max(Dosis.tumor.portal_vein(:));
Dosis.pretumor.parenquima=A(ind).*micro.parenquima;        %Bq/g*(Gy*g*Bq^-1)=Gy
Dosis.pretumor.max_parenquima=max(Dosis.tumor.parenquima(:));
Dosis.pretumor.central_vein=A(ind).*micro.central_vein;        %Bq/g*(Gy*g*Bq^-1)=Gy
Dosis.pretumor.max_central_vein=max(Dosis.pretumor.central_vein(:));


paciente.R_SAND=R_SAND; 

%close all 
%organo=index.tumor; 
%for i=1:5
%  f_HDV_micro(Dmicro(i).D,I1,organo,vCT,nfig,i); 
%end
%nfig=nfig+1; 
%save('C:\MAT\3Dosim\paciente.mat',"paciente");
