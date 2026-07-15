function Dx = f_Dx_DVH(d,a)

%=========================================================
% Calcula parámetros de una DVH acumulativa
%
% d : dosis (Gy) ordenada de mayor a menor
% a : volumen (%) correspondiente (100 -> 0)
%
% Devuelve:
%   D98 D95 D70 D50 D2
%   V30 V70
%=========================================================



d = d(:);
a = a(:);

%%=========================================================
%% Dx
%%=========================================================

% interp1 necesita eje X creciente

aDx = flipud(a);
dDx = flipud(d);

% eliminar porcentajes repetidos

[aDx,idx] = unique(aDx,'stable');
dDx = dDx(idx);

Dx.D98 = interp1(aDx,dDx,98,'linear','extrap');
Dx.D95 = interp1(aDx,dDx,95,'linear','extrap');
Dx.D70 = interp1(aDx,dDx,70,'linear','extrap');
Dx.D50 = interp1(aDx,dDx,50,'linear','extrap');
Dx.D2  = interp1(aDx,dDx,2 ,'linear','extrap');

%%=========================================================
%% Vx
%%=========================================================

dV = flipud(d);
aV = flipud(a);

% eliminar dosis repetidas

[dV,idx] = unique(dV,'stable');
aV = aV(idx);

Dx.V30 = interp1(dV,aV,30,'linear',0);
Dx.V70 = interp1(dV,aV,70,'linear',0);

%%=========================================================
%% Limitar resultados
%%=========================================================

campos = fieldnames(Dx);

for i=1:numel(campos)

    if isnan(Dx.(campos{i}))
        Dx.(campos{i}) = 0;
    end

end

Dx.V30 = max(0,min(100,Dx.V30));
Dx.V70 = max(0,min(100,Dx.V70));

end