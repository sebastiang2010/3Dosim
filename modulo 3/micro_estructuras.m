%% Micro estructuras 
%Esto es valido solo para el higado
%por lo tanto hay que usar el Phantoma para seleccionar solo el higado 
% usar la densidad que estaba antes
close all
%clear 
clc

nfig=1000; 

load('C:\MAT\3Dosim\paciente.mat')
vPET=paciente.vPET; 
vCT=paciente.vCT; 
PET1=paciente.PET;
I1=paciente.Phantom; 
index=paciente.index; 

volumen=prod(vPET); %cm 
masa1=1.06*volumen;  %el volumen esta en cm  

D=paciente.Dosis.voxel; 
CT=paciente.CT; 

%actividad ok 
actividad=sum(PET1(:))/1e9;


A=PET1.*1e-6; %Bq2MBq 
A=A./masa1; %Bq/g

s=size(A);
ind_maxA=find(max(A(:))==A);
ind_maxD=find(max(D(:))==D); 
[xa,ya,za]=ind2sub(s,ind_maxA); 
[xD,yD,zD]=ind2sub(s,ind_maxD);

% figure(100)
% imshow(D(:,:,zD),[]); 
% colormap(jet)
% hold on 
% figure(101)
% imshow(CT(:,:,zD),[])
% hold on 
% h=imshow(A(:,:,zD),[]); 
% colormap(jet)
% alpha 0.4
% %alpha 0.2

% factor
% Asumiendo una distribucion de la tabla no la encuentro !!!
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
Dmicro(4).D=A.*micro.parenquima;        %Bq/g*(Gy*g*Bq^-1)=Gy
Dmicro(5).D=A.*micro.central_vein;        %Bq/g*(Gy*g*Bq^-1)=Gy

nfig=1000; 

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
