% Leer la información del volumen 
% grabar la fusion en dicom 
close all
clear 
clc
%% 
nshow=3;
nfig=1; 
%%
a=load('C:\MAT\3Dosim\Check\registracion_ 1\paciente.mat'); 
paciente=a.paciente; 
clear a 
%%
interpolacion{1,1}='linear';
interpolacion{1,2}='nearest'; 
interpolacion{1,3}='cubic'; 
interpolacion{1,4}='makima';
interpolacion{1,5}='spline'; 

type_intp=2; 

PET=paciente.PET_check.PET; 
R_PET=paciente.PET_check.R;
CT=paciente.CT_check.CT;
R_CT=paciente.CT_check.R; 
vPET(1)=R_PET.PixelExtentInWorldX;
vPET(2)=R_PET.PixelExtentInWorldY;
vPET(3)=R_PET.PixelExtentInWorldZ; 
vCT=[1, 1 ,1]; 
sCT=size(CT);
%%
figure(nfig)
nfig=nfig+1;
for i=1:size(PET,3)
    imshow(PET(:,:,i),[])
    colormap(jet)
    title(num2str(i))
    pause(0.1)
end 

%% traslado la CT 
posfinal=[0 0 0]; 
desp(1)=posfinal(1)-R_CT.XWorldLimits(1); 
desp(2)=posfinal(2)-R_CT.YWorldLimits(1);
desp(3)=posfinal(3)-R_CT.ZWorldLimits(1);  

T=affine3d([1 0 0 0; 
            0 1 0 0; 
            0 0 1 0; 
            desp(1) desp(2) desp(3) 1]);

[CT_moved,R_CT_moved]=imwarp(CT,R_CT,T); 
[PET_moved,R_PET_moved]=imwarp(PET,R_PET,T); 
R_CT=R_CT_moved; 
R_PET=R_PET_moved; 
clear R_PET_moved R_CT_moved
%%
R_PET2=imref2d(size(PET),R_PET.XWorldLimits,R_PET.YWorldLimits);
R_CT2=imref2d(size(CT),R_CT.XWorldLimits,R_CT.YWorldLimits);
%% 
b=PET_moved(:,:,6);
max1=max(PET_moved(:)); 
figure(nfig)
nfig=nfig+1; 
ax1 = axes;
h = imshow(b, R_PET2, 'Parent', ax1);  
colormap(ax1, jet);
colorbar(ax1);  
clim([0 max1])

b=PET_moved(:,:,21);
max1=max(PET_moved(:)); 
figure(nfig)
nfig=nfig+1; 
ax1 = axes;
h = imshow(b, R_PET2, 'Parent', ax1);  
colormap(ax1, jet);
colorbar(ax1);  
clim([0 max1])


% figure(nfig)
% nfig=nfig+1;
% for i=1:size(PET,3)
%     imshow(PET_moved(:,:,i),[])
%     colormap(jet)
%     title(num2str(i))
%     pause(0.1)
% end 

%% interpolacion 

% Coordenadas originales
[x, y, z] = meshgrid (R_PET.XWorldLimits(1):vPET(1):(R_PET.XWorldLimits(2) - vPET(1)), ...
                       R_PET.YWorldLimits(1):vPET(2):(R_PET.YWorldLimits(2) - vPET(2)), ...
                       R_PET.ZWorldLimits(1):vPET(3):(R_PET.ZWorldLimits(2) - vPET(3)));

% Coordenadas de la nueva resolución (en el mundo real)
[xq, yq, zq] = meshgrid (R_PET.XWorldLimits(1):vCT(1):(R_PET.XWorldLimits(2) - vCT(1)), ...
                          R_PET.YWorldLimits(1):vCT(2):(R_PET.YWorldLimits(2) - vCT(2)), ...
                          R_PET.ZWorldLimits(1):vCT(3):(R_PET.ZWorldLimits(2) - vCT(3)));


PET_interpolado = interp3(x, y, z, PET, xq, yq, zq,interpolacion{1,type_intp});


%%
R_PET_interpolado=imref3d(size(PET_interpolado),R_PET.XWorldLimits,R_PET.YWorldLimits,R_PET.ZWorldLimits);

% Después de crear R_PET_interpolado:
% debe ser igual al de la CT 
voxelSize_PET_interpolado = [R_PET_interpolado.PixelExtentInWorldX, ...
                             R_PET_interpolado.PixelExtentInWorldY, ...
                             R_PET_interpolado.PixelExtentInWorldZ];

nslice=1; 
b=PET_interpolado(:,:,nslice); 
R_PET2=imref2d(size(b),R_PET.XWorldLimits,R_PET.YWorldLimits); 

max2=max(PET_interpolado(:)); 


b=PET_interpolado(:,:,11); 
figure(nfig)
nfig=nfig+1; 
ax1 = axes;
h = imshow(b, R_PET2, 'Parent', ax1);  
colormap(ax1, jet);
colorbar(ax1);  
clim([0 max2])

b=PET_interpolado(:,:,40); 
figure(nfig)
nfig=nfig+1; 
ax1 = axes;
h = imshow(b, R_PET2, 'Parent', ax1);  
colormap(ax1, jet);
colorbar(ax1);  
clim([0 max2])


figure(nfig)
nfig=nfig+1;
for i=1:size(PET_interpolado,3)-1 % que da la ultima matriz como NaN 
    imshow(PET_interpolado(:,:,i),[])
    colormap(jet)
    title(num2str(i))
    colorbar
    clim([0 max2])
    pause(0.5)
end 

%% recorte interpolado 
% 
% posPETi(1)=R_CT.XWorldLimits(1); 
% posPETi(2)=R_CT.YWorldLimits(1);
% posPETi(3)=R_CT.ZWorldLimits(1); 
% 
% posPETf(1)=R_CT.XWorldLimits(2); 
% posPETf(2)=R_CT.YWorldLimits(2);
% posPETf(3)=R_CT.ZWorldLimits(2); 
% 
% ind_i(1)=(posPETi(1)-R_PET_interpolado.XWorldLimits(1))/R_PET_interpolado.PixelExtentInWorldX;
% ind_i(1)=ind_i(1)+1; 
% ind_i(2)=(posPETi(2)-R_PET_interpolado.YWorldLimits(1))/R_PET_interpolado.PixelExtentInWorldY;
% ind_i(2)=ind_i(2)+1; 
% ind_i(3)=(posPETi(3)-R_PET_interpolado.ZWorldLimits(1))/R_PET_interpolado.PixelExtentInWorldZ;
% ind_i(3)=ind_i(3)+1; 
% 
% % analizar si hay que sumarle uno o no 
% ind_i=round(ind_i); 
% 
% ind_f(1)=(posPETf(1)-R_PET_interpolado.XWorldLimits(1))/R_PET_interpolado.PixelExtentInWorldX;
% ind_f(1)=ind_f(1)+1; 
% ind_f(2)=(posPETf(2)-R_PET_interpolado.YWorldLimits(1))/R_PET_interpolado.PixelExtentInWorldY;
% ind_f(2)=ind_f(2)+1; 
% ind_f(3)=(posPETf(3)-R_PET_interpolado.ZWorldLimits(1))/R_PET_interpolado.PixelExtentInWorldZ;
% ind_f(3)=ind_f(3)+1; 
% 
% ind_f=round(ind_f); 
% 
% delta=ind_f-ind_i; 
% 
% b=PET_interpolado(:,:,nslice); 
% 
% b1=b(ind_i(1):ind_f(1),ind_i(2):ind_f(2)); 
% PET_interpolado_cortado=PET_interpolado(ind_i(1):ind_i(1)+sCT(1)-1,ind_i(2):ind_i(2)+sCT(2)-1,1:end); 
% sPET_intr_rec=size(PET_interpolado_cortado); 
% PET_interpolado_completado=zeros(sCT); 
% PET_interpolado_completado(:,:,1:sPET_intr_rec(3))=PET_interpolado_cortado; 
% %% modificarlo aca para que quede de 512x512x127
% 
% 
% b2=b1; 
% 
% R_PET2_interpolado=imref2d(size(b2),[0 ,R_PET_interpolado.PixelExtentInWorldX*size(b1,1)],[0 ,R_PET_interpolado.PixelExtentInWorldY*size(b1,2)]); 
% 
% %PET_expandido_recortado=PET_expandido(ind(1):ind(1)+sCT(1),ind(2):ind(2)+sCT(2),ind(3):sPET(3)); 

% PET2=PET_interpolado(1:81,1:101,1:21); 
% 
% b2=PET2(:,:,11); 
% 
% figure(nfig)
% nfig=nfig+1; 
% ax1 = axes;
% %h = imshow(b2, R_PET2_interpolado, 'Parent', ax1);  
% h=imshow(b2);
% colormap(ax1, jet);
% colorbar(ax1); 
% clim([0 max2])
% 
% figure(nfig)
% nfig=nfig+1;
% for i=1:size(PET2,3)
%     imshow(PET2(:,:,i),[])
%     colormap(jet)
%     pause(0.1)
% end 
%%
% A=PET_interpolado_completado; 
% %relacion=prod(vCT)/prod(vPET); 
% 
% relacion=1; % no entiendo 
% Actividad=sum(A(:)/relacion);
% Actividad_GBq_int=Actividad/1e9; 

%% 
 a=CT(:,:,11);
 b=PET(:,:,11); 
 figure(nfig)
 nfig=nfig+1; 
 ax1 = axes;
 imshow(a ./ max(a(:)), R_CT2, 'Parent', ax1);  
 hold on 
 ax2 = axes;
 h = imshow(b, R_PET2_interpolado, 'Parent', ax2);  
 set(ax2, 'Color', 'none');  
 set(h, 'AlphaData', 0.5);  
 colormap(ax2, jet);
 h=colorbar(ax2);  
 pos_bar=h.Position; 
 pos_bar(1)=pos_bar(1)+0.05; 
 set(h,'Position',pos_bar)
 axis(ax1, 'off');   
 clim([0 max2])
% 
% %% 
% figure(nfig)
% nfig=nfig+1; 
% ax1 = axes;
% pos_ax1=ax1.Position; 
% h = imshow(a./max(a(:)),'Parent', ax1);
% hold on 
% ax2 = axes;
% set(ax2,'Position',pos_ax1)
% h = imshow(b2,'Parent', ax2);  
% set(ax2, 'Color', 'none');  
% set(h, 'AlphaData', 0.5); 
% colormap(ax2, jet);
% h=colorbar(ax2);  
% pos_bar=h.Position; 
% pos_bar(1)=pos_bar(1)+0.05; 
% set(h,'Position',pos_bar)
% clim([0 max2])
% %% 
% 
% 
% 
% max5=max(PET_interpolado_completado(:)); 
% figure(nfig)
% nfig=nfig+1; 
% for i=1:sCT(3)
%     clf
%     a=double(CT(:,:,i));
%     b=PET_interpolado_completado(:,:,i);
%     ax1 = axes;
%     pos_ax1=ax1.Position; 
%     h = imshow(a./max(a(:)),'Parent', ax1);
%     hold on 
%     ax2 = axes;
%     set(ax2,'Position',pos_ax1)
%     h = imshow(b,'Parent', ax2);  
%     set(ax2, 'Color', 'none');  
%     set(h, 'AlphaData', 0.5); 
%     colormap(ax2, jet);
%     h=colorbar(ax2);  
%     pos_bar=h.Position; 
%     pos_bar(1)=pos_bar(1)+0.05; 
%     set(h,'Position',pos_bar)
%     clim([0 max5])
%     pause(0.1)
% end 
% %% 
% Actividad_GBq.org=Actividad_GBq_org; 
% Actividad_GBq.intp=Actividad_GBq_int;
% Actividad_GBq.exp=Actividad_GBq_exp;
% 
% %% 
% paciente.PET_intp.PET=PET_interpolado_completado; 
% paciente.PET_intp.type_intp=interpolacion{1,type_intp}; 
% paciente.PET_intp.vPET=voxelSize_PET_interpolado;
% paciente.PET_intp.R_PET=R_PET_interpolado;
% % 
% paciente.PET_exp.PET=PET_exp_completado; 
% paciente.PET_exp.factor=factor; 
% paciente.PET_exp.vPET=voxelSize_PET_expandido;
% paciente.UnitsPET=UnitsPET;
% %% save tiff
% clc
% %f_save_tiff(PET2,1,directorio); %op=1 PET else CT
% %f_save_tiff(CT,0,directorio);
% 
% %if ~isempty(file_paciente);load(file_paciente);end
% %paciente.vCT=vCT;
% paciente.PET_original=PET; 
% paciente.CT=CT;
% paciente.vCT=vCT; 
% paciente.info_CT=info_CT; 
% paciente.info_PET=info_PET;
% paciente.registro=1; 
% paciente.registro_date=datetime("today");
% paciente.PatientID=info_CT.PatientID; 
% paciente.UnitsPET=UnitsPET; 
% paciente.vPET_org=vPET_org;
% paciente.Actividad=Actividad; %Bq
% paciente.R_PET=R_PET_interpolado; 
% paciente.R_CT=R_CT; 
% 
% %% save paciente 
% file=[directorio,'/paciente.mat'];
% delete(file)
% save(file,'paciente')
% 
% disp(' ')
% disp('....................................................................')
% disp('....................................................................')
% disp('    Se genero un archivo "paciente.mat" en el directorio:           ')
% disp(' ')
% disp(directorio)
