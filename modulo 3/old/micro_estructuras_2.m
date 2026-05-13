clc

%% Micro estructuras
%Esto es valido solo para el higado
%por lo tanto hay que usar el Phantoma para seleccionar solo el higado
masa1=1.06*prod(vPET);


% agregar que tabla es 
micro.hepatic_arteria=154; %Gy*g*MBq^-1;
micro.bile_duct=85;
micro.portal_vein=85;
micro.parenquima=50;
micro.central_vein=45;

Actividad1=sum(PET1);
A=PET1.*1e-6; %Bq2MBq
A=A./masa1; %Bq/g

% tengo que consideras solo el higado
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