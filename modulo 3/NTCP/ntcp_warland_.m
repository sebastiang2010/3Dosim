% 
clc 
clear 
close all 
% Selección de material
material = menu('Seleccione el material de las microesferas:', 'Resina', 'Vidrio');

% Valores de msA para cada material (kBq)
switch material
    case 1 % Resina
        msA_resina = 0.05; % 5%kBq
        msA = msA_resina;
        material_str = 'Resina'; 
        Dlim=300; 
    case 2 % Vidrio
        msA_vidrio = 2.5; % kBq
        msA = msA_vidrio;
        material_str = 'Vidrio';
        Dlim = 500 ; 
    otherwise
        error('Selección no válida');
end

% Parámetros fijos
D = linspace(0.1, Dlim, 500); % dosis absorbida en Gy

% Funciones para el modelo de Walrand
TD50_walrand = @(nu, msA) (25.2 + 22.1 * (1 - exp(-2.74 * msA))) ./ (nu - 0.4).^0.584;
gamma_walrand = @(nu) 13.7 * nu.^2 + 30.6 * nu - 8.41;
NTCP_walrand = @(D, nu, msA) 1 ./ (1 + (TD50_walrand(nu, msA) ./ D).^gamma_walrand(nu));

% Volúmenes a graficar
nu_values = [1.0, 0.67, 0.5, 0.45, 0.4];
colors = {'k', [0.5 0.5 0.5], [0.55 0 0], [1 0.5 0], [0 0.5 0]};
labels = {'100%', '67%', '50%', '45%', '40%'};

% Graficar
figure;
set(gcf, 'Color', [1 1 1]);
hold on;
for i = 1:length(nu_values)
    nu = nu_values(i);
    ntcp = NTCP_walrand(D, nu, msA);
    plot(D, ntcp*100, 'Color', colors{i}, 'DisplayName', [labels{i} ' – ' num2str(nu, '%.2f')]);
end

xlabel('Dosis absorbida en RE (Gy)');
ylabel('NTCP (%)');
title(['Curvas NTCP – Modelo de Walrand (msA = ' num2str(msA) ' kBq – ' material_str ')']);
grid on;
legend('Location','best');
ylim([0 105]);
xlim([0 Dlim]);
hold off
