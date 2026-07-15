function [Volumen,DVH] = f_HDV_v2(D,Phantom,organo,t_voxel,nfig)

%=========================================================
% Calcula y grafica la DVH acumulativa
% Devuelve:
%   Volumen [cm3]
%   DVH (D98,D95,D70,D50,D2,V30,V70)
%=========================================================

%% Nombre y color

switch organo

    case 30
        txt='Tejido Blando';
        c='k';

    case 50
        txt='Pulmon';
        c='m';

    case 80
        txt='Hueso';
        c='c';

    case 90
        txt='Higado sano';
        c='b';

    case 99
        txt='Pretumor';
        c='g';

    otherwise

        if organo>=100
            txt='Tumor';
            c='r';
        else
            txt='Organo';
            c='k';
        end

end

%% Extraer voxeles

ind = Phantom==organo;

D = D(ind);

n = numel(D);

Volumen = n*prod(t_voxel);

if n==0

    DVH=[];

    return

end

%%=========================================================
%% Construcción exacta de la DVH
%%=========================================================

d = sort(D(:),'descend');

a = linspace(100,0,n)';

%% Calcular parámetros

DVH = f_Dx_DVH(d,a);

%%=========================================================
%% Graficar
%%=========================================================

figure(nfig)

stairs(d,a,...
    'Color',c,...
    'LineWidth',2);

hold on

grid on

xlabel('Dose (Gy)')
ylabel('Volume (%)')

title('Cumulative Dose Volume Histogram')

set(gca,'YScale','log')
ylim([0.1 100])

legend({'Higado','Tumor','Pretumor'})

end